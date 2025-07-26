from typing import List, Dict, Any, Optional

from app.domain.chat import Chat, Message
from app.services.gateways.chat_llm_client import ChatLLMClient
from app.spec import ChatMessageDto


class LLMChatService:
    """LLM を用いたチャット応答生成のアプリケーションサービス"""

    def __init__(self, llm_client: ChatLLMClient):
        self._llm_client = llm_client

    async def invoke(
        self,
        messages: List[ChatMessageDto],
        schema: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """ユーザー入力を受け取り、LLM から応答を生成して返す"""
        if not messages:
            return {"success": False, "error": "メッセージが空です"}

        try:
            # ドメインオブジェクトに変換
            chat = self._create_chat(messages)
            # AIチャット
            generated = await self._llm_client.chat(chat.messages, schema=schema)

            if isinstance(generated, dict):
                return {"success": True, "generated_json": generated}
            else:
                return {"success": True, "generated_text": generated}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_chat(self, dtos: List[ChatMessageDto]) -> Chat:
        """メッセージリストから Chat ドメインオブジェクトを作成"""
        return Chat([Message(role=d.role, content=d.content) for d in dtos])
