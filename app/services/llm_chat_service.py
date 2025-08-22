import re
import json
import uuid

from typing import List, Dict, Any, Optional, Tuple

from geopy.geocoders import Nominatim

from app.infrastructure.opinions_table import OpinionsTable
from app.domain.chat import Chat, Message
from app.services.gateways.chat_llm_client import ChatLLMClient
from app.spec import ChatMessageDto


class LLMChatService:
    """LLM を用いたチャット応答生成のアプリケーションサービス"""

    def __init__(self, llm_client: ChatLLMClient):
        self._llm_client = llm_client
        self._opinions_table = OpinionsTable()
        self._first_prompt = f"""あなたは住民から地域への要望作成を支援するアシスタントです。以下の手順でユーザーの「要望」と要望のある「場所」を聞き出してください。
1. ユーザー要望の内容を聞き、要望のある場所が不明である場合、場所（最低限、市区町村）を尋ねます。
2. 不足があれば簡潔に一つずつ補足質問します（同時に複数質問しない）。
3. 「要望」「場所」が明確になったら、以下のように質問します。
  - "ありがとうございます。ご要望は以下の通りでよろしいでしょうか？\n要望：<ユーザーの要望>\n場所：<ユーザーの指定した場所>"
4. ユーザーが間違いない、と回答したら以下の通りに返答してください
  - "ありがとうございます。要望を送信しました。"
  - JSON形式の文字列を付け加えてください。
    - {{"opinion": "XXXXXXX", "place": "YYYYYY"}}
    - ただし、place は Python の geopy の Nominatim で使用します。
"""

    async def invoke(
        self,
        mail_address: str,
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
                json_pattern = r"\{\"opinion\": \".*\", \"place\": \".*\"\}"
                json_string = re.search(json_pattern, generated["answer"])

                # 「場所」と「要望」のJSONが取得できた場合、opinions テーブルに追加
                if json_string:
                    json_data = json.loads(json_string.group(0))
                    id = str(uuid.uuid4())
                    opinion = json_data["opinion"]
                    latitude, longitude = self._get_location(json_data["place"])
                    self._opinions_table.put_opinion(id, mail_address, opinion, latitude, longitude)

                    # JSON部分は削除
                    generated["answer"] = re.sub(json_pattern, "", generated["answer"])

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
    
    def _get_location(self, place: str) -> Tuple[float, float]:
        """場所から緯度経度を取得"""
        geolocator = Nominatim(user_agent="geopy")
        location = geolocator.geocode(place)
        return location.latitude, location.longitude
