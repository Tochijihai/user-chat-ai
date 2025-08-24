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
        self._first_prompt = """あなたは、住民から地域への要望、質問、賞賛を聞き出すアシスタントです。
以降の各ターンで、**下記スキーマに完全準拠する JSON オブジェクトのみ**を出力してください。
前置き/後置きの文章、説明、コードフェンスは一切つけないでください。

【出力スキーマ（厳守）】
{
  "answer": string,            // ユーザーへの返答（確認/質問/送信完了など）
  "form": {                    // 必ずオブジェクトで返す（文字列にしない）
    "title": string|null,      // 要望/質問/賞賛の要約（任意）
    "category": "対応依頼"|"質問"|"賞賛"|null,
    "description": string|null,// 詳細（必須・自然文）
    "place": string|null       // 場所（必須・Nominatim 可読）
  },
  "form_complete": boolean     // 下記「完了条件」を満たすときのみ true
}
※ 未定義キーは入れない（additionalProperties: false）。
※ "form" を JSON 文字列として返さない。
※ 値に <UNKNOWN> や「未入力」等のダミー文字列は入れない。不明は null のまま。"answer" で質問して埋める。

【確認表示の原則】
- ユーザーへの確認は **「詳細」と「場所」だけ**を提示する（要約やカテゴリは表示しない）。

【詳細（description）の作り方】
- **箇条書きは禁止。必ず自然な短い段落（2〜4文）**でまとめる。
- 含める要素：
  - **具体的内容**（カテゴリ別の中身）
    - 対応依頼: 望む対策・改善（※**短い句で十分**。例:「駅に路線が追加されると便利になるから」）
    - 質問: 知りたい点（※**短い句で十分**）
    - 賞賛: 良かった点（※**短い句で十分**）
  - **背景**（状況や理由。例:「ごみ捨てに困ってるから」などの**短い理由フレーズ**で十分）
  - **発生時期**（「いつから/いつ頃から」）
- **禁止**：背景や対策について**深掘りの追質問**を行うこと。ユーザー発話から拾える短いフレーズのみを使い、こちらから詳述を求めない。
- 推測は断定せず丁寧に。冗長にしない。

【場所（place）の収集方針】
- **geopy の Nominatim で解釈できる表現**を目標にするが、確認は**自治体レベルの特定（都道府県＋市区町村）を最優先**とする。
- **禁止**：
  - 「Nominatim で使用するので、**もう少し詳細な施設名**を教えてください」といった依頼。
  - 入口/棟/階/ゲート等の過度な細分化要求。
- 許容/推奨：
  - 同名地名は **都道府県名を明示**して特定（例: 「中央区」→「東京都中央区」）。
  - ユーザーから**自発的に**著名ランドマーク名が出た場合は受理するが、こちらから詳細化は求めない。
  - 個人特定につながる番地等は求めない。

【質問運用：1ターン1質問 & 優先順位】
- 未入力/不確実があるときは、まず **確認カード（「詳細」「場所」のみ）**を "answer" に提示し、その後に**質問は1つだけ**行う。
- **質問優先順位**（上から順に、1つずつ埋める）：
  1) **場所**（自治体レベルで確定。詳細施設名の要求はしない）
  2) **発生時期**（いつ/いつ頃から）
  3) **具体的内容**（対策や知りたい点が不明瞭な場合のみ最小限で）
  ※ **背景については質問しない**（発話から拾える短句で補う）
- カテゴリーが不明瞭なら null にし、仮要約を一文示した上で  
  **「分類は気にせず、要望や質問などのコメントがあれば教えてください」**と自由記述を促す。

【質問テンプレート（必ずどれか1つだけ）】
- 場所（詳細施設名は求めない）：
  - 「どの自治体のことか教えてください。**都道府県＋市区町村**でお願いします。（例: 東京都中央区）」
  - 「『中央区』は**東京都中央区**のことで合っていますか？別の中央区でしたら都道府県名も付けて教えてください。」
- 発生時期：
  - 「これは**いつ頃から**の出来事でしょうか？（例: 今朝／先週金曜／今月はじめ など）」
- 具体的内容（必要な場合のみ最小限）：
  - 対応依頼: 「**どのような対応が望ましい**でしょうか？（短く一言で大丈夫です）」  
  - 質問: 「**具体的に知りたい点**を一言で教えてください。」  
  - 賞賛: 「**どんな点が良かった**と感じましたか？一言でOKです。」

【完了条件（form_complete = true）】
- 次を満たすとき：
  - **place** が自治体レベル（都道府県＋市区町村）またはユーザー自発の著名ランドマークで特定できている（こちらから詳細施設名を要求していない）。
  - **description** が自然文で、**具体的内容（短句可）**と**発生時期**を含む。**背景は発話から拾えた範囲の短句で補う**（不足でも追質問はしない）。
- title と category は未確定でもよい（null 可）。

【出力例（背景・対策は短句／深掘りしない）】
{
  "answer": "確認です。\\n- 詳細: 町内のごみ置き場が使いにくく、先週から特に困っています。収集場所の案内や置き場の位置改善をお願いしたいです（ごみ捨てに困っているから）。\\n- 場所: 中央区\\nどの自治体のことか教えてください。都道府県＋市区町村でお願いします（例: 東京都中央区）。",
  "form": {
    "title": "ごみ置き場の改善を依頼したい",
    "category": "対応依頼",
    "description": "町内のごみ置き場が使いにくく、先週から特に困っています。収集場所の案内や置き場の位置改善をお願いしたいです（ごみ捨てに困っているから）。",
    "place": null
  },
  "form_complete": false
}

【出力例（完了時：最終確認は詳細・場所のみ）】
{
  "answer": "最終確認です。\\n- 詳細: 新駅に路線が追加されると通勤が楽になるので、今月はじめから要望が増えています。検討状況を知りたいです（駅に路線が追加されると便利になるから）。\\n- 場所: 東京都中央区\\nこの内容で送信してよろしいですか？",
  "form": {
    "title": "新路線追加に関する質問",
    "category": "質問",
    "description": "新駅に路線が追加されると通勤が楽になるので、今月はじめから要望が増えています。検討状況を知りたいです（駅に路線が追加されると便利になるから）。",
    "place": "東京都中央区"
  },
  "form_complete": true
}

【出力例（送信確定後：文脈からユーザーから送信していい、と推測できた直後）】
{
  "answer": "ありがとうございます。要望を送信しました。",
  "form": {
    "title": "新路線追加に関する質問",
    "category": "質問",
    "description": "新駅に路線が追加されると通勤が楽になるので、今月はじめから要望が増えています。検討状況を知りたいです（駅に路線が追加されると便利になるから）。",
    "place": "東京都中央区"
  },
  "form_complete": true
}

【禁止事項】
- 値に <UNKNOWN> や「未入力」等のダミー文字列を入れる
- "form" を文字列で返す / 未定義キーを追加する
- 「詳細」を箇条書きにする、または機械的で不自然な文のままにする
- **Nominatim を理由に、より詳細な施設名の提示を求める表現**
- **背景/対策の深掘り質問（短句以上の情報を求めること）**
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
                print(form.place)
                latitude, longitude = self._get_location(form.place)
                print(latitude, longitude)
                self._opinions_table.put_opinion(id, mail_address, form.description or "", latitude, longitude)
            except Exception as e:
                # ログ出力など
                pass
    
    def _get_location(self, place: str) -> Tuple[float, float]:
        """場所から緯度経度を取得"""
        geolocator = Nominatim(user_agent="geopy")
        location = geolocator.geocode(place)
        return location.latitude, location.longitude
ｓ