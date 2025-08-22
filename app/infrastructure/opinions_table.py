# opinions_table.py
from __future__ import annotations
from decimal import Decimal
from typing import Dict, Any
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError


class OpinionsTable:
    def __init__(self):
        table_name = "opinions"
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        self.table = dynamodb.Table(table_name)

    def put_opinion(
        self,
        id: str,
        mail_address: str,
        opinion: str,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """1件のopinionを保存する"""        
        return self.table.put_item(Item={
            "id": id,
            "mailAddress": mail_address,
            "latitude": Decimal(str(latitude)),
            "longitude": Decimal(str(longitude)),
            "opinion": opinion
        })
