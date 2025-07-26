"""全てのルーティングを管理"""
from fastapi import APIRouter
from datetime import datetime, timezone
from app.services.llm_chat_service import LLMChatService
from app.services.survey_service import SurveyService
from app.services.summery_service import SummeryService
from app.infrastructure.vertex_chat_llm_client import VertexChatLLMClient
from app.spec import ChatRequest, ChatResponse, HealthResponse, StartSurveyRequest, StartSurveyResponse, EvaluateResponse,EvaluateRequest, SummeryResponse
from app.infrastructure.firestore import upsert_user_engagement_survey, get_health, get_all_latest_health

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
    
    会話履歴を考慮してGemini AIが返答を生成します。
    roleは'user'（ユーザー）または'assistant'（AI）を指定してください。
    """
    llm_client = VertexChatLLMClient()
    # 依存性注入：インフラ層をアプリケーションサービスに注入
    chat_service = LLMChatService(llm_client)
    result = await chat_service.invoke(request.messages, request.schema)
    return result


@router.post("/start-survey", response_model=StartSurveyResponse)
async def start_survey(request: StartSurveyRequest):
    """
    面談開始API

    最新の健康状態データを基に、AIが面談開始のメッセージを生成します。
    """
    try:
        # 依存関係をセットアップし、適切なサービスを呼び出す
        llm_client = VertexChatLLMClient()
        survey_service = SurveyService(llm_client)

        # 前回のhealth情報を取得
        uid = request.uid
        health = get_health(uid)
        if health is None:
            return StartSurveyResponse(
            success=True,
            opening_message="""はじめまして！
日々のちょっとした不安やモヤモヤ、仕事のことでもプライベートのことでも、気軽に話してみてくださいね。
最近「困っていること」や「気になっていること」などありませんか？"""
            ) 
        else:
            # サービスを呼び出してビジネスロジックを実行
            result = await survey_service.create_opening_message(health)
            return StartSurveyResponse(
            success=True,
            opening_message=result.get("opening_message")
            )
    except Exception as e:
        # 予期せぬエラーが発生した場合のフォールバック
        return StartSurveyResponse(success=False, error=f"サーバー内部でエラーが発生しました: {str(e)}")


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_conversations(request: EvaluateRequest):
    """
    会話履歴をLLMが分析し、エンゲージメントスコア算出
    """
    created_at = datetime.today().strftime("%Y%m%d")

    try:
        # 依存関係をセットアップし、適切なサービスを呼び出す
        llm_client = VertexChatLLMClient()
        survey_service = SurveyService(llm_client)

        # サービスはHealthドメインオブジェクトを返す
        health_result = await survey_service.evaluate_conversations(request.messages)
        chat_history = [msg.dict() for msg in request.messages]
        now = datetime.now(timezone.utc)
        engagement_map = {
            "createdAt": now,
            "chatHistory": chat_history,
            "health": health_result.__dict__
        }
        upsert_user_engagement_survey(request.uid, engagement_map)

        # ドメインオブジェクトをレスポンスモデルが要求する辞書形式に変換する
        return EvaluateResponse(
            uid=request.uid,
            success=True,
            health=health_result.to_dict(),
            created_at=created_at
        )

    except Exception as e:
        return EvaluateResponse(uid=request.uid,success=False, created_at=created_at,error=f"サーバー内部でエラーが発生しました: {str(e)}")

@router.get("/summery", response_model=SummeryResponse)
async def summery():
    """
    LLMで分析し最新レポートに表示するデータを返す
    """
    healthList = get_all_latest_health()
    score_sum = 0
    note_list = []
    try:
        for i in healthList:
            score_sum += i["score"]
            note_list.append(i["note"])
        average_score = round(score_sum / len(healthList))

        llm_client = VertexChatLLMClient()
        # 依存性注入：インフラ層をアプリケーションサービスに注入
        summery_service = SummeryService(llm_client)
        result = await summery_service.create_summery(note_list)
        good_point = result["summery"]["goodPoint"]
        bad_point = result["summery"]["badPoint"]

        return SummeryResponse(
            average_score = average_score,
            success=True,
            good_point = good_point,
            bad_point = bad_point,
        )
    except Exception as e:
        return SummeryResponse(
            average_score=0,
            success=False,
            good_point="",
            bad_point="",
            error=f"サーバー内部でエラーが発生しました: {str(e)}",
        )

