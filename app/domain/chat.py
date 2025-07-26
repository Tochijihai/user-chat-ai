"""チャットドメインモデル"""

from typing import List, Literal
from dataclasses import dataclass


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
class Chat:
    """チャットドメインモデル"""
    messages: List[Message]
    
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
