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


class HealthData(BaseModel):
    """面談時の健康状態データ"""
    score: int = Field(..., description="健康スコア（1-5）", example=5, ge=1, le=5)
    note: str = Field(..., description="健康状態に関するメモ", example="前回よりぐっすり寝れたみたい。要経過観察")

class StartSurveyRequest(BaseModel):
    """面談開始リクエスト"""
    uid: str = Field(...,description="ユーザID",example="xxx")

class StartSurveyResponse(BaseModel):
    """面談開始レスポンス"""
    success: bool = Field(..., description="処理の成功/失敗")
    opening_message: Optional[str] = Field(None, description="AIが生成した面談開始のメッセージ")
    error: Optional[str] = Field(None, description="エラーメッセージ（失敗時のみ）")

class EvaluateRequest(BaseModel):
    """面談内容スコア化リクエスト"""
    uid:str=Field(...,description="ユーザID",example="xxx")
    messages: List[ChatMessageDto] = Field(
    ...,
    description="会話履歴のメッセージリスト",
    example=[
        {"role": "user", "content": "最近寝れてないんですよ"},
        {"role": "assistant", "content": "ゆっくり寝てください"}
    ]
    )


class EvaluateResponse(BaseModel):
    """面談内容スコア化レスポンス"""
    uid:str=Field(...,description="ユーザID")
    success: bool = Field(..., description="処理の成功/失敗")
    health: Optional[dict] = Field( 
        None,  
        description="健康スコア(0~100点)と特記事項",
        example={
            "score": 10,
            "note": "あまり寝れてないみたい"
        }
    )
    created_at:str= Field(...,description="作成日(YYYYMMDD")
    error: Optional[str] = Field(None, description="エラーメッセージ（失敗時のみ）")


class SummeryResponse(BaseModel):
    """最新要約レスポンス"""
    average_score: int = Field(...,description="今月の平均点")
    success: bool = Field(..., description="処理の成功/失敗")
    good_point: str = Field(...,description="今月のgood point")
    bad_point: str = Field(...,description="今月のbad point")
    error: Optional[str] = Field(None, description="エラーメッセージ（失敗時のみ）")
