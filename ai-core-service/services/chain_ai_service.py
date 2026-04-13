"""1차 → 2차 → (선택) 3차 LLM 체인을 객체로 묶은 서비스."""

import json
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException

from services.ai_service import (process_conversation, process_final,
                                 process_summary)
from services.result_processor import (
    extract_complex_items, extract_items_only, map_place_to_complex_items,
    preprocess_conversation_results, process_all_results,
    process_all_results_without_final_prompt, process_complex_results)
from utils.logging_utils import log_processing_stage

Conversation = Union[Dict[str, Any], List[Dict[str, str]]]
Prompt = Dict[str, Any]


class ChainAIService:
    async def process_with_simplified_chain(
        self,
        conversation: Conversation,
        input_prompt: Prompt,
        secondary_prompt: Prompt,
        member_names: List[str],
        id_to_name: Dict[str, str],
        name_to_id: Dict[str, str],
        stage1_llm=None,
        stage2_llm=None,
    ) -> Dict[str, Any]:
        """final_prompt 없이 hint_phrases 규칙으로 최종 조합 (단일 패스)."""
        members = (
            conversation.get("members", []) if isinstance(conversation, dict) else []
        )
        result = await process_conversation(
            conversation, input_prompt, callback=None, members=members, llm=stage1_llm
        )
        if not result:
            raise HTTPException(status_code=500, detail="처리 결과가 없습니다.")

        converted = await preprocess_conversation_results(result)
        log_processing_stage("통화 변환 후 결과", converted)

        secondary_conversation = [
            {"speaker": "system", "message_content": "다음은 분석할 항목 목록입니다."},
            {
                "speaker": "user",
                "message_content": json.dumps(
                    extract_items_only(converted), ensure_ascii=False
                ),
            },
        ]
        secondary_result = await process_summary(
            secondary_conversation, secondary_prompt, callback=None, llm=stage2_llm
        )
        if not secondary_result:
            raise HTTPException(status_code=500, detail="2차 처리 결과가 없습니다.")

        log_processing_stage("2차 처리 결과", secondary_result)

        final_result = process_all_results_without_final_prompt(
            converted, secondary_result, member_names, id_to_name, name_to_id
        )
        if not final_result:
            raise HTTPException(status_code=500, detail="최종 처리 결과가 없습니다.")

        log_processing_stage("최종 처리 결과", final_result)
        return {"final_result": final_result}

    async def process_with_sequential_chain(
        self,
        conversation: Conversation,
        input_prompt: Prompt,
        secondary_prompt: Prompt,
        final_prompt: Prompt,
        member_names: List[str],
        id_to_name: Dict[str, str],
        name_to_id: Dict[str, str],
        stage1_llm=None,
        stage2_llm=None,
    ) -> Dict[str, Any]:
        """복잡 정산은 3차 LLM(process_final), 나머지는 균등 분배 로직."""
        members = (
            conversation.get("members", []) if isinstance(conversation, dict) else []
        )
        result = await process_conversation(
            conversation,
            input_prompt,
            callback=None,
            members=members,
            llm=stage1_llm,
        )
        if not result:
            raise HTTPException(status_code=500, detail="처리 결과가 없습니다.")

        converted = await preprocess_conversation_results(result)
        log_processing_stage("통화 변환 후 결과", converted)

        secondary_conversation = [
            {"speaker": "system", "message_content": "다음은 분석할 항목 목록입니다."},
            {
                "speaker": "user",
                "message_content": json.dumps(
                    extract_items_only(converted), ensure_ascii=False
                ),
            },
        ]
        secondary_result = await process_summary(
            secondary_conversation,
            secondary_prompt,
            callback=None,
            llm=stage2_llm,
        )
        if not secondary_result:
            raise HTTPException(status_code=500, detail="2차 처리 결과가 없습니다.")

        log_processing_stage("2차 처리 결과", secondary_result)

        complex_items = extract_complex_items(converted)
        if not complex_items:
            final_result = process_all_results_without_final_prompt(
                converted, secondary_result, member_names, id_to_name, name_to_id
            )
        else:
            mapped = map_place_to_complex_items(
                complex_items, secondary_result, converted
            )
            final_conversation = [
                {
                    "speaker": "system",
                    "message_content": "다음은 복잡한 정산 항목 목록입니다.",
                },
                {
                    "speaker": "user",
                    "message_content": json.dumps(mapped, ensure_ascii=False),
                },
            ]
            complex_raw = await process_final(
                final_conversation, final_prompt, callback=None
            )
            if not complex_raw:
                raise HTTPException(
                    status_code=500, detail="3차(복잡 항목) 처리 결과가 없습니다."
                )
            log_processing_stage("3차 처리 결과", complex_raw)
            complex_processed = process_complex_results(complex_raw, mapped, name_to_id)
            final_result = process_all_results(
                converted,
                secondary_result,
                complex_processed,
                member_names,
                id_to_name,
                name_to_id,
            )

        if not final_result:
            raise HTTPException(status_code=500, detail="최종 처리 결과가 없습니다.")

        log_processing_stage("최종 처리 결과", final_result)
        return {"final_result": final_result}

    async def process_chunked_with_sequential_chain(
        self,
        conversation: Conversation,
        input_prompt: Prompt,
        secondary_prompt: Prompt,
        final_prompt: Optional[Prompt],
        member_names: List[str],
        id_to_name: Dict[str, str],
        name_to_id: Dict[str, str],
        stage1_llm=None,
        stage2_llm=None,
    ) -> Dict[str, Any]:
        """긴 대화는 기존 청크 파이프라인과 동일하게 처리 (순환 import 방지를 위해 지연 import)."""
        from handlers.process_handler import split_and_process_conversation

        return await split_and_process_conversation(
            conversation=conversation,
            input_prompt=input_prompt,
            secondary_prompt=secondary_prompt,
            final_prompt=final_prompt,
            member_names=member_names,
            id_to_name=id_to_name,
            name_to_id=name_to_id,
            stage1_llm=stage1_llm,
            stage2_llm=stage2_llm,
        )
