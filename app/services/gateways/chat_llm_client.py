from typing import Protocol, List, Dict, Any, Union, Type
from app.domain.chat import Message
from langchain_core.pydantic_v1 import BaseModel


class ChatLLMClient(Protocol):
    async def chat(
        self,
        messages: List[Message],
        schema: Union[Type[BaseModel], Dict[str, Any], None] = None,
    ) -> Union[str, Dict[str, Any]]:
        ...
