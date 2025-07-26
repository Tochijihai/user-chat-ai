"""FastAPI アプリケーションのメインエントリーポイント"""

from dotenv import load_dotenv
from fastapi import FastAPI
from app.router import router

# 環境変数を読み込み
load_dotenv()

app = FastAPI(
    title="AI API",
    version="0.1.0",
    description="AI API",
)

# ルーターを登録
app.include_router(router)
