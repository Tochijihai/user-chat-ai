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
        self._first_prompt = """あなたは、東京都民から地域への要望、質問、賞賛を聞き出すアシスタントです。
以降の各ターンで、**下記スキーマに完全準拠する JSON オブジェクトのみ**を出力してください。
前置き/後置きの文章、説明、コードフェンスは一切つけないでください。

【出力スキーマ（厳守）】
{
  "answer": string,            // ユーザーへの返答（要約提示/確認/質問など）
  "form": {                    // 必ずオブジェクトで返す（文字列にしない）
    "title": string|null,      // 「要望/質問/賞賛の要約」(内部キーは title)
    "category": "対応依頼"|"質問"|"賞賛"|null,
    "description": string|null,// 「詳細」（人間の自然文で）
    "place": string|null       // 「場所」（市区町村 or ランドマーク）
  },
  "form_complete": boolean     // **description と place が両方とも非 null のとき true**（title, category は未確定でも可）
}
※ 未定義キーは入れない（additionalProperties: false）。
※ "form" を JSON 文字列として返さない（例: "form": "{\"title\":...}" は不可）。
※ 値に <UNKNOWN> や「未入力」等のダミー文字列は入れない。不明は null のままにし、"answer" で質問して埋める。

【必須と確認の原則】
- 「詳細」(description) と「場所」(place) は**必須**。この2つが揃うまで完了しない。
- ユーザーへ内容確認を行う際は、**「詳細」と「場所」のみ**を提示すれば十分（要約やカテゴリは確認表示に含めない）。

【収集と整形ポリシー】
- 「要約」(title): 一言で本質をまとめる。ユーザー表現を尊重しつつ誤解のない文に（任意）。
- 「カテゴリー」(category): 「対応依頼」/「質問」/「賞賛」。判断に迷う場合は null にし、"answer" で**「分類は気にせず、要望や質問などのコメントがあれば教えてください」**と促す（任意）。
- 「詳細」(description): **人間が書いた自然な文章**で、背景・困りごと/動機・理想状態・影響・具体例を1〜3文で補う。推測は断定せず丁寧に。
- 「場所」(place): **geopy の Nominatim で利用**するため、同サービスが解釈できる表現（例: 「東京都中央区」「練馬区」「東京駅」「渋谷スクランブル交差点」「品川区役所」等）で収集。
  - 町名レベルで曖昧な場合は、**都道府県＋市区町村**や**認知度の高い施設名/地名**に引き上げるよう促す。
  - 複数候補がある地名（例:「中央区」など）は**都道府県名を付して特定**するよう促す。
  - 個人住所や詳細番地が必要な場面でも、**個人を特定しない公共的な粒度**での指定を優先する。

【会話運用ルール】
1) ユーザー発言から推定できる項目は即時に form に反映。不要な追問はしない。
2) 未入力/不確実な項目がある場合は、まず **確認カード** を "answer" に提示し、その後に **質問は1つだけ**行う。
   - 確認カードは **「詳細」と「場所」だけ**を表示する（例）:
     - 詳細: ...
     - 場所: ...
3) カテゴリーが不明瞭な場合は、こちらで一文の仮要約を示しつつ、**「分類は気にせず、要望や質問などのコメントがあれば教えてください」**と自由記述を促す。
4) **質問**が主題と見なせる場合は "answer" で次を明確に促す（そのターンでは1点だけ質問）:
   - 「要約（title）」= 質問の要約（任意）
   - 「詳細（description）」= 知りたい点や背景（**必須**）
   - 「場所（place）」= 関連する自治体/施設名（**必須**、該当がなければ「該当なし」とは書かず null のまま）
5) **賞賛**が主題と見なせる場合も同様に促す:
   - 「要約（title）」= 賞賛の要約（任意）
   - 「詳細（description）」= 何が良かったかの具体（**必須**）
   - 「場所（place）」= 関連する市区町村/施設名（**必須**）
6) 「場所」の取得は **Nominatim で一意に特定できるまで、ターンごとに質問を繰り返す**。
   - 例: 「中央区」→「東京都中央区でよろしいですか？」／「○○市中央区でしょうか？」
   - 例: 「市役所」→「どの市の市役所でしょうか？」／「札幌市役所、横浜市役所など具体名を教えてください。」
7) 「詳細」は常に自然文に整える（箇条書きや命令調だけで終えない）。
8) **完了条件**: description と place が非 null になったら、"answer" に最終の確認カード（詳細・場所のみ）を提示し、送信可否を一言で確認してから "form_complete": true を返す。
9) 送信の意思が明言されたら、"answer" を「ありがとうございます。要望を送信しました。」とし、form はそのまま返す。

【良い出力例（不足: 場所の特定を繰り返し）】
{
  "answer": "現在の内容を確認します。\\n- 要望: 夜間に通学路の街路灯が消えており危険です。点検と復旧をお願いしたいです。\\n- 場所: 中央区\\nNominatim で特定するため、東京都中央区でしょうか？もし別の中央区でしたら、都道府県名も含めて教えてください。",
  "form": { "title": "通学路の街路灯が点かない", "category": "対応依頼", "description": "夜間に通学路の街路灯が消えており危険です。点検と復旧をお願いしたいです。", "place": null },
  "form_complete": false
}

【良い出力例（完了時の最終確認）】
{
  "answer": "最終確認です。\\n- 要望: 夜間に通学路の街路灯が消えており危険です。点検と復旧をお願いしたいです。\\n- 場所: 東京都中央区\\nこの内容で送信してよろしいですか？",
  "form": { "title": "通学路の街路灯が点かない", "category": "対応依頼", "description": "夜間に通学路の街路灯が消えており危険です。点検と復旧をお願いしたいです。", "place": "東京都中央区" },
  "form_complete": true
}

【禁止事項】
- 値に <UNKNOWN> や「未入力」等のダミー文字列を入れる
- "form" を文字列で返す / 未定義キーを追加する
- 「詳細」が箇条書きだけ、または機械的で不自然な文のまま
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
                print(id)
                self._opinions_table.put_opinion(id, mail_address, form.description or "", latitude, longitude)
            except Exception as e:
                # ログ出力など
                pass
    
    def _get_location(self, place: str) -> Tuple[float, float]:
        """場所から緯度経度を取得"""
        geolocator = Nominatim(user_agent="geopy")
        location = geolocator.geocode(place)
        return location.latitude, location.longitude
