# 프롬프트 관리 시스템

이 폴더는 LangGraph 에이전트들의 프롬프트를 관리하는 시스템입니다. 서비스 운영 중에도 프롬프트를 업데이트하고 즉시 반영할 수 있습니다.

## 📁 폴더 구조

```
prompts/
├── README.md              # 이 파일
├── research_agent.md      # Research Agent 프롬프트
└── [기타 에이전트].md     # 향후 추가될 에이전트 프롬프트들
```

## 🚀 주요 기능

### 1. 동적 프롬프트 로딩
- 프롬프트가 파일에서 자동으로 로드됩니다
- 파일 수정 시간을 체크하여 변경된 경우에만 다시 로드
- 캐싱을 통한 성능 최적화

### 2. 실시간 업데이트
- 서비스 중단 없이 프롬프트 업데이트 가능
- 파일 수정 후 함수 호출만으로 즉시 반영
- 운영 환경에서 안전한 업데이트

### 3. 버전 관리 친화적
- 마크다운 형식으로 가독성 높음
- Git을 통한 변경 이력 관리 가능
- 코드와 분리된 프롬프트 관리

## 📖 사용법

### 기본 사용법

```python
from utils.prompt_loader import get_prompt

# 프롬프트 로드
prompt = get_prompt("research_agent")
```

### 실시간 업데이트

```python
from super_agent import reload_research_agent

# 1. 프롬프트 파일 수정 (research_agent.md)
# 2. 에이전트 리로드
reload_research_agent()
```

### 고급 사용법

```python
from utils.prompt_loader import prompt_loader, get_prompt

# 강제 리로드
prompt = get_prompt("research_agent", force_reload=True)

# 모든 프롬프트 리로드
prompt_loader.reload_all()

# 사용 가능한 프롬프트 목록
available_prompts = prompt_loader.list_available_prompts()
```

## 🔧 프롬프트 파일 관리

### 파일 생성 규칙
1. 파일명: `{에이전트명}.md`
2. 인코딩: UTF-8
3. 형식: 마크다운 (.md)

### 프롬프트 작성 가이드
- 명확하고 구체적인 지시사항 작성
- 역할, 책임, 제약사항을 명시
- 예시와 템플릿 포함 권장
- 마크다운 형식 활용으로 가독성 향상

## 🛠️ 개발자 가이드

### 새로운 에이전트 추가

1. **프롬프트 파일 생성**
   ```bash
   touch prompts/new_agent.md
   ```

2. **프롬프트 내용 작성**
   ```markdown
   # ROLE
   새로운 에이전트의 역할 정의
   
   # RESPONSIBILITIES
   주요 책임사항
   
   # GUIDELINES
   동작 가이드라인
   ```

3. **에이전트 코드에서 로드**
   ```python
   from utils.prompt_loader import get_prompt
   
   def create_new_agent():
       prompt = get_prompt("new_agent")
       return create_react_agent(
           model="...",
           tools=[...],
           prompt=prompt,
           name="new_agent"
       )
   ```

### 프롬프트 로더 확장

필요에 따라 `utils/prompt_loader.py`를 수정하여 추가 기능을 구현할 수 있습니다:

- 프롬프트 템플릿 시스템
- 다국어 지원
- 환경별 프롬프트 관리
- 프롬프트 버전 관리

## 📊 모니터링

### 프롬프트 상태 확인

```python
# 예제 실행
python examples/prompt_management_example.py
```

### 로그 확인
프롬프트 로딩 시 콘솔에 로그가 출력됩니다:
```
Loaded prompt: research_agent
Reloading research agent with updated prompt...
Research agent reloaded successfully!
```

## ⚠️ 주의사항

1. **프롬프트 파일 경로**: `lgraph/prompts/` 폴더에만 저장
2. **파일 인코딩**: 반드시 UTF-8 사용
3. **파일 권한**: 읽기 권한 필요
4. **프로덕션 환경**: 프롬프트 변경 전 충분한 테스트 권장

## 🔍 트러블슈팅

### 자주 발생하는 문제

1. **프롬프트 파일을 찾을 수 없음**
   ```
   Warning: Prompt file 'prompts/xxx.md' not found
   ```
   → 파일 경로와 이름 확인

2. **인코딩 오류**
   ```
   Error loading prompt 'xxx': ...
   ```
   → 파일을 UTF-8로 저장했는지 확인

3. **권한 오류**
   → 파일 읽기 권한 확인

### 도움이 필요하면
- `examples/prompt_management_example.py` 실행
- 로그 메시지 확인
- 파일 경로와 권한 검증

## 📝 변경 이력

- v1.0.0: 기본 프롬프트 관리 시스템 구현
- 동적 로딩, 캐싱, 실시간 업데이트 기능 포함 