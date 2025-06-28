"""
Airflow DAG for L-Graph Daily Evaluation

- 매일 자정, 지난 24시간 동안 생성된 팟캐스트 결과(Traces)를 평가합니다.
- lgraph_evaluators.py의 평가 로직을 사용하여 각 에이전트의 성능을 측정합니다.
- 평가 결과는 Langfuse에 Score로 다시 기록되어 지속적인 성능 추적을 가능하게 합니다.
"""
import pendulum
from airflow.decorators import dag, task
from datetime import datetime, timedelta
import os
import logging

# Airflow는 기본적으로 DAG 파일을 주기적으로 파싱하므로,
# 실제 실행 시점에만 필요한 라이브러리는 task 함수 내에서 import 하는 것이 좋습니다.

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 환경변수 로드 ---
# Airflow에서는 Connections나 Variables를 사용하는 것이 권장되지만,
# 로컬 테스트 및 단순성을 위해 .env 파일을 사용할 수 있도록 설정합니다.
# Docker 환경에서는 docker-compose.yml의 env_file 속성으로 변수가 주입되므로 이 코드는 로컬 실행에 더 유용합니다.
try:
    from dotenv import load_dotenv
    # DAG가 위치한 aflow/dags/ 에서 상위 폴더인 aflow/ 에 있는 .env 파일을 찾습니다.
    dag_folder = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(dag_folder, '..', '.env')
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
        logger.info(f".env 파일을 다음 경로에서 로드했습니다: {env_path}")
    else:
        logger.warning(f"지정된 경로에 .env 파일이 없습니다: {env_path}. Airflow 환경 변수를 사용합니다.")
except ImportError:
    logger.info("dotenv 패키지가 설치되지 않았습니다. Airflow 환경 변수를 사용합니다.")

@dag(
    dag_id='lgraph_daily_evaluation',
    schedule_interval='@daily',
    start_date=pendulum.datetime(2024, 6, 21, tz="UTC"),
    catchup=False,
    doc_md="""
    ### L-Graph 일일 평가 파이프라인
    
    이 DAG는 매일 자정, L-Graph 시스템이 지난 24시간 동안 생성한 팟캐스트 결과물을 자동으로 평가합니다.
    - **추출**: Langfuse API를 통해 최근 Trace들을 가져옵니다.
    - **평가**: Deepeval 기반의 LLM-as-a-judge를 활용하여 각 에이전트(Research, Narrative, TTS)의 결과물 품질을 점수화합니다.
    - **기록**: 산출된 점수(Score)와 평가 이유(Comment)를 원래 Trace에 다시 기록하여 성능을 지속적으로 추적하고 분석할 수 있도록 합니다.
    """,
    tags=['lgraph', 'evaluation', 'langfuse'],
)
def lgraph_daily_evaluation_dag():
    """
    L-Graph 멀티 에이전트 시스템의 일일 자동 평가를 수행하는 Airflow DAG
    """
    @task()
    def run_lgraph_evaluations():
        """
        Langfuse에서 Trace를 가져와 평가하고, Score를 기록하는 메인 태스크
        """
        import langfuse
        from lgraph_evaluators import (
            evaluate_research_relevance,
            evaluate_narrative_faithfulness,
            evaluate_narrative_coherence,
            evaluate_final_script_safety,
            evaluate_tts_readiness,
        )

        try:
            langfuse_client = langfuse.Langfuse()
            logger.info("Langfuse 클라이언트 초기화 성공")
        except Exception as e:
            logger.error(f"Langfuse 클라이언트 초기화 실패: {e}")
            raise

        # 1. 지난 24시간 동안의 Trace를 Fetch
        yesterday = datetime.utcnow() - timedelta(days=1)
        # lgraph/tasks/podcast_tasks.py 에서 설정한 trace_name
        trace_name_prefix = "Podcast Production" 
        
        try:
            traces_iterator = langfuse_client.client.trace.list_iterator(
                name_starts_with=trace_name_prefix,
                from_timestamp=yesterday,
            )
            logger.info(f"'{trace_name_prefix}'로 시작하는 Trace들을 성공적으로 가져왔습니다.")
        except Exception as e:
            logger.error(f"Langfuse에서 Trace를 가져오는 중 오류 발생: {e}")
            raise

        # 2. 각 Trace를 순회하며 평가 실행
        evaluation_functions = {
            "research_relevance": evaluate_research_relevance,
            "narrative_faithfulness": evaluate_narrative_faithfulness,
            "narrative_coherence": evaluate_narrative_coherence,
            "final_script_safety": evaluate_final_script_safety,
            "tts_readiness": evaluate_tts_readiness,
        }

        processed_traces = 0
        for trace in traces_iterator:
            logger.info(f"--- Trace {trace.id} 평가 시작 ---")
            
            for eval_name, eval_func in evaluation_functions.items():
                try:
                    # 이미 해당 평가 점수가 있는지 확인
                    if any(score.name == eval_name for score in trace.scores):
                        logger.info(f"Trace {trace.id}에 이미 '{eval_name}' 점수가 있으므로 건너뜁니다.")
                        continue

                    # 평가 함수 실행
                    eval_result = eval_func(trace)
                    
                    # 3. 평가 결과를 Langfuse Score로 기록
                    if eval_result and isinstance(eval_result.get("score"), (int, float)):
                        langfuse_client.score(
                            trace_id=trace.id,
                            name=eval_name,
                            value=eval_result["score"],
                            comment=eval_result.get("reason")
                        )
                        logger.info(f"Trace {trace.id}에 '{eval_name}' 점수 ({eval_result['score']:.2f})를 기록했습니다.")
                    else:
                        logger.warning(f"Trace {trace.id}의 '{eval_name}' 평가에서 유효한 결과를 얻지 못했습니다.")

                except Exception as e:
                    logger.error(f"Trace {trace.id}의 '{eval_name}' 평가 중 예외 발생: {e}", exc_info=True)
            
            processed_traces += 1
            logger.info(f"--- Trace {trace.id} 평가 완료 ---")

        logger.info(f"총 {processed_traces}개의 Trace에 대한 평가를 완료했습니다.")

    run_lgraph_evaluations()

# DAG 인스턴스화
lgraph_daily_evaluation_dag() 