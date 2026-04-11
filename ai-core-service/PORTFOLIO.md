# Tally Bot - AI Core Service

그룹 채팅 대화에서 금액·항목을 자동 추출해 정산 데이터를 생성하는 FastAPI + LLM 코어 서비스

[Github →](https://github.com/25-spring-Capstone-Design-team1/tally-bot)

2025. 3 ~ 현재 / 캡스톤 팀 프로젝트 (AI 파트 단독 기여)

---

## 내가 기여한 부분

### 2단계 LLM 파이프라인 설계 및 최적화

- 초기에는 3단계 구조(항목 추출 → 장소 추출 → 정산 계산)로 설계했으나, 3차 프롬프트(final_prompt)의 역할을 규칙 기반 파싱으로 대체해 LLM 호출 횟수를 33% 절감
- 1차 프롬프트(`input_prompt.yaml`)에서 GPT-3.5-turbo로 항목·금액·화자·hint_phrases를 추출하고, 2차 프롬프트(`secondary_prompt.yaml`)에서 장소 정보를 보강하는 2단계 체계로 확정; 각 단계의 입출력 데이터는 JSON 포맷으로 전달해 파이프라인 간 연동을 표준화
- 외화 금액 변환(EUR, USD, JPY 등)을 LLM이 아닌 `currency_converter.py`에서 처리해 LLM의 단위 변환 오류를 방지

### FastAPI 서버 구축 및 API 설계

- `config/app_config.py`의 `create_app()`에서 FastAPI 앱을 생성하고 CORS 미들웨어를 적용해 Spring Boot 백엔드와의 크로스 오리진 통신을 허용
- 처리 목적에 따라 엔드포인트를 분리 설계: `/api/process`(실시간 처리), `/api/process-file`(파일 기반 처리), `/api/process-chain`(SequentialChain 처리), `/api/evaluate-with-processing`(결과 평가)
- Pydantic 모델(`ConversationRequest`, `ConversationResponse`)로 요청·응답 데이터의 자동 검증 및 JSON 직렬화 처리; 멤버 정보는 `List[Dict[str, str]]` 형태의 JSON으로 수신해 내부에서 `id_to_name` / `name_to_id` 매핑으로 변환
- `asyncio.gather`로 프롬프트 파일 3개를 병렬 로드해 I/O 대기 시간 최소화

### hint_phrase 중간 언어 도입

- LLM이 정산 규칙을 직접 계산하지 않고, 구조화된 힌트 문자열(hint_phrases)을 출력하도록 설계 → 이후 `result_processor.py`에서 regex 기반으로 확정적(deterministic)으로 파싱
- 7가지 정산 패턴을 커버하는 파싱 규칙 구현: 금액대납(`4 → 2`), 부담금액 지정(`0이 15000원 지불`), 1인당 금액, 참여자 제외(`1은 제외`), 배수 지불, 지불자 지정, n분의1
- LLM이 중간 언어만 생성하기 때문에 같은 입력에 대해 일관된 결과를 보장하고, 파싱 오류 위치를 즉시 특정 가능

### LLM vs 알고리즘 역할 경계 명확화

- "추출·구조화는 LLM, 계산은 알고리즘"으로 역할을 분리 — 정산 금액 분배 계산은 `calculation_helper.py`의 `generate_standard_calculation`에서 수행
- LLM에 계산을 맡겼을 때 발생하는 반올림 오차·비율 불일치를 제거하고, 재현성 및 단위 테스트 가능성 확보
- 복잡한 정산(hint_phrases 존재)과 단순 균등분할(n분의1)을 `is_complex_settlement`로 분기 처리해 불필요한 연산 최소화

### AI 응답 안정성 레이어 구축

- LLM 응답이 자주 깨진 JSON을 반환하는 문제를 해결하기 위해 `sanitize_json_string` 파이프라인 구현
  - 따옴표 없는 속성명 자동 보정 (`{name: ...}` → `{"name": ...}`)
  - 작은따옴표를 큰따옴표로 변환
  - 단일 객체를 배열로 자동 래핑
- `message_merger.py`로 같은 화자의 연속 메시지를 병합해 LLM 컨텍스트 효율 향상
- `json_filter.py`로 0 이하 금액 항목을 1차 결과에서 제거, 잘못된 항목이 후처리에 전달되지 않도록 차단

### LangChain 연동 및 LLM 추상화

- `langchain_openai.ChatOpenAI`로 OpenAI 모델을 래핑해 `ainvoke` 비동기 인터페이스를 통일; `service_config.py`에서 fast_llm(3.5-turbo) / experimental_llm(4o-mini) / accurate_llm(GPT-4) 3계층을 모듈 수준에서 선언해 호출부(`ai_service.py`)가 모델 교체 없이 변수명만 바꿔 실험 가능하도록 설계
- `langchain.schema`의 `SystemMessage` / `HumanMessage`로 프롬프트를 역할(role) 단위로 구조화; 시스템 프롬프트에 특별 규칙을 동적으로 append하는 방식으로 프롬프트 확장성 확보
- LangSmith tracing을 `service_config.py`에서 환경 변수로 활성화해 각 LLM 호출의 입·출력·지연 시간을 원격에서 추적 가능하도록 구성
- `ChainAIService`의 `process_with_simplified_chain` / `process_with_sequential_chain`으로 1차(항목 추출) → 2차(장소 보강) → 규칙 파싱의 파이프라인을 체인 단위로 캡슐화; 동일 입력에 모델만 교체해 `settlement_evaluator.py`의 7개 지표로 정량 비교 수행 (→ [정량 평가 체계 도입](#정량-평가-체계-도입-settlement_evaluatorpy) 참조)

### 정량 평가 체계 도입 (`settlement_evaluator.py`)

- LLM 출력 품질을 감각이 아닌 지표로 판단하기 위해 7개 지표 설계 및 구현
  - 금액 정확도(36%), 참여자 정확도(26%), 항목 수(15%), 할루시네이션 검출(10%), 장소·항목명 유사도(5%), 데이터 완성도(5%), 내부 일관성(3%)
- 총점 70% 이상을 통과 기준으로 설정, A+~F 등급으로 변환해 직관적 비교 가능
- 금액 비교 시 ±5% 허용 오차, 텍스트 유사도는 SequenceMatcher + 키워드 교집합 혼합 방식 적용

---

## 트러블슈팅

### 1. 사적 대화 혼입으로 인한 오추출

**문제 상황**
별명, 잡담, 계획 단계 메시지가 섞인 대화에서 정산과 무관한 금액이 항목으로 추출됨

**원인 가설**
LLM이 "도착하면 밥 먹자, 1만원대로" 같은 예상 발화를 실제 지불로 판단

**해결 접근**
- 1차 프롬프트에 "계획/예약 단계·금액 없는 대화는 출력하지 말 것" 명시적 규칙 추가
- `json_filter.py`에서 amount ≤ 0인 항목 후처리 제거
- `message_merger.py`로 연속 메시지 병합 후 LLM 입력 → 문맥 판단 정확도 향상

**검증 방법**
`settlement_evaluator.py`의 hallucination_detection 지표로 전후 비교 (`[수치 추가 예정]`)

---

### 2. 자연어 정산 명령 불안정

**문제 상황**
`;정산` 명령형 입력은 안정적이었으나 "어제 저녁 정산해줘", "나 빠져" 같은 자연어 요청에서 hint_type 오분류 발생

**원인 가설**
프롬프트가 구체적인 규칙 없이 LLM의 자연어 이해에 의존

**해결 접근**
- 7가지 hint_type을 명시적 패턴과 예시로 프롬프트에 고정 (`n분의1`, `금액대납`, `부담 금액 지정` 등)
- "멤버 수 = member_count일 때 'n명이서 나눠야 함' → n분의1" 같은 조건 규칙 명시
- hint_phrases를 regex로 파싱하는 `parse_hint_phrases_to_settlement`로 LLM 출력 범위를 좁힘

**검증 방법**
7가지 hint_type별 케이스 테스트 셋 구성 (`[케이스 수 추가 예정]`)

---

### 3. 모델 선택 기준 불명확

**문제 상황**
GPT-3.5-turbo와 GPT-4o-mini 사이의 속도/정확도 차이를 감각으로만 판단, 근거 없이 모델 교체

**원인 가설**
정량 비교 기준 없이 체감에만 의존

**해결 접근**
- `service_config.py`에 fast_llm(3.5-turbo) / experimental_llm(4o-mini, default) / accurate_llm(GPT-4) 3단계 명시
- `settlement_evaluator.py`로 동일 테스트셋에 대해 모델별 종합 점수 및 항목별 지표 비교 가능하도록 구조화
- LangChain을 연동해 동일 입력에 대해 모델별 응답을 일괄 수집하고, `settlement_evaluator.py` 지표로 정량 비교 실행
- 비용·응답속도·정확도 3축 기준으로 모델 선택 근거 문서화 (`[지표 추가 예정]`)

---

### 4. 계산 재현성 및 디버깅 어려움

**문제 상황**
정산 계산까지 LLM에 맡겼을 때 같은 입력에서 비율·반올림 결과가 달라지고, 어디서 오류가 발생했는지 추적이 어려움

**원인 가설**
LLM은 확률적 출력 → 동일 입력에도 계산 결과 불일치

**해결 접근**
- LLM 역할을 "추출·구조화"로 제한, 계산은 `calculation_helper.py`의 deterministic 함수로 분리
- hint_phrases → regex 파싱 → 정산 JSON 생성의 파이프라인으로 각 단계를 독립적으로 단위 테스트 가능하게 구성
- 3차 프롬프트(final_prompt) 제거 후 `process_all_results_without_final_prompt`로 단일 경로 통합

**결과**
동일 입력에 대해 항상 같은 정산 결과를 보장, 오류 발생 시 hint_phrases 단계만 확인하면 원인 특정 가능
