import logging
from pathlib import Path
from typing import Any

import aiofiles
import yaml

logger = logging.getLogger(__name__)

# resources/ 디렉터리 기준 경로 (이 파일 기준 한 단계 위)
_RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"

# 허용된 프롬프트 파일 목록 (allowlist)
_ALLOWED_PROMPT_FILES = {
    "resources/input_prompt.yaml",
    "resources/input_prompt_concise.yaml",
    "resources/secondary_prompt.yaml",
    "resources/final_prompt.yaml",
}

# 캐시 딕셔너리 (모듈 내부 전용)
_prompt_cache: dict = {}


def _validate_prompt_path(file_path: str) -> Path:
    """허용된 프롬프트 파일인지 검증하고 절대 경로를 반환합니다."""
    if file_path not in _ALLOWED_PROMPT_FILES:
        logger.warning(
            "허용되지 않은 프롬프트 파일 요청: '%s'. 허용 목록: %s",
            file_path,
            sorted(_ALLOWED_PROMPT_FILES),
        )
        raise ValueError(f"허용되지 않은 프롬프트 파일입니다: '{file_path}'")
    resolved = (_RESOURCES_DIR.parent / file_path).resolve()
    if not resolved.is_relative_to(_RESOURCES_DIR):
        raise ValueError(f"경로 탐색 시도가 감지되었습니다: '{file_path}'")
    return resolved


async def load_prompt(file_path: str) -> dict[str, Any]:
    """프롬프트 파일을 비동기로 로드하고 캐시하는 함수"""
    if file_path in _prompt_cache:
        return _prompt_cache[file_path]

    validated_path = _validate_prompt_path(file_path)

    try:
        async with aiofiles.open(validated_path, "r", encoding="utf-8") as file:
            content = await file.read()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"프롬프트 파일을 찾을 수 없습니다: '{file_path}'. "
            f"resources/ 디렉터리에 파일이 존재하는지 확인하세요."
        )
    prompt = yaml.safe_load(content)
    if not isinstance(prompt, dict):
        raise ValueError(
            f"프롬프트 파일 '{file_path}'의 최상위 구조가 dict가 아닙니다: {type(prompt)}"
        )
    _prompt_cache[file_path] = prompt
    return prompt


def clear_prompt_cache() -> None:
    """프롬프트 캐시를 초기화합니다. YAML 파일이 변경된 경우에만 사용하세요."""
    _prompt_cache.clear()
