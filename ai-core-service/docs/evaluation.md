# 평가 인프라

## 정확도 지표 (`SettlementEvaluator.evaluate_comprehensive()`)

| 지표 | 가중치 | 설명 |
|---|---|---|
| `item_count` | 15% | 추출 항목 수가 정답과 일치하는가 |
| `place_item_similarity` | 5% | 장소·항목명 유사도 |
| `amount_accuracy` | 36% | 금액이 정답 대비 정확한가 |
| `participant_accuracy` | 26% | payer, participants 배정 |
| `hallucination_detection` | 10% | 대화에 없는 항목 생성 여부 |
| `data_completeness` | 5% | 필수 필드(item, amount, payer, participants) 존재 |
| `consistency` | 3% | 내부 중복·ratio 유효성 |

점수 등급: A+ (≥0.95), A (≥0.90), B (≥0.80), C (≥0.70), D (≥0.60), F (<0.60)  
`hallucination_detection` 실패 시 다른 지표와 무관하게 치명적 오류.

---

## LangSmith

- **프로젝트**: `tally-temporary`
- **자동 활성화**: `service_config.py`에서 `LANGSMITH_TRACING=true` 자동 설정
- **확인 가능한 정보**: LLM 입출력, latency, token 사용량

---

## DeepEval / Confident AI

- `utils/advanced_metrics.py`의 `AdvancedSettlementMetrics` 클래스
- 평가 항목: semantic understanding, edge case handling, data quality
- `/api/evaluate-with-processing` 호출 시 점수 자동 업로드
