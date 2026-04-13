# 로컬 개발 환경 설정

## 필수 환경 변수 (`.env` 파일)

```
OPENAI_API_KEY=sk-...
LANGSMITH_API_KEY=ls__...
DEEP_EVAL_API_KEY=...        # 또는 CONFIDENT_API_KEY
```

로드 우선순위: `.env` → OS 환경 변수 → AWS Secrets Manager (`prod/AppBeta/apikey`)  
일부만 설정된 경우 에러 발생 (혼용 방지). 초기화 실패 시 `SystemExit`.

---

## 선택적 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `APP_ENV` | `"development"` | `"production"` 설정 시 Swagger UI 비활성화 |
| `ALLOWED_ORIGINS` | `"http://localhost:3000,http://localhost:8080"` | CORS 허용 오리진 (쉼표 구분) |
| `API_BASE_URL` | - | 운영 서버 URL |

---

## 실행 명령

```bash
# 의존성 설치
pip install -r requirements.txt

# 평가 기능 포함 설치
pip install -r requirements-eval.txt

# 개발 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# API 문서 확인
open http://localhost:8000/docs
```
