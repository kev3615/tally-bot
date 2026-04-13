# 실험 설계

## 실험 매트릭스 (EXP-A ~ EXP-F)

| 실험 ID | stage1_model | prompt_file | stage2_model | 목적 |
|---|---|---|---|---|
| EXP-A | gpt-3.5-turbo | full | gpt-3.5-turbo | **현재 기준선** |
| EXP-B | gpt-4o-mini | full | gpt-3.5-turbo | 모델 업그레이드 단독 효과 |
| EXP-C | gpt-4o-mini | concise | gpt-3.5-turbo | 프롬프트 단축 효과 (중간 모델) |
| EXP-D | gpt-4o | full | gpt-3.5-turbo | 고성능 모델 + full 프롬프트 |
| EXP-E | gpt-4o | concise | gpt-3.5-turbo | **핵심 실험**: 고성능 + 단축 조합 |
| EXP-F | gpt-4.1 | concise | gpt-3.5-turbo | 최신 모델 성능 측정 |

> **핵심 비교**: EXP-D vs EXP-E — 동일 모델(gpt-4o)에서 full/concise 정확도가 동등하면 concise 유효성 입증.

---

## 실험 실행 예시

```bash
# EXP-A: 기준선
curl -X POST http://localhost:8000/api/evaluate-with-processing \
  -H "Content-Type: application/json" \
  -d '{
    "stage1_model": "gpt-3.5-turbo",
    "stage2_model": "gpt-3.5-turbo",
    "prompt_file": "resources/input_prompt.yaml",
    "chatroom_name": "테스트",
    "members": [{"0": "Alice"}, {"1": "Bob"}],
    "messages": [...],
    "expected_output": [...]
  }'

# EXP-E: 핵심 실험
curl -X POST http://localhost:8000/api/evaluate-with-processing \
  -H "Content-Type: application/json" \
  -d '{
    "stage1_model": "gpt-4o",
    "stage2_model": "gpt-3.5-turbo",
    "prompt_file": "resources/input_prompt_concise.yaml",
    "chatroom_name": "테스트",
    "members": [{"0": "Alice"}, {"1": "Bob"}],
    "messages": [...],
    "expected_output": [...]
  }'
```
