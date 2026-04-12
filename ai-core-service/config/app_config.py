import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    """FastAPI 앱 생성 및 설정"""
    is_production = os.getenv("APP_ENV", "development") == "production"
    raw_origins = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080"
    )
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

    if is_production and os.getenv("ALLOWED_ORIGINS") is None:
        raise RuntimeError(
            "ALLOWED_ORIGINS must be explicitly set in production. "
            "Refusing to start with localhost CORS defaults."
        )
    if not allowed_origins:
        raise RuntimeError(
            "ALLOWED_ORIGINS resolved to an empty list. Check the env var value."
        )

    servers = [{"url": "http://localhost:8000", "description": "Development server"}]
    if prod_url := os.getenv("API_BASE_URL"):
        servers.append({"url": prod_url, "description": "Production server"})

    app = FastAPI(
        title="Tally Bot AI Core Service",
        description="""
        ## 정산 대화 분석 및 처리 API

        이 API는 다음 기능을 제공합니다:

        ### 🎯 주요 기능
        - **대화 분석**: 정산 관련 대화에서 항목별 금액 추출
        - **다중 처리 방식**: 단일 처리, 체인 처리, 파일 기반 처리
        - **평가 시스템**: 추출 결과의 정확도 평가

        ### 💡 사용법
        1. `/api/process` - 실시간 대화 데이터 처리
        2. `/api/process-file` - JSON 파일 기반 처리
        3. `/api/process-chain` - 최적화된 체인 방식 처리
        4. `/api/evaluate-with-processing` - 결과 평가

        ### 📊 지원 기능
        - 한국어 복합 금액 처리 (47만 8천원 → 478000)
        - 외화 처리 (19유로 → 19 EUR)
        - 정산 방식 분류 (n분의1, 금액대납, 고정+n분의1)
        """,
        version="1.0.0",
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
        servers=servers,
    )

    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )

    return app
