from pathlib import Path
from typing import Any, Dict

import aiofiles
import yaml

# resources/ 디렉터리 기준 경로 (이 파일 기준 한 단계 위)
_RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"

# 허용된 프롬프트 파일 목록 (allowlist)
_ALLOWED_PROMPT_FILES = {
    "resources/input_prompt.yaml",
    "resources/input_prompt_concise.yaml",
    "resources/secondary_prompt.yaml",
    "resources/final_prompt.yaml",
}

# 캐시 딕셔너리
prompt_cache = {}


def _validate_prompt_path(file_path: str) -> Path:
    """허용된 프롬프트 파일인지 검증하고 절대 경로를 반환합니다."""
    if file_path not in _ALLOWED_PROMPT_FILES:
        raise ValueError(
            f"허용되지 않은 프롬프트 파일입니다: '{file_path}'. "
            f"허용 목록: {sorted(_ALLOWED_PROMPT_FILES)}"
        )
    resolved = (_RESOURCES_DIR.parent / file_path).resolve()
    if not resolved.is_relative_to(_RESOURCES_DIR):
        raise ValueError(f"경로 탐색 시도가 감지되었습니다: '{file_path}'")
    return resolved


async def load_prompt(file_path: str) -> Dict[str, Any]:
    """프롬프트 파일을 비동기로 로드하고 캐시하는 함수"""
    if file_path in prompt_cache:
        return prompt_cache[file_path]

    validated_path = _validate_prompt_path(file_path)

    async with aiofiles.open(validated_path, "r", encoding="utf-8") as file:
        content = await file.read()
        prompt = yaml.safe_load(content)
        prompt_cache[file_path] = prompt
        return prompt
