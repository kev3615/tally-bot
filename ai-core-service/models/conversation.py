from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional

from load.prompt_loader import _ALLOWED_PROMPT_FILES


def _validate_prompt_file(value: str) -> str:
    if value not in _ALLOWED_PROMPT_FILES:
        raise ValueError(f"허용되지 않은 프롬프트 파일입니다: '{value}'")
    return value

# FastAPI와 Pydantic을 사용하여 데이터 모델을 정의합니다.
# Pydantic 모델은 자동 데이터 검증, 직렬화/역직렬화를 제공하여 
# FastAPI에서 요청과 응답 데이터를 처리하는 데 사용됩니다.

class ChatMessage(BaseModel):
    # 개별 채팅 메시지 모델 - FastAPI가 요청에서 자동으로 파싱하고 검증합니다.
    unique_chat_id: Optional[str] = None
    speaker: str
    message_content: str
    timestamp: Optional[str] = None

class ConversationRequest(BaseModel):
    # API 요청 모델 - FastAPI 엔드포인트에서 request: ConversationRequest 형태로 사용됩니다.
    # FastAPI는 수신된 JSON을 자동으로 이 모델로 변환하고 검증합니다.
    groupId: Optional[int] = None
    chatroom_name: str
    members: List[Dict[str, str]] = Field(min_length=1, max_length=50)
    messages: List[ChatMessage] = Field(min_length=1, max_length=500)
    prompt_file: str = "resources/input_prompt.yaml" # 1차 프롬프트 파일
    secondary_prompt_file: str = "resources/secondary_prompt.yaml"  # 2차 프롬프트 파일
    final_prompt_file: str = "resources/final_prompt.yaml"  # 3차 프롬프트 파일
    stage1_model: str = "gpt-4o-mini"  # 1차 처리(항목 추출)
    stage2_model: str = "gpt-3.5-turbo"  # 2차 처리(장소 추출)

    @field_validator("prompt_file", "secondary_prompt_file", "final_prompt_file")
    @classmethod
    def validate_prompt_files(cls, v: str) -> str:
        return _validate_prompt_file(v)

class EvaluationRequest(BaseModel):
    # 평가를 위한 통합 요청 모델
    chatroom_name: str
    members: List[Dict[str, str]] = Field(min_length=1, max_length=50)
    messages: List[ChatMessage] = Field(min_length=1, max_length=500)
    expected_output: List[Dict[str, Any]]  # 예상 결과
    prompt_file: str = "resources/input_prompt.yaml"
    secondary_prompt_file: str = "resources/secondary_prompt.yaml"
    final_prompt_file: str = "resources/final_prompt.yaml"
    evaluation_model: str = "gpt-4o"  # 평가용 모델 (더 정확한 평가를 위해 4o 사용)
    stage1_model: str = "gpt-4o-mini"   # 1차 처리(항목 추출) 모델
    stage2_model: str = "gpt-3.5-turbo" # 2차 처리(장소 추출) 모델

    @field_validator("prompt_file", "secondary_prompt_file", "final_prompt_file")
    @classmethod
    def validate_prompt_files(cls, v: str) -> str:
        return _validate_prompt_file(v)

class ConversationResponse(BaseModel):
    # API 응답 모델 - FastAPI 엔드포인트에서 response_model=ConversationResponse로 사용됩니다.
    # 이 모델을 통해 FastAPI는 응답 데이터의 유효성을 검증하고 JSON으로 직렬화합니다.
    final_result: List[Dict[str, Any]]  # 최종 정산 결과만 반환