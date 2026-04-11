# AI Core Service - 개발 가이드

정산 대화를 분석하여 정산 항목을 추출하는 FastAPI 서비스.
GPT 모델별 정확도·latency·비용 비교 실험을 위한 설계 문서 포함.

---

## 1. 서비스 개요

**역할**: 카카오톡 등 메신저 대화에서 정산 항목(금액, 참여자, 정산 방식)을 자동 추출  
**기술 스택**: Python 3.10+, FastAPI, LangChain, OpenAI API, LangSmith, DeepEval  
**주요 엔드포인트**:
- `POST /api/process` - 실운영 체인 (simplified chain)
- `POST /api/evaluate-with-processing` - 실험/평가용 (결과 + DeepEval 점수 반환)

---

## 2. 아키텍처

### 3단계 처리 체인

```
ConversationRequest
      │
      ▼
[1차] process_conversation()
  - 모델: fast_llm (현재 gpt-3.5-turbo)
  - 프롬프트: input_prompt.yaml
  - 출력: speaker, item, amount, hint_phrases
      │
      ▼
[2차] process_summary()
  - 모델: fast_llm
  - 프롬프트: secondary_prompt.yaml
  - 출력: item + place (장소 추출)
      │
      ▼
ConversationResponse (final_result)
```

> **참고**: 3차 `process_final()`은 현재 실운영 체인에서 제외됨 (규칙 파서로 대체).
> 복잡 케이스 fallback 또는 실험 목적으로만 사용.

### 디렉토리 구조

```
ai-core-service/
├── config/
│   ├── app_config.py          # FastAPI 앱 설정, CORS
│   └── service_config.py      # 모델 인스턴스, API 키 관리
├── handlers/
│   └── process_handler.py     # 체인 오케스트레이션, 청킹 로직
├── services/
│   ├── ai_service.py          # LLM 호출 함수 (process_conversation/summary/final)
│   └── chain_ai_service.py    # simplified/sequential 체인 구현
├── resources/
│   ├── input_prompt.yaml           # 1차 프롬프트 - full 버전 (gpt-3.5 / gpt-4o-mini용)
│   ├── input_prompt_concise.yaml   # 1차 프롬프트 - concise 버전 (gpt-4o / gpt-4.1용)
│   ├── secondary_prompt.yaml       # 2차 프롬프트 - 장소 추출
│   └── final_prompt.yaml           # 3차 프롬프트 - 정산 구조화 (레거시)
├── utils/
│   ├── settlement_evaluator.py    # 정확도 평가 (SettlementEvaluator)
│   └── advanced_metrics.py        # GEval / DeepEval 연동
├── models/
│   └── conversation.py            # Pydantic 모델 (Request/Response)
└── main.py                        # FastAPI 진입점
```

---

## 3. 모델 티어 정의

### 5티어 모델 구성 (`config/service_config.py`)

| 변수명 | 모델 | 용도 |
|---|---|---|
| `fast_llm` | gpt-3.5-turbo | 단순 구조 변환, 2차(장소 추출)에 충분 |
| `experimental_llm` | gpt-4o-mini | 현재 실험 기준선. 1차 추출에 사용 |
| `accurate_llm` | gpt-4 | 레거시 기준점 보존용 |
| `gpt4o_llm` | gpt-4o | 고성능 실험용. concise 프롬프트와 조합 |
| `gpt41_llm` | gpt-4.1 | 최신 모델 실험용 |
| `gpt45_llm` | gpt-4.5-preview | 최상위 정확도 측정용 |

### MODEL_REGISTRY 사용법

```python
from config.service_config import MODEL_REGISTRY

# 모델명으로 인스턴스 조회
llm = MODEL_REGISTRY["gpt-4o"]

# 평가 엔드포인트에서 stage1_model 파라미터로 동적 선택 예정
```

### 단계별 모델 배정 기준

| 단계 | 난이도 | 권장 모델 | 이유 |
|---|---|---|---|
| 1차 (항목 추출) | **높음** | gpt-4o-mini 이상 | 7패턴 판별, 화살표 방향, 금액 변환 복합 작업. 오류가 하위 단계로 전파됨 |
| 2차 (장소 추출) | 낮음 | gpt-3.5-turbo | 단순 분류. 고성능 모델 사용은 낭비 |
| 3차 (정산 구조화) | 중간 | gpt-4o-mini 이상 | 규칙 기반 변환. 복잡 케이스 fallback용 |

---

## 4. 프롬프트 버전 관리

### full vs concise 버전 비교

| 항목 | full (`input_prompt.yaml`) | concise (`input_prompt_concise.yaml`) |
|---|---|---|
| 대상 모델 | gpt-3.5-turbo, gpt-4o-mini | gpt-4o, gpt-4.1 |
| 라인 수 | ~415라인 | ~130라인 |
| 예시 수 | 패턴당 2-4개 | 패턴당 1개 |
| 반복 경고 | 다수 (`⚠️` 블록) | 제거 |
| 키워드 열거 | 포함 | 제거 |

### concise 버전에서 제거한 내용

- 금액대납 화살표 방향 "절대 실수하지 말 것" 경고 블록
- 부담금액 추가 예시 + 패턴 인식 키워드 열거 3개 섹션
- "십만원 단위 처리 흔한 실수" 섹션 (공식 한 줄로 대체)
- 금액대납 예시 4개 → 1개로 축소
- 제외항목 구분 예시 3개 → 1개로 축소

### concise 버전에서 반드시 유지한 내용

- 절대 추출 금지 4카테고리 (감정/불확실/미래계획/전달표현)
- 7가지 hint_phrases 패턴 규격 (형식 계약)
- JSON 출력 스키마 (원화/외화 두 형식)
- 금액 변환 공식: `"XX만 Y천원" = XX × 10000 + Y × 1000`
- 외화 처리 규칙 (절대 원화로 변환 금지)
- 패턴별 예시 각 1개

### 새 프롬프트 버전 추가 시 절차

1. `resources/` 하위에 `input_prompt_<버전명>.yaml` 파일 생성
2. 이 문서의 버전 비교 표 업데이트
3. `/api/evaluate-with-processing` 호출 시 `prompt_file` 파라미터로 지정

---

## 5. 실험 설계

### 실험 매트릭스 (EXP-A ~ EXP-F)

| 실험 ID | 1차 모델 | 1차 프롬프트 | 2차 모델 | 목적 |
|---|---|---|---|---|
| EXP-A | gpt-3.5-turbo | full | gpt-3.5-turbo | **현재 기준선** |
| EXP-B | gpt-4o-mini | full | gpt-3.5-turbo | 모델 업그레이드 단독 효과 측정 |
| EXP-C | gpt-4o-mini | concise | gpt-3.5-turbo | 프롬프트 단축 효과 (중간 모델) |
| EXP-D | gpt-4o | full | gpt-3.5-turbo | 고성능 모델 + full 프롬프트 |
| EXP-E | gpt-4o | concise | gpt-3.5-turbo | **핵심 실험**: 고성능 + 단축 조합 |
| EXP-F | gpt-4.1 | concise | gpt-3.5-turbo | 최신 모델 성능 측정 |

> **핵심 비교**: EXP-D vs EXP-E  
> 동일 모델(gpt-4o)에서 full/concise 정확도 차이가 없거나 concise가 동등하면,
> 고성능 모델에서 프롬프트 단축이 유효함을 입증.

### 측정 지표

**정확도** (`utils/settlement_evaluator.py`의 `SettlementEvaluator`):
- `item_count`: 추출된 항목 수가 정답과 일치하는가
- `amount_accuracy`: 금액이 정답 대비 5% 이내인가
- `participant_accuracy`: participants, payer 배정이 맞는가
- `hallucination_detection`: 대화에 없는 항목을 생성했는가
- `overall_score`: 가중 평균

**Latency**:
- 1차 LLM 호출 시간 (ms)
- 전체 체인 시간 (ms)
- 측정: LangSmith trace의 `start_time` / `end_time` 활용

**비용** (LangSmith trace의 `token_usage` 메타데이터):

| 모델 | 입력 (per 1M tokens) | 출력 (per 1M tokens) |
|---|---|---|
| gpt-3.5-turbo | $0.50 | $1.50 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4.1 | $2.00 | $8.00 |
| gpt-4.5-preview | $75.00 | $150.00 |
| gpt-4 | $30.00 | $60.00 |

*(2026년 4월 기준 참고 단가. OpenAI 공식 가격 페이지에서 최신 확인 필요)*  
> **주의**: gpt-4.5-preview는 비용이 매우 높으므로 소량 샘플로만 실험 권장.

### 실험 실행 방법

`/api/evaluate-with-processing` 엔드포인트에서 `stage1_model`, `stage2_model`, `prompt_file`을 조합하여 실험 실행.

**요청 Body 파라미터:**
| 파라미터 | 기본값 | 설명 |
|---|---|---|
| `stage1_model` | `"gpt-4o-mini"` | 1차 처리 모델 (MODEL_REGISTRY 키) |
| `stage2_model` | `"gpt-3.5-turbo"` | 2차 처리 모델 (장소 추출, 단순 작업) |
| `prompt_file` | `"resources/input_prompt.yaml"` | 1차 프롬프트 버전 |

```bash
# EXP-A: 기준선 (gpt-3.5 + full 프롬프트)
curl -X POST http://localhost:8000/api/evaluate-with-processing \
  -H "Content-Type: application/json" \
  -d '{
    "stage1_model": "gpt-3.5-turbo",
    "stage2_model": "gpt-3.5-turbo",
    "prompt_file": "resources/input_prompt.yaml",
    "chatroom_name": "테스트",
    "members": [...],
    "messages": [...],
    "expected_output": [...]
  }'

# EXP-E: 핵심 실험 (gpt-4o + concise 프롬프트)
curl -X POST http://localhost:8000/api/evaluate-with-processing \
  -H "Content-Type: application/json" \
  -d '{
    "stage1_model": "gpt-4o",
    "stage2_model": "gpt-3.5-turbo",
    "prompt_file": "resources/input_prompt_concise.yaml",
    ...
  }'

# EXP-F: 최신 모델 (gpt-4.1 + concise)
curl -X POST http://localhost:8000/api/evaluate-with-processing \
  -H "Content-Type: application/json" \
  -d '{
    "stage1_model": "gpt-4.1",
    "stage2_model": "gpt-3.5-turbo",
    "prompt_file": "resources/input_prompt_concise.yaml",
    ...
  }'
```

**사용 가능한 `stage1_model` 값**: `"gpt-3.5-turbo"`, `"gpt-4o-mini"`, `"gpt-4"`, `"gpt-4o"`, `"gpt-4.1"`

---

## 6. 평가 인프라

### LangSmith

- **프로젝트 이름**: `tally-temporary`
- **트레이싱 자동 활성화**: `service_config.py`에서 `LANGSMITH_TRACING=true` 설정
- **확인 가능한 정보**: 각 LLM 호출의 입력/출력, latency, token 사용량

### DeepEval / Confident AI

- `utils/advanced_metrics.py`의 `evaluate_advanced_metrics()` 함수
- `/api/evaluate-with-processing` 엔드포인트 호출 시 자동 점수 업로드
- 대시보드에서 실험 ID별 점수 비교 가능

### SettlementEvaluator 점수 해석

- `overall_score` 0.8 이상: 양호
- `hallucination_detection` 실패 시 다른 지표와 무관하게 치명적 오류로 분류

---

## 7. 로컬 개발 환경 설정

### 필수 환경 변수 (`.env` 파일)

```
OPENAI_API_KEY=sk-...
LANGSMITH_API_KEY=ls__...
DEEP_EVAL_API_KEY=...        # 또는 CONFIDENT_API_KEY
```

모두 설정되어 있지 않으면 AWS Secrets Manager(`prod/AppBeta/apikey`)에서 자동 조회.  
일부만 설정된 경우 에러 발생 (혼용 방지).

### 실행 명령

```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# API 문서 확인
open http://localhost:8000/docs
```

### 테스트 데이터

- `resources/sample_conversation.json`: 샘플 대화 데이터

---

## 8. 알려진 이슈 및 주의사항

### 금액 방향 오류 (gpt-3.5-turbo에서 빈번)

`"허원혁 25000 보내라"` (speaker: "2") → 화살표 방향 오류 발생 가능.  
올바른 해석: `허원혁 → speaker(2)` (허원혁이 나에게 보냄)  
잘못된 해석: `speaker(2) → 허원혁` ← gpt-3.5에서 종종 역방향 생성

### 외화 변환 금지

외화 금액은 절대 원화로 변환하지 않음.  
`"택시비 23유로"` → `amount: 23` + `currency: "EUR"` (23000으로 변환 금지)

### 중복 요청 방지 현재 비활성화

`main.py`의 `generate_request_hash()`에 `time.time()` + 랜덤값 포함 → 매번 다른 해시 생성.  
실운영 배포 시에는 이 부분을 제거하여 실제 중복 방지 활성화 필요.

### 긴 대화 청킹

15개 이상의 사용자 메시지가 포함된 대화는 10개씩 청크 분리 후 처리.  
청킹 로직: `handlers/process_handler.py`의 `process_conversation_logic()`
