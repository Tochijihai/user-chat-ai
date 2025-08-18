import os
from typing import List, Dict, Any, Type, Union

from langchain_aws.chat_models import ChatBedrock
from pydantic import BaseModel  # v2 に合わせて直接 import
from app.domain.chat import Message
from app.services.gateways.chat_llm_client import ChatLLMClient
from app.utils.jsonschema_to_pydantic import model_from_json_schema

class BedrockChatLLMClient(ChatLLMClient):
    def __init__(self) -> None:
        self._base_llm = ChatBedrock(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region_name=os.getenv("BEDROCK_REGION", "us-east-1"),
            model_kwargs={
                # Claude 3 系は下記キー
                "temperature": 0.7,
                "max_tokens": 1024,
                "anthropic_version": "bedrock-2023-05-31",
            },
        )

    async def chat(
        self,
        messages: List[Message],
        schema: Union[Type[BaseModel], Dict[str, Any], None] = None,
    ) -> Union[str, Dict[str, Any]]:
        # LangChain 用メッセージ形式
        langchain_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        # Pydantic モデルで構造化出力
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            res = await self._base_llm.with_structured_output(schema).ainvoke(
                langchain_messages
            )
            return res.model_dump()

        if isinstance(schema, dict):
            try:
                DynModel = model_from_json_schema("Out", schema)
            except ValueError as e:
                raise NotImplementedError(f"JSON Schema 変換失敗: {e}")

            res = await self._base_llm.with_structured_output(DynModel).ainvoke(
                langchain_messages
            )
            return res.model_dump()

        # プレーンテキスト
        res = await self._base_llm.ainvoke(langchain_messages)
        return res.content
