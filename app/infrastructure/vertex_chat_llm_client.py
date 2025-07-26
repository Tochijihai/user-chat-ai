import json
import os
from typing import Type, Union, Dict, Any

from langchain_google_vertexai import ChatVertexAI
from langchain_core.pydantic_v1 import BaseModel

from app.domain.chat import Message
from app.services.gateways.chat_llm_client import ChatLLMClient
from app.infrastructure.config import vertex_config


class VertexChatLLMClient(ChatLLMClient):
    """VertexAI クライアントクラス"""
    
    def __init__(self):
         # LangChain の ChatVertexAI は初期化時に ADC を自動取得
        self._base_llm = ChatVertexAI(
            project=vertex_config.project_id,
            location=vertex_config.location,
            model=vertex_config.model_name,
            temperature=float(os.getenv("TEMPERATURE", 0.7)),
            max_output_tokens=int(os.getenv("MAX_TOKENS", 1024)),
        )

    async def chat(
        self,
        messages: list[Message],
        schema: Union[Type[BaseModel], Dict[str, Any], None] = None,
    ) -> Union[str, Dict[str, Any]]:
        """
        - `schema` に Pydantic モデル or JSON Schema(dict) を渡すと JSON 構造で返す
        - 渡さない場合は通常のテキストを返す
        """
        langchain_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        # ① Pydantic モデル指定
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            llm = self._base_llm.with_structured_output(schema)
            res = await llm.ainvoke(langchain_messages)
            return res.model_dump()

        # ② dict(JSON Schema) 指定
        if isinstance(schema, dict):
            llm = self._base_llm.bind(
                response_schema=schema,
                response_mime_type="application/json",
            )
            res = await llm.ainvoke(langchain_messages)
            return json.loads(res.content)

        # ③ スキーマ無し（テキスト）
        res = await self._base_llm.ainvoke(langchain_messages)
        return res.content
