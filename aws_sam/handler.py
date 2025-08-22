import os
from mangum import Mangum
from app.main import app 

# 環境変数からステージ名を取得
stage = os.getenv("ENVIRONMENT", "dev")

# API Gateway のベースパスを設定（ステージ名 + カスタム接頭辞を取り除く）
lambda_handler = Mangum(app, api_gateway_base_path=f"/{stage}/user-chat", lifespan="off")
