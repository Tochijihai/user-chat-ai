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


class ChatRequest(BaseModel):
    """チャット形式の会話リクエスト"""
    messages: List[ChatMessageDto] = Field(
        ...,
        description="会話履歴のメッセージリスト",
        example=[
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "こんにちは！何かお手伝いできることはありますか？"},
            {"role": "user", "content": "日本の首都はどこですか？"}
        ]
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
    error: Optional[str] = Field(None, description="エラーメッセージ（失敗時のみ）")

