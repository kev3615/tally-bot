# 아키텍처

## 서비스 개요

**역할**: 카카오톡 등 메신저 대화에서 정산 항목(금액, 참여자, 정산 방식)을 자동 추출  
**기술 스택**: Python 3.10+, FastAPI, LangChain, OpenAI API, LangSmith, DeepEval  
**주요 엔드포인트**:
- `POST /api/process` - 실운영 체인 (simplified chain, 2-stage LLM)
- `POST /api/process-file` - 파일 기반 처리 (샘플 데이터 테스트용)
- `POST /api/evaluate-with-processing` - 실험/평가용 (결과 + DeepEval 점수 반환)

---

## 처리 파이프라인 (Simplified Chain)

```
ConversationRequest
      │
      ▼ 전처리
merge_consecutive_messages()      # 같은 화자 연속 메시지 병합
      │
      ▼ 청킹 판단
사용자 메시지 > 15개? → 10개씩 청크 분리 처리
      │
      ▼
[Stage 1] process_conversation()
  - 기본 모델: gpt-4o-mini (stage1_model 파라미터로 변경 가능)
  - 프롬프트: input_prompt.yaml (prompt_file 파라미터로 변경 가능)
  - 출력: speaker, item, amount, hint_phrases, [currency]
      │
      ▼ 후처리
convert_currency_in_json()        # 외화 → KRW 변환 (하드코딩 환율)
filter_invalid_amounts()          # amount <= 0 제거
      │
      ▼
[Stage 2] process_summary()
  - 기본 모델: gpt-3.5-turbo (stage2_model 파라미터로 변경 가능)
  - 프롬프트: secondary_prompt.yaml
  - 출력: 기존 항목 + place 필드 추가
      │
      ▼ 규칙 기반 파싱 (LLM 미사용)
parse_hint_phrases_to_settlement() # hint_phrases → payer/participants/constants/ratios
      │
      ▼
ConversationResponse { final_result: [...] }
```

> **Stage 3 (`process_final()`)** 은 실운영 체인에서 제외됨.  
> `chain_ai_service.py`의 `process_with_sequential_chain()`에서만 사용 가능 (실험/레거시 목적).

---

## 디렉토리 구조

```
ai-core-service/
├── config/
│   ├── app_config.py          # FastAPI 앱 설정, CORS 미들웨어
│   └── service_config.py      # LLM 인스턴스, API 키 관리, MODEL_REGISTRY
├── handlers/
│   └── process_handler.py     # 체인 오케스트레이션, 청킹, 리소스 로딩
├── services/
│   ├── ai_service.py          # LLM 호출 함수 (process_conversation/summary/final)
│   ├── chain_ai_service.py    # ChainAIService (simplified/sequential 체인)
│   └── result_processor.py    # hint_phrases 파싱, 정산 구조화, 필드 정렬
├── resources/
│   ├── input_prompt.yaml           # 1차 프롬프트 - full 버전 (gpt-3.5 / gpt-4o-mini용)
│   ├── input_prompt_concise.yaml   # 1차 프롬프트 - concise 버전 (gpt-4o / gpt-4.1용)
│   ├── secondary_prompt.yaml       # 2차 프롬프트 - 장소 추출
│   ├── final_prompt.yaml           # 3차 프롬프트 - 정산 구조화 (레거시)
│   └── sample_conversation.json    # 테스트용 샘플 대화
├── utils/
│   ├── settlement_evaluator.py     # 정확도 평가 (SettlementEvaluator)
│   ├── advanced_metrics.py         # DeepEval / Confident AI 연동
│   ├── currency_converter.py       # 외화 → KRW 변환 (하드코딩 환율)
│   ├── json_filter.py              # 유효하지 않은 금액 필터링
│   ├── calculation_helper.py       # 단순 n분의1 정산 구조 생성
│   ├── message_merger.py           # 연속 메시지 병합
│   └── logging_utils.py            # 처리 단계 로깅
├── models/
│   └── conversation.py            # Pydantic 모델 (Request/Response)
├── load/
│   ├── prompt_loader.py           # YAML 프롬프트 로더 (허용 경로 화이트리스트)
│   └── conversation_loader.py     # JSON 대화 파일 로더
└── main.py                        # FastAPI 진입점
```

---

## API 엔드포인트

### POST `/api/process`

실운영 체인. simplified chain(2-stage LLM + 규칙 기반 파싱) 사용.

**Request Body** (`ConversationRequest`):

| 필드 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `chatroom_name` | str | 필수 | 채팅방 이름 |
| `members` | List[Dict] | 필수 | `[{"0": "Alice"}, {"1": "Bob"}]` 형식, 1~50명 |
| `messages` | List[ChatMessage] | 필수 | 최대 500개 |
| `groupId` | int | null | 그룹 식별자 (선택) |
| `stage1_model` | str | `"gpt-4o-mini"` | 1차 LLM (MODEL_REGISTRY 키) |
| `stage2_model` | str | `"gpt-3.5-turbo"` | 2차 LLM |
| `prompt_file` | str | `"resources/input_prompt.yaml"` | 1차 프롬프트 파일 |
| `secondary_prompt_file` | str | `"resources/secondary_prompt.yaml"` | 2차 프롬프트 파일 |
| `final_prompt_file` | str | `"resources/final_prompt.yaml"` | 레거시 (현재 미사용) |

**Response** (`ConversationResponse`):

```json
{
  "final_result": [
    {
      "place": "식당",
      "payer": "0",
      "item": "저녁 식사",
      "amount": 45000,
      "participants": ["0", "1", "2"],
      "constants": {"0": 0, "1": 0, "2": 0},
      "ratios": {"0": 1, "1": 1, "2": 1}
    }
  ]
}
```

**필드 의미**:
- `payer`: 실제 결제한 사람의 member ID
- `participants`: 정산에 포함되는 사람들의 ID 목록
- `constants`: 각 참여자의 고정 부담액 (0이면 ratio 비율로 분배)
- `ratios`: 균등 분배 시 부담 배수 (1이면 동일 금액)

### POST `/api/process-file`

파일에서 대화 데이터를 로드하여 처리. 테스트 및 개발용.

**Query Parameters**:

| 파라미터 | 기본값 |
|---|---|
| `conversation_file` | `"resources/sample_conversation.json"` |
| `stage1_model` | `"gpt-4o-mini"` |
| `stage2_model` | `"gpt-3.5-turbo"` |
| `prompt_file` | `"resources/input_prompt.yaml"` |
| `use_chunking` | `true` |

### POST `/api/evaluate-with-processing`

실험/평가용. `expected_output` 대비 정확도 점수 반환.

**Request Body** (`EvaluationRequest`):

`ConversationRequest`의 모든 필드 + 추가:

| 필드 | 기본값 | 설명 |
|---|---|---|
| `expected_output` | 필수 | 정답 정산 항목 배열 |
| `evaluation_model` | `"gpt-4o"` | DeepEval 평가에 사용할 모델 |
