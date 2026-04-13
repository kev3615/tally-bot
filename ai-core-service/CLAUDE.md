# AI Core Service - 개발 가이드

정산 대화를 분석하여 정산 항목을 추출하는 FastAPI 서비스.
GPT 모델별 정확도·latency·비용 비교 실험을 위한 설계 문서 포함.

---

## 빠른 시작

```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

필수 환경 변수: `OPENAI_API_KEY`, `LANGSMITH_API_KEY`, `DEEP_EVAL_API_KEY`  
→ 상세 설정: [docs/setup.md](docs/setup.md)

---

## 문서 인덱스

| 문서 | 내용 |
|---|---|
| [docs/architecture.md](docs/architecture.md) | 서비스 개요, 처리 파이프라인, 디렉토리 구조, API 엔드포인트 |
| [docs/models.md](docs/models.md) | MODEL_REGISTRY, 단계별 권장 모델, 비용 참고 |
| [docs/prompts.md](docs/prompts.md) | full vs concise 비교, 화이트리스트, 새 버전 추가 절차 |
| [docs/experiments.md](docs/experiments.md) | 실험 매트릭스 (EXP-A ~ EXP-F), 실행 예시 |
| [docs/evaluation.md](docs/evaluation.md) | 정확도 지표, LangSmith, DeepEval |
| [docs/setup.md](docs/setup.md) | 환경 변수, 실행 명령 |
| [docs/known-issues.md](docs/known-issues.md) | 외화 처리, 금액 방향 오류, 청킹, 보안 주의사항 |

---

## 핵심 정보 요약

**처리 흐름**: `ConversationRequest` → 전처리 → Stage 1 (항목 추출) → 후처리 → Stage 2 (장소 추출) → 규칙 기반 파싱 → `ConversationResponse`

**기본 모델**: Stage 1 `gpt-4o-mini` / Stage 2 `gpt-3.5-turbo`

**실험 핵심**: EXP-D vs EXP-E — gpt-4o에서 full/concise 프롬프트 정확도 비교

**주의**: `hallucination_detection` 실패 시 치명적 오류. 프롬프트 추가 시 `_ALLOWED_PROMPT_FILES` 등록 필수.
