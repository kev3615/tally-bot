# 프롬프트 버전 관리

## full vs concise 비교

| 항목 | `input_prompt.yaml` (full) | `input_prompt_concise.yaml` (concise) |
|---|---|---|
| 대상 모델 | gpt-3.5-turbo, gpt-4o-mini | gpt-4o, gpt-4.1 |
| 라인 수 | ~415라인 | ~130라인 |
| 예시 수 | 패턴당 2-4개 | 패턴당 1개 |
| 반복 경고 블록 | 다수 (`⚠️`) | 제거 |

---

## 허용된 프롬프트 파일 (화이트리스트)

`load/prompt_loader.py`의 `_ALLOWED_PROMPT_FILES`에 등록된 파일만 로드 가능:

```
resources/input_prompt.yaml
resources/input_prompt_concise.yaml
resources/secondary_prompt.yaml
resources/final_prompt.yaml
```

---

## 새 프롬프트 버전 추가 시 절차

1. `resources/input_prompt_<버전명>.yaml` 생성
2. `load/prompt_loader.py`의 `_ALLOWED_PROMPT_FILES` 셋에 경로 추가
3. `docs/prompts.md`의 버전 비교 표 업데이트
4. `/api/evaluate-with-processing` 호출 시 `prompt_file` 파라미터로 지정
