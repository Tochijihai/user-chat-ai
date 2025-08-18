from typing import List, Dict, Any, Optional

from app.domain.chat import Chat, Message
from app.services.gateways.chat_llm_client import ChatLLMClient
from app.spec import ChatMessageDto


class LLMChatService:
    """LLM を用いたチャット応答生成のアプリケーションサービス"""

    def __init__(self, llm_client: ChatLLMClient):
        self._llm_client = llm_client
        self._first_prompt = f"""あなたは住民から地域への要望作成を支援するアシスタントです。
- まず要望の内容を聞き、その後に場所（最低限、市区町村）を尋ねます。
- 不足があれば簡潔に一つずつ補足質問します（同時に複数質問しない）。
- 最終的に「要望」「場所」「背景・理由（任意）」「緊急度（任意）」を整形して要約し、ユーザーに確認を取ります。
- 文章はていねいで具体的、1メッセージは200字程度を目安に簡潔に。
"""

    async def invoke(
        self,
        messages: List[ChatMessageDto],
        schema: Optional[Dict[str, Any]]
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
        messages = [Message(role=d.role, content=d.content) for d in dtos]
        messages.insert(0, Message(role="user", content=self._first_prompt))
        return Chat(messages)
