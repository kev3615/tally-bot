# 모델 구성

## MODEL_REGISTRY (`config/service_config.py`)

| 키 | 모델 | 용도 |
|---|---|---|
| `"gpt-3.5-turbo"` | gpt-3.5-turbo | Stage 2 기본 (장소 추출, 단순 작업) |
| `"gpt-4o-mini"` | gpt-4o-mini | Stage 1 기본 (항목 추출) |
| `"gpt-4"` | gpt-4 | 레거시 기준점 |
| `"gpt-4o"` | gpt-4o | 고성능 실험용 |
| `"gpt-4.1"` | gpt-4.1 | 최신 모델 실험용 |
| `"gpt-4.5-preview"` | gpt-4.5-preview | 최상위 정확도 측정용 (비용 주의) |

모든 모델은 `temperature=0.0`으로 초기화.

```python
from config.service_config import MODEL_REGISTRY
llm = MODEL_REGISTRY["gpt-4o"]
```

---

## 단계별 권장 모델

| 단계 | 난이도 | 권장 모델 | 이유 |
|---|---|---|---|
| Stage 1 (항목 추출) | 높음 | gpt-4o-mini 이상 | 7패턴 판별, 화살표 방향, 금액 변환 복합 작업. 오류 하위 전파됨 |
| Stage 2 (장소 추출) | 낮음 | gpt-3.5-turbo | 단순 분류. 고성능 모델은 낭비 |
| Stage 3 (구조화, 레거시) | 중간 | gpt-4o-mini 이상 | 복잡 케이스 fallback용 |

---

## 비용 참고 (2026년 4월 기준)

| 모델 | 입력 (per 1M tokens) | 출력 (per 1M tokens) |
|---|---|---|
| gpt-3.5-turbo | $0.50 | $1.50 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4.1 | $2.00 | $8.00 |
| gpt-4.5-preview | $75.00 | $150.00 |
| gpt-4 | $30.00 | $60.00 |

*(OpenAI 공식 가격 페이지에서 최신 확인 필요)*  
> **주의**: gpt-4.5-preview는 소량 샘플로만 실험 권장.
