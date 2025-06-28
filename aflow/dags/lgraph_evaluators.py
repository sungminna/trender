"""
L-Graph 프로젝트의 멀티 에이전트 파이프라인 평가 로직
- Langfuse의 Trace 객체를 입력으로 받아, 각 에이전트의 결과물을 평가합니다.
- Deepeval을 사용하여 LLM 기반의 정성적 평가 및 표준 메트릭을 사용합니다.
"""
from deepeval.metrics import GEval, FaithfulnessMetric, ToxicityMetric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from langfuse.model import Trace, Span
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _get_agent_observation(trace: Trace, agent_name_contains: str) -> Span | None:
    """Trace에서 특정 이름을 포함하는 첫 번째 에이전트 Span(Observation)을 찾습니다."""
    for obs in trace.observations:
        if agent_name_contains in obs.name:
            # LangGraph에서 생성된 실제 에이전트 노드는 'agent:...' 또는 'agent:graph:...-...' 형태
            if obs.name.startswith("agent:") or obs.type == "SPAN":
                return obs
    logger.warning(f"Trace {trace.id}에서 '{agent_name_contains}'를 포함하는 에이전트 관측을 찾지 못했습니다.")
    return None

def _get_content_from_message(message_payload: dict | None) -> str:
    """Langfuse 메시지 구조에서 content를 추출합니다."""
    if not message_payload:
        return ""
    
    # LangGraph의 출력은 복잡한 리스트/사전 구조일 수 있음
    messages = message_payload.get("messages", [])
    if isinstance(messages, list) and messages:
        # 마지막 메시지의 content를 사용
        last_message = messages[-1]
        if isinstance(last_message, dict):
            return last_message.get("content", "")
    
    # 단순 문자열인 경우
    if isinstance(message_payload, str):
        return message_payload

    return str(message_payload)

def evaluate_research_relevance(trace: Trace) -> dict | None:
    """Research Agent의 결과물이 사용자의 초기 요청과 관련성이 높은지 평가합니다. (G-Eval)"""
    try:
        research_obs = _get_agent_observation(trace, "research_agent")
        if not research_obs or not research_obs.input or not research_obs.output:
            return None

        user_request = _get_content_from_message(research_obs.input)
        research_output = _get_content_from_message(research_obs.output)

        if not user_request or not research_output:
            logger.warning(f"Trace {trace.id}의 Research Agent에서 유효한 입/출력 content를 찾지 못했습니다.")
            return None

        relevance_metric = GEval(
            name="Research Relevance",
            criteria="제시된 '사용자 요청'을 바탕으로 팟캐스트 대본을 작성해야 할 때, 'Research 결과물'이 얼마나 관련성 높고 유용한 정보를 담고 있는지 평가해줘. 핵심 정보를 잘 요약하고 있는지, 불필요한 내용이 없는지를 중점적으로 봐줘.",
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT]
        )
        test_case = LLMTestCase(input=user_request, actual_output=research_output)
        relevance_metric.measure(test_case)

        logger.info(f"Trace {trace.id} - Research Relevance: {relevance_metric.score:.2f}")
        return {"score": relevance_metric.score, "reason": relevance_metric.reason}

    except Exception as e:
        logger.error(f"Research Agent 평가 중 오류 발생 (Trace ID: {trace.id}): {e}", exc_info=True)
        return None

def evaluate_narrative_faithfulness(trace: Trace) -> dict | None:
    """Narrative Agent의 대본이 Research 결과에 충실한지 평가합니다. (FaithfulnessMetric)"""
    try:
        research_obs = _get_agent_observation(trace, "research_agent")
        narrative_obs = _get_agent_observation(trace, "story_narrative_agent")
        if not research_obs or not narrative_obs or not research_obs.output or not narrative_obs.output:
            return None
        
        research_context = _get_content_from_message(research_obs.output)
        narrative_output = _get_content_from_message(narrative_obs.output)
        if not research_context or not narrative_output:
            return None

        faithfulness_metric = FaithfulnessMetric(threshold=0.7)
        test_case = LLMTestCase(actual_output=narrative_output, retrieval_context=[research_context])
        faithfulness_metric.measure(test_case)
        logger.info(f"Trace {trace.id} - Narrative Faithfulness: {faithfulness_metric.score:.2f}")
        return {"score": faithfulness_metric.score, "reason": faithfulness_metric.reason}
    except Exception as e:
        logger.error(f"Narrative Faithfulness 평가 중 오류 발생 (Trace ID: {trace.id}): {e}", exc_info=True)
        return None

def evaluate_narrative_coherence(trace: Trace) -> dict | None:
    """Story Narrative Agent가 생성한 대본의 내러티브 완성도와 흥미도를 평가합니다. (G-Eval)"""
    try:
        narrative_obs = _get_agent_observation(trace, "story_narrative_agent")
        if not narrative_obs or not narrative_obs.output:
            return None

        narrative_output = _get_content_from_message(narrative_obs.output)
        if not narrative_output:
            logger.warning(f"Trace {trace.id}의 Narrative Agent에서 유효한 출력 content를 찾지 못했습니다.")
            return None

        coherence_metric = GEval(
            name="Narrative Coherence & Engagement",
            criteria="이 팟캐스트 대본이 청중의 흥미를 끌 수 있도록 이야기가 자연스럽게 흘러가는지, 내러티브 구조(서론, 본론, 결론)가 명확한지 평가해줘. 문장의 흐름이 어색하거나 논리적 비약이 없는지를 중점적으로 검토해줘.",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT]
        )
        test_case = LLMTestCase(input="N/A", actual_output=narrative_output)
        coherence_metric.measure(test_case)

        logger.info(f"Trace {trace.id} - Narrative Coherence: {coherence_metric.score:.2f}")
        return {"score": coherence_metric.score, "reason": coherence_metric.reason}
        
    except Exception as e:
        logger.error(f"Narrative Agent 평가 중 오류 발생 (Trace ID: {trace.id}): {e}", exc_info=True)
        return None

def evaluate_final_script_safety(trace: Trace) -> dict | None:
    """최종 스크립트의 유해성을 평가합니다. (ToxicityMetric)"""
    try:
        tts_obs = _get_agent_observation(trace, "tts_agent")
        if not tts_obs or not tts_obs.output:
            return None

        tts_output = _get_content_from_message(tts_obs.output)
        if not tts_output:
            logger.warning(f"Trace {trace.id}의 TTS Agent에서 유효한 출력 content를 찾지 못했습니다.")
            return None
            
        toxicity_metric = ToxicityMetric(threshold=0.1) # 엄격하게 관리
        test_case = LLMTestCase(input="N/A", actual_output=tts_output)
        toxicity_metric.measure(test_case)
        # Toxicity는 점수가 낮을수록 좋으므로, 1.0 - score 로 변환하여 직관성을 높임 (1.0 = 안전)
        safety_score = 1.0 - toxicity_metric.score
        logger.info(f"Trace {trace.id} - Script Safety (1 - Toxicity): {safety_score:.2f}")
        return {"score": safety_score, "reason": toxicity_metric.reason}

    except Exception as e:
        logger.error(f"Script Safety 평가 중 오류 발생 (Trace ID: {trace.id}): {e}", exc_info=True)
        return None

def evaluate_tts_readiness(trace: Trace) -> dict | None:
    """TTS Agent가 생성한 최종 스크립트가 음성 합성에 적합한지 평가합니다. (G-Eval)"""
    try:
        tts_obs = _get_agent_observation(trace, "tts_agent")
        if not tts_obs or not tts_obs.output:
            return None

        tts_output = _get_content_from_message(tts_obs.output)
        if not tts_output:
            logger.warning(f"Trace {trace.id}의 TTS Agent에서 유효한 출력 content를 찾지 못했습니다.")
            return None
            
        readiness_metric = GEval(
            name="TTS Readiness",
            criteria="이 스크립트가 TTS(Text-to-Speech)로 자연스럽게 변환될 수 있는지 평가해줘. 어려운 약어, 복잡한 문장 구조, 부자연스러운 표현이 없는지, 그리고 적절한 위치에 쉼표나 마침표가 사용되어 운율을 살릴 수 있는지 중점적으로 검토해줘.",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT]
        )
        test_case = LLMTestCase(input="N/A", actual_output=tts_output)
        readiness_metric.measure(test_case)

        logger.info(f"Trace {trace.id} - TTS Readiness: {readiness_metric.score:.2f}")
        return {"score": readiness_metric.score, "reason": readiness_metric.reason}

    except Exception as e:
        logger.error(f"TTS Agent 평가 중 오류 발생 (Trace ID: {trace.id}): {e}", exc_info=True)
        return None 