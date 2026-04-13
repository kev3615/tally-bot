import json

from fastapi import HTTPException, Query

from config.app_config import create_app
from handlers.process_handler import (
    CHUNKING_THRESHOLD, load_resources, process_conversation_logic,
    process_conversation_with_simplified_chain)
from models.conversation import ConversationRequest, ConversationResponse

# FastAPI 앱 생성
app = create_app()


def resolve_llm(model_name, param_name: str):
    """MODEL_REGISTRY에서 llm 인스턴스를 반환. 알 수 없는 모델명이면 400 에러."""
    if not model_name:
        return None
    from config.service_config import MODEL_REGISTRY

    llm = MODEL_REGISTRY.get(model_name)
    if llm is None:
        valid = list(MODEL_REGISTRY.keys())
        raise HTTPException(
            status_code=400,
            detail=f"알 수 없는 모델: {param_name}='{model_name}'. 사용 가능한 모델: {valid}",
        )
    return llm


def create_member_mapping(members_data):
    """멤버 데이터에서 ID-이름 매핑을 생성합니다"""
    id_to_name = {}
    name_to_id = {}

    for member_dict in members_data:
        for member_id, member_name in member_dict.items():
            id_to_name[member_id] = member_name
            name_to_id[member_name] = member_id

    return id_to_name, name_to_id


def convert_members_to_single_object(members_data):
    """
    분리된 멤버 객체들을 하나의 객체로 합칩니다
    입력: [{'8': '이다빈'}, {'9': '임재민'}, {'10': '정혜윤'}, {'11': '허원혁'}]
    출력: [{'8': '이다빈', '9': '임재민', '10': '정혜윤', '11': '허원혁'}]
    """
    if not members_data:
        return []

    # 모든 멤버 딕셔너리를 하나로 합치기
    merged_dict = {}
    for member_dict in members_data:
        merged_dict.update(member_dict)

    # 합쳐진 딕셔너리를 배열에 넣어서 반환
    return [merged_dict]


@app.get(
    "/",
    summary="서비스 상태 확인",
    description="API 서비스의 기본 상태를 확인합니다.",
    tags=["Health Check"],
)
async def root():
    return {"message": "Tally Bot AI Core Service API"}


@app.post(
    "/api/process",
    response_model=ConversationResponse,
    summary="실시간 대화 처리 (단순화된 체인)",
    description="""
          hint_phrases를 직접 파싱하는 단순화된 처리 API입니다.
          
          ### 🚀 개선사항
          - final_prompt 제거로 처리 속도 향상
          - LLM 호출 3회 → 2회로 감소
          - hint_phrases 규칙 기반 파싱으로 일관성 향상
          
          ### ⚡ 처리 과정
          1. 1차: 정산 항목 추출 (hint_phrases 포함)
          2. 2차: 장소 정보 추출
          3. 3차: hint_phrases 직접 파싱 → 정산 JSON 생성
          
          ### ✨ 특징
          - 더 빠른 처리 속도
          - 더 일관된 결과
          - 규칙 기반 안정성
          """,
    tags=["Core Processing"],
)
async def process_api(request: ConversationRequest):
    try:
        print(
            f"[process] chatroom={request.chatroom_name}, members={len(request.members)}, messages={len(request.messages)}"
        )

        # 멤버 데이터 형식 변환: 분리된 객체들 → 단일 객체
        converted_members = convert_members_to_single_object(request.members)

        # 프롬프트 로드 (final_prompt는 사용하지 않지만 호환성을 위해 로드)
        input_prompt, secondary_prompt, final_prompt, _ = await load_resources(
            request.prompt_file,
            request.secondary_prompt_file,
            request.final_prompt_file,
        )

        # 변환된 멤버 데이터로 ID-이름 매핑 생성
        id_to_name, name_to_id = create_member_mapping(converted_members)

        # sample_conversation.json 형식에서 필요한 대화 형식으로 변환
        conversation = [
            {
                "speaker": "system",
                "message_content": f"member_count: {len(id_to_name)}\nmember_mapping: {json.dumps(id_to_name, ensure_ascii=False)}",
            }
        ]

        # 실제 대화 내용 추가
        conversation.extend(
            [
                {"speaker": msg.speaker, "message_content": msg.message_content}
                for msg in request.messages
            ]
        )

        # 대화 길이 확인 및 청크 처리 옵션 설정
        use_chunking = len(request.messages) > CHUNKING_THRESHOLD

        # 모델 선택 (알 수 없는 모델명이면 400 반환)
        stage1_llm = resolve_llm(request.stage1_model, "stage1_model")
        stage2_llm = resolve_llm(request.stage2_model, "stage2_model")

        # 단순화된 체인 처리 로직 호출 (final_prompt 사용 안함)
        result = await process_conversation_with_simplified_chain(
            conversation=conversation,
            input_prompt=input_prompt,
            secondary_prompt=secondary_prompt,
            member_names=list(id_to_name.values()),
            id_to_name=id_to_name,
            name_to_id=name_to_id,
            use_chunking=use_chunking,
            stage1_llm=stage1_llm,
            stage2_llm=stage2_llm,
        )

        print("✅ 요청 처리 완료")
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 요청 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post(
    "/api/process-file",
    response_model=ConversationResponse,
    summary="파일 기반 대화 처리",
    description="""
          JSON 파일에 저장된 대화 데이터를 처리합니다.
          
          ### 📂 파일 형식
          - sample_conversation.json 형식 지원
          - 멤버 정보와 대화 내용 포함
          
          ### ⚙️ 설정 옵션
          - 프롬프트 파일 경로 설정
          - 청킹 처리 활성화/비활성화
          """,
    tags=["File Processing"],
)
async def process_conversation_from_file(
    conversation_file: str = "resources/sample_conversation.json",  # 대화 JSON 파일
    prompt_file: str = "resources/input_prompt.yaml",  # 1차 프롬프트 파일
    secondary_prompt_file: str = "resources/secondary_prompt.yaml",  # 2차 프롬프트 파일
    final_prompt_file: str = "resources/final_prompt.yaml",  # 3차 프롬프트 파일
    use_chunking: bool = True,  # 청크 처리 사용 여부
    stage1_model: str = Query("gpt-4o-mini", description="1차 처리 모델"),
    stage2_model: str = Query("gpt-3.5-turbo", description="2차 처리 모델"),
):
    try:
        # 프롬프트와 대화 로드
        input_prompt, secondary_prompt, final_prompt, conversation = (
            await load_resources(
                prompt_file, secondary_prompt_file, final_prompt_file, conversation_file
            )
        )

        # member 정보 추출 및 매핑 생성
        members_text = conversation[0]["message_content"]

        # ID-이름 매핑이 이미 있는지 확인
        if "member_mapping:" in members_text:
            # 기존 매핑 정보 사용
            mapping_line = [
                line
                for line in members_text.split("\n")
                if line.startswith("member_mapping:")
            ][0]
            id_to_name = json.loads(mapping_line.replace("member_mapping:", "").strip())
            name_to_id = {name: id for id, name in id_to_name.items()}
            member_names = list(id_to_name.values())
        else:
            # members 정보에서 매핑 생성
            members_line = [
                line for line in members_text.split("\n") if line.startswith("members:")
            ][0]
            members_str = members_line.replace("members:", "").strip()
            member_names = json.loads(members_str)

            # 딕셔너리 형태로 변환 (고정 형식 유지)
            members = [dict(zip(map(str, range(len(member_names))), member_names))]

            # ID-이름 매핑 생성
            id_to_name, name_to_id = create_member_mapping(members)

            # member_mapping 정보 추가 및 members 정보 대체
            for i, msg in enumerate(conversation):
                if msg["speaker"] == "system" and i == 0:
                    content = msg["message_content"]
                    lines = content.split("\n")

                    # members: 라인 삭제
                    lines = [line for line in lines if not line.startswith("members:")]

                    # member_mapping 및 count 추가
                    lines.append(f"member_count: {len(id_to_name)}")
                    lines.append(
                        f"member_mapping: {json.dumps(id_to_name, ensure_ascii=False)}"
                    )

                    # 다시 조합
                    msg["message_content"] = "\n".join(lines)
                    break

        # 공통 대화 처리 로직 호출
        stage1_llm = resolve_llm(stage1_model, "stage1_model")
        stage2_llm = resolve_llm(stage2_model, "stage2_model")
        return await process_conversation_logic(
            conversation=conversation,
            input_prompt=input_prompt,
            secondary_prompt=secondary_prompt,
            final_prompt=final_prompt,
            member_names=member_names,
            id_to_name=id_to_name,
            name_to_id=name_to_id,
            use_chunking=use_chunking,
            stage1_llm=stage1_llm,
            stage2_llm=stage2_llm,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# FastAPI가 uvicorn을 통해 실행될 때 사용
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
