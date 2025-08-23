"""API仕様とPydanticモデル定義"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str = Field(..., description="サービスの状態", example="healthy")
    version: str = Field(..., description="APIのバージョン", example="0.1.0")

class ChatMessageDto(BaseModel):
    """チャットメッセージ"""
    role: Literal["user", "assistant"] = Field(
        ...,
        description="メッセージの送信者（user: ユーザー, assistant: AI）"
    )
    content: str = Field(
        ...,
        description="メッセージの内容",
        example="日本の首都はどこですか？"
    )


class FormDto(BaseModel):
    """フォームDTO"""
    title: Optional[str] = Field(None, description="タイトル", example="家の近くに落書き")
    category: Optional[Literal["対応依頼", "質問", "賞賛"]] = Field(None, description="カテゴリ")
    description: Optional[str] = Field(None, description="詳細説明", example="家の近くにスプレーででっかい絵がたくさんあって目障り")
    place: Optional[str] = Field(None, description="場所名", example="東京都大田区")


class ChatRequest(BaseModel):
    """チャット形式の会話リクエスト"""
    mail_address: str = "test@example.com"
    messages: List[ChatMessageDto] = Field(
        ...,
        description="会話履歴のメッセージリスト",
        example=[
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "こんにちは！何かお手伝いできることはありますか？"},
            {"role": "user", "content": "東京都の中央区に住んでるんだけど、中央区の１番街のセブンイレブンの横の道路のど真ん中に大きな落書きがあって困ってるんだよねぇ"}
        ]
    )
    form: Optional[FormDto] = Field(
        None,
        description="現在のフォーム状態（部分的に埋まっている可能性あり）"
    )
    schema: Optional[dict] = Field(
        None,
        description="JSON Schema（Draft-07 サブセット）。指定すると LLM がこの構造で返す",
        example={
            "type": "object",
            "properties": {
                "answer": { "type": "string" }
            },
            "required": ["answer"]
        }
    )


class ChatResponse(BaseModel):
    """チャット会話レスポンス"""
    success: bool = Field(..., description="処理の成功/失敗")
    generated_text: Optional[str] = Field(None, description="AIの返答")
    generated_json: Optional[dict] = None
    form: Optional[FormDto] = Field(None, description="更新されたフォーム状態")
    form_complete: bool = Field(False, description="フォームが完成したかどうか")
    error: Optional[str] = Field(None, description="エラーメッセージ（失敗時のみ）")
