"""全てのルーティングを管理"""
from fastapi import APIRouter
from app.services.llm_chat_service import LLMChatService
from app.infrastructure.bedrock_chat_llm_client import BedrockChatLLMClient
from app.spec import ChatRequest, ChatResponse, HealthResponse


router = APIRouter()


@router.get("/")
async def root():
    """ルートエンドポイント"""
    return {"message": "Hello World from AI API!"}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy", "version": "0.1.0"}


@router.post("/chat", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    チャット形式での会話エンドポイント
    
    会話履歴を考慮してBedrockが返答を生成します。
    roleは'user'（ユーザー）または'assistant'（AI）を指定してください。
    """
    llm_client = BedrockChatLLMClient()
    # 依存性注入：インフラ層をアプリケーションサービスに注入
    chat_service = LLMChatService(llm_client)
    result = await chat_service.invoke(request.messages, request.schema)
    return result