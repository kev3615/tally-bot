import asyncio
import json
import aiofiles
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

_ALLOWED_DIR = Path(__file__).parent.parent / "resources"
_CACHE_MAX_SIZE = 128

def _validate_path(file_path: str) -> Path:
    resolved = (_ALLOWED_DIR / file_path).resolve()
    if not resolved.is_relative_to(_ALLOWED_DIR.resolve()):
        raise ValueError(f"허용되지 않는 경로: {file_path}")
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
        safe_path = _validate_path(file_path)
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
        async with aiofiles.open(safe_path, 'r', encoding='utf-8') as file:
            content = await file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"대화 파일을 찾을 수 없습니다: {file_path}")

    try:
        json_content = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"대화 파일 JSON 파싱 실패: {file_path} — {e}")

    members = json_content.get('members', [])
    member_count = len(members)

    conversation: List[Dict[str, str]] = [{
        'speaker': 'system',
        'message_content': f"members: {members}\nmember_count: {member_count}"
    }]

    messages = json_content.get('messages', [])
    for i, msg in enumerate(messages):
        speaker = msg.get('speaker')
        message_content = msg.get('message_content')
        if speaker is None or message_content is None:
            raise ValueError(f"messages[{i}]에 'speaker' 또는 'message_content' 필드가 없습니다.")
        conversation.append({'speaker': speaker, 'message_content': message_content})

    return conversation