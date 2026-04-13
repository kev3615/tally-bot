import asyncio
import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

import aiofiles

_RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"
_CACHE_MAX_SIZE = 128

_ALLOWED_CONVERSATION_FILES = {
    "resources/sample_conversation.json",
}


def _validate_conversation_path(file_path: str) -> Path:
    """허용된 대화 파일인지 검증하고 절대 경로를 반환합니다."""
    if file_path not in _ALLOWED_CONVERSATION_FILES:
        raise ValueError(
            f"허용되지 않은 대화 파일입니다: '{file_path}'. "
            f"허용 목록: {sorted(_ALLOWED_CONVERSATION_FILES)}"
        )
    resolved = (_RESOURCES_DIR.parent / file_path).resolve()
    if not resolved.is_relative_to(_RESOURCES_DIR):
        raise ValueError(f"경로 탐색 시도가 감지되었습니다: '{file_path}'")
    return resolved


# LRU 캐시 (최대 128개 항목)
_conversation_cache: OrderedDict[str, List[Dict[str, str]]] = OrderedDict()
_cache_lock = asyncio.Lock()
_in_flight: Dict[str, asyncio.Future] = {}


async def load_conversation(file_path: str) -> List[Dict[str, str]]:
    """대화 내용을 비동기로 로드하고 캐시하는 함수"""
    async with _cache_lock:
        if file_path in _conversation_cache:
            _conversation_cache.move_to_end(file_path)
            return _conversation_cache[file_path]

        if file_path in _in_flight:
            future = _in_flight[file_path]
        else:
            future = asyncio.get_event_loop().create_future()
            _in_flight[file_path] = future

    if not future.done():
        safe_path = _validate_conversation_path(file_path)
        result = await _load_from_disk(safe_path, file_path)
        async with _cache_lock:
            _conversation_cache[file_path] = result
            _conversation_cache.move_to_end(file_path)
            if len(_conversation_cache) > _CACHE_MAX_SIZE:
                _conversation_cache.popitem(last=False)
            _in_flight.pop(file_path, None)
            future.set_result(result)
        return result

    return await future


async def _load_from_disk(safe_path: Path, file_path: str) -> List[Dict[str, str]]:
    try:
        async with aiofiles.open(safe_path, "r", encoding="utf-8") as file:
            content = await file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"대화 파일을 찾을 수 없습니다: {file_path}")

    try:
        json_content = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"대화 파일 JSON 파싱 실패: {file_path} — {e}")

    members = json_content.get("members", [])
    member_count = len(members)

    conversation: List[Dict[str, str]] = [
        {
            "speaker": "system",
            "message_content": f"members: {json.dumps(members, ensure_ascii=False)}\nmember_count: {member_count}",
        }
    ]

    messages = json_content.get("messages", [])
    for i, msg in enumerate(messages):
        speaker = msg.get("speaker")
        message_content = msg.get("message_content")
        if speaker is None or message_content is None:
            raise ValueError(
                f"messages[{i}]에 'speaker' 또는 'message_content' 필드가 없습니다."
            )
        conversation.append({"speaker": speaker, "message_content": message_content})

    return conversation
