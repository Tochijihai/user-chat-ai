"""チャットドメインモデル"""

from typing import List, Literal, Optional
from dataclasses import dataclass, field


@dataclass
class Message:
    """メッセージドメインモデル"""
    role: Literal["user", "assistant"]
    content: str
    
    def is_user_message(self) -> bool:
        """ユーザーメッセージかどうか"""
        return self.role == "user"
    
    def is_assistant_message(self) -> bool:
        """アシスタントメッセージかどうか"""
        return self.role == "assistant"


@dataclass
class Form:
    """問い合わせフォーム"""
    title: Optional[str] = None  # 例: "家の近くに落書き"
    category: Optional[Literal["対応依頼", "質問", "賞賛"]] = None
    description: Optional[str] = None  # 詳細説明
    place: Optional[str] = None  # 場所名（例: "大田区大森町"）
    
    def is_complete(self) -> bool:
        """フォームが完成しているかどうか"""
        return (
            self.title is not None and
            self.category is not None and
            self.description is not None and
            self.place is not None
        )
    
    def get_missing_fields(self) -> List[str]:
        """未入力のフィールドリストを取得"""
        missing = []
        if not self.title:
            missing.append("title")
        if not self.category:
            missing.append("category")
        if not self.description:
            missing.append("description")
        if not self.place:
            missing.append("place")
        return missing


@dataclass
class Chat:
    """チャットドメインモデル"""
    messages: List[Message]
    form: Form = field(default_factory=Form)
    
    def add_message(self, message: Message) -> None:
        """メッセージを追加"""
        self.messages.append(message)
    
    def get_conversation_context(self) -> str:
        """会話コンテキストを文字列として取得"""
        context = ""
        for message in self.messages:
            if message.is_user_message():
                context += f"ユーザー: {message.content}\n"
            elif message.is_assistant_message():
                context += f"アシスタント: {message.content}\n"
        return context.strip()
    
    def get_last_user_message(self) -> Message | None:
        """最後のユーザーメッセージを取得"""
        for message in reversed(self.messages):
            if message.is_user_message():
                return message
        return None
    
    def is_empty(self) -> bool:
        """空のチャットかどうか"""
        return len(self.messages) == 0
