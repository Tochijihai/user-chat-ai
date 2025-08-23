import re
import json
import uuid

from typing import List, Dict, Any, Optional, Tuple

from geopy.geocoders import Nominatim

from app.infrastructure.opinions_table import OpinionsTable
from app.domain.chat import Chat, Message, Form
from app.services.gateways.chat_llm_client import ChatLLMClient
from app.spec import ChatMessageDto, FormDto


class LLMChatService:
    """LLM を用いたチャット応答生成のアプリケーションサービス"""

    def __init__(self, llm_client: ChatLLMClient):
        self._llm_client = llm_client
        self._opinions_table = OpinionsTable()
        self._first_prompt = f"""あなたは住民から地域への要望作成を支援するアシスタントです。以下の手順でユーザーから必要な情報を聞き出してください。

必要な情報：
- title: 要望のタイトル
- category: "対応依頼"、"質問"、"賞賛"、 "雑談(それ以外)"のいずれか
- description: 要望の詳細説明
- place: 場所（都道府県・市区町村レベルで十分。詳細な住所は不要）

重要な指示：
1. ユーザーの発言から既に情報を抽出できる場合は、追加質問せずにフォームを更新してください
2. place は「東京都中央区」「大阪府大阪市」レベルで十分です。具体的な住所や番地は求めないでください
3. 未入力の項目のみ簡潔に質問してください（同時に複数質問しない）
4. 全ての情報が揃ったら、確認のため内容をまとめて提示してください
5. ユーザーが確認したら「ありがとうございます。要望を送信しました。」と返答してください

会話を通じて、フォームの各項目を段階的に埋めていってください。
"""

    async def invoke(
        self,
        mail_address: str,
        messages: List[ChatMessageDto],
        form_dto: Optional[FormDto] = None,
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """ユーザー入力を受け取り、LLM から応答を生成して返す"""
        if not messages:
            return {"success": False, "error": "メッセージが空です"}

        try:
            # ドメインオブジェクトに変換
            chat = self._create_chat(messages, form_dto)
            
            # フォーム機能用のstructured outputスキーマを作成
            form_schema = self._create_form_schema()
            
            # AIチャット（常にフォーム機能用のschemaを使用）
            generated = await self._llm_client.chat(chat.messages, schema=form_schema)

            if isinstance(generated, dict):
                # フォーム情報を更新
                updated_form = self._update_form_from_response(chat.form, generated)
                form_complete = updated_form.is_complete()
                
                # フォーム完成時の処理
                if form_complete:
                    await self._handle_completed_form(mail_address, updated_form)
                
                return {
                    "success": True,
                    "generated_json": generated,
                    "form": self._form_to_dto(updated_form),
                    "form_complete": form_complete
                }
            else:
                # 文字列が返された場合（structured outputが失敗した場合）
                # 現在のフォーム状態をそのまま返す
                return {
                    "success": True,
                    "generated_text": generated,
                    "form": self._form_to_dto(chat.form),
                    "form_complete": chat.form.is_complete()
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_chat(self, dtos: List[ChatMessageDto], form_dto: Optional[FormDto] = None) -> Chat:
        """メッセージリストから Chat ドメインオブジェクトを作成"""
        messages = [Message(role=d.role, content=d.content) for d in dtos]
        
        # フォーム状態をプロンプトに含める
        form_prompt = self._create_form_prompt(form_dto)
        messages.insert(0, Message(role="user", content=self._first_prompt + form_prompt))
        
        # フォームオブジェクトを作成
        form = self._dto_to_form(form_dto) if form_dto else Form()
        
        return Chat(messages=messages, form=form)
    
    def _create_form_prompt(self, form_dto: Optional[FormDto]) -> str:
        """現在のフォーム状態をプロンプトに追加"""
        if not form_dto:
            return "\n\n現在のフォーム状態: 空（全て未入力）"
        
        form_status = "\n\n現在のフォーム状態:"
        form_status += f"\n- title: {form_dto.title or '未入力'}"
        form_status += f"\n- category: {form_dto.category or '未入力'}"
        form_status += f"\n- description: {form_dto.description or '未入力'}"
        form_status += f"\n- place: {form_dto.place or '未入力'}"
        
        return form_status
    
    def _create_form_schema(self) -> Dict[str, Any]:
        """フォーム機能用のstructured outputスキーマを作成"""
        return {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "AIの会話応答（追加質問など）"
                },
                "form": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": ["string", "null"],
                            "description": "タイトル（未入力の場合はnull）"
                        },
                        "category": {
                            "type": ["string", "null"],
                            "enum": ["対応依頼", "質問", "賞賛", None],
                            "description": "カテゴリ（未入力の場合はnull）"
                        },
                        "description": {
                            "type": ["string", "null"],
                            "description": "詳細説明（未入力の場合はnull）"
                        },
                        "place": {
                            "type": ["string", "null"],
                            "description": "場所（都道府県レベル、未入力の場合はnull）"
                        }
                    },
                    "required": ["title", "category", "description", "place"],
                    "additionalProperties": False,
                    "description": "現在の会話から抽出・更新されたフォーム情報。必ずオブジェクト形式で返すこと。"
                },
                "form_complete": {
                    "type": "boolean",
                    "description": "フォームが完成したかどうか"
                }
            },
            "required": ["answer", "form", "form_complete"],
            "additionalProperties": False
        }
    
    def _dto_to_form(self, form_dto: FormDto) -> Form:
        """FormDtoをFormドメインオブジェクトに変換"""
        return Form(
            title=form_dto.title,
            category=form_dto.category,
            description=form_dto.description,
            place=form_dto.place
        )
    
    def _form_to_dto(self, form: Form) -> FormDto:
        """FormドメインオブジェクトをFormDtoに変換"""
        return FormDto(
            title=form.title,
            category=form.category,
            description=form.description,
            place=form.place
        )
    
    def _update_form_from_response(self, current_form: Form, response: Dict[str, Any]) -> Form:
        """LLMの応答からフォームを更新"""
        if not isinstance(response, dict):
            return current_form
            
        form_data = response.get("form", {})
        
        # 文字列の場合はJSONパースを試行
        if isinstance(form_data, str):
            try:
                form_data = json.loads(form_data)
                print('JSON文字列をパースしました')
            except json.JSONDecodeError:
                print('JSON文字列のパースに失敗')
                return current_form
        
        if not isinstance(form_data, dict):
            print('formが辞書でも文字列でもない')
            return current_form
        
        return Form(
            title=form_data.get("title") or current_form.title,
            category=form_data.get("category") or current_form.category,
            description=form_data.get("description") or current_form.description,
            place=form_data.get("place") or current_form.place
        )
    
    async def _handle_completed_form(self, mail_address: str, form: Form) -> None:
        """完成したフォームの処理"""
        if form.place:
            try:
                id = str(uuid.uuid4())
                latitude, longitude = self._get_location(form.place)
                self._opinions_table.put_opinion(id, mail_address, form.description or "", latitude, longitude)
            except Exception as e:
                # ログ出力など
                pass
    
    def _get_location(self, place: str) -> Tuple[float, float]:
        """場所から緯度経度を取得"""
        geolocator = Nominatim(user_agent="geopy")
        location = geolocator.geocode(place)
        return location.latitude, location.longitude
