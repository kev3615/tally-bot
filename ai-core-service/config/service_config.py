import json
import logging
import os
from pathlib import Path

import boto3
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 프로젝트 루트의 .env 로드 (이미 설정된 환경 변수는 덮어쓰지 않음)
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def get_secret(secret_name="prod/AppBeta/apikey", region_name="ap-northeast-2"):
    """AWS Secrets Manager에서 시크릿 값을 가져옵니다."""
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


def _secrets_from_dotenv_or_env():
    """
    .env / OS 환경 변수에서 API 키를 읽습니다.
    일부만 설정된 경우 AWS와 섞이지 않도록 오류로 처리합니다.
    """
    openai = os.getenv("OPENAI_API_KEY")
    langsmith = os.getenv("LANGSMITH_API_KEY")
    deepeval = os.getenv("DEEP_EVAL_API_KEY") or os.getenv("CONFIDENT_API_KEY")

    if openai and langsmith and deepeval:
        return {
            "OpenAI": openai,
            "Langsmith": langsmith,
            "DeepEval": deepeval,
        }

    if openai or langsmith or deepeval:
        missing = []
        if not openai:
            missing.append("OPENAI_API_KEY")
        if not langsmith:
            missing.append("LANGSMITH_API_KEY")
        if not deepeval:
            missing.append("DEEP_EVAL_API_KEY 또는 CONFIDENT_API_KEY")
        raise EnvironmentError(
            ".env 또는 환경 변수에 API 키가 일부만 설정되어 있습니다. "
            f"다음을 모두 설정해 주세요: {', '.join(missing)}"
        )

    return None


def _apply_secrets(secrets: dict) -> dict:
    """시크릿 dict를 os.environ에 반영하고 검증용 dict를 반환합니다."""
    required_env_vars = {
        "OPENAI_API_KEY": secrets.get("OpenAI"),
        "LANGSMITH_API_KEY": secrets.get("Langsmith"),
        "DEEP_EVAL_API_KEY": secrets.get("DeepEval"),
    }

    missing_vars = [var for var, value in required_env_vars.items() if not value]
    if missing_vars:
        raise EnvironmentError(f"필수 값이 누락되었습니다: {', '.join(missing_vars)}")

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGSMITH_API_KEY"] = required_env_vars["LANGSMITH_API_KEY"]
    os.environ["LANGSMITH_PROJECT"] = "tally-temporary"
    os.environ["OPENAI_API_KEY"] = required_env_vars["OPENAI_API_KEY"]
    os.environ["DEEP_EVAL_API_KEY"] = required_env_vars["DEEP_EVAL_API_KEY"]
    os.environ["CONFIDENT_API_KEY"] = required_env_vars["DEEP_EVAL_API_KEY"]

    return required_env_vars


def initialize_environment():
    """환경 변수 검증 및 설정 (.env 우선, 없으면 AWS Secrets Manager)."""
    try:
        secrets = _secrets_from_dotenv_or_env()
        if secrets is not None:
            return _apply_secrets(secrets)

        secrets = get_secret("prod/AppBeta/apikey")
        return _apply_secrets(secrets)

    except EnvironmentError:
        raise
    except Exception as e:
        raise EnvironmentError(
            "시크릿을 불러오지 못했습니다. 프로젝트 루트에 .env를 두고 "
            "OPENAI_API_KEY, LANGSMITH_API_KEY, DEEP_EVAL_API_KEY(또는 CONFIDENT_API_KEY)를 설정하거나, "
            f"AWS Secrets Manager 연결을 확인하세요. 상세: {e}"
        ) from e


def get_api_keys():
    """설정된 API 키들을 반환합니다"""
    return {
        "openai": os.getenv("OPENAI_API_KEY"),
        "langsmith": os.getenv("LANGSMITH_API_KEY"),
        "deepeval": os.getenv("CONFIDENT_API_KEY"),
        "deep_eval": os.getenv("DEEP_EVAL_API_KEY"),  # 호환성을 위해 유지
    }


def ensure_api_key(service_name: str) -> str:
    """특정 서비스의 API 키가 설정되어 있는지 확인하고 반환합니다"""
    api_keys = get_api_keys()

    if service_name.lower() == "openai":
        key = api_keys["openai"]
        if not key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        return key
    elif service_name.lower() in ["deepeval", "confident"]:
        key = api_keys["deepeval"]
        if not key:
            raise ValueError("DeepEval (Confident AI) API 키가 설정되지 않았습니다.")
        return key
    elif service_name.lower() == "langsmith":
        key = api_keys["langsmith"]
        if not key:
            raise ValueError("LangSmith API 키가 설정되지 않았습니다.")
        return key
    else:
        raise ValueError(f"알 수 없는 서비스: {service_name}")


# 환경 변수 초기화
try:
    env_vars = initialize_environment()
except Exception as e:
    logging.critical("환경 변수 초기화 실패 — 서비스를 시작할 수 없습니다: %s", e)
    raise SystemExit(1) from e

# 빠른 모델(GPT-3.5) - 2차(장소 추출) 등 단순 작업용
fast_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.0)

# 실험용 모델(GPT-4o-mini) - 현재 실험 기준선
experimental_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

# 레거시 기준점(GPT-4) - 구버전 비교용으로 보존
accurate_llm = ChatOpenAI(model="gpt-4", temperature=0.0)

# 고성능 모델(GPT-4o) - concise 프롬프트와 조합 실험용
gpt4o_llm = ChatOpenAI(model="gpt-4o", temperature=0.0)

# 최신 모델(GPT-4.1) - 최신 성능 측정용
gpt41_llm = ChatOpenAI(model="gpt-4.1", temperature=0.0)

# 최고 성능 모델(GPT-4.5) - 최상위 정확도 측정용
gpt45_llm = ChatOpenAI(model="gpt-4.5-preview", temperature=0.0)

# 실험 레지스트리: 모델명 → 인스턴스 (평가 엔드포인트에서 동적 선택용)
MODEL_REGISTRY = {
    "gpt-3.5-turbo": fast_llm,
    "gpt-4o-mini": experimental_llm,
    "gpt-4": accurate_llm,
    "gpt-4o": gpt4o_llm,
    "gpt-4.1": gpt41_llm,
    "gpt-4.5-preview": gpt45_llm,
}

# 기본 모델은 실험을 위해 GPT-4o-mini 사용
llm = experimental_llm
