import os
import time
import uuid
from typing import List, Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError


class ChatTable:
    """DynamoDB へチャット内容を保存/取得するための薄いゲートウェイ"""

    def __init__(self) -> None:
        table_name = "chat"
        region = "ap-northeast-1"
        self._dynamodb = boto3.resource("dynamodb", region_name=region, endpoint_url="http://localhost:8002")
        self._table = self._dynamodb.Table(table_name)

    def put_chat_message(
        self,
        messages: List[Dict[str, str]],
        generated: str,
        chat_id: Optional[str] = None
    ) -> str:
        new_chat_id = chat_id or str(uuid.uuid4())

        self._table.put_item(Item={
            "chatId": new_chat_id,
            "messages": messages,
            "generated": generated
        })

        return new_chat_id
