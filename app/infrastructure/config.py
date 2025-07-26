"""VertexAI関連の設定"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートの.envファイルを明示的に読み込み
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


class VertexAIConfig:
    """VertexAI設定クラス"""
    
    def __init__(self):
        self.project_id: Optional[str] = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-northeast1")
        
        # 認証情報のパスを絶対パスに変換
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if credentials_path and not os.path.isabs(credentials_path):
            # 相対パスの場合、プロジェクトルートからの絶対パスに変換
            project_root = Path(__file__).parent.parent.parent
            self.credentials_path = str(project_root / credentials_path)
        else:
            self.credentials_path = credentials_path
        
        # Geminiモデル設定
        self.model_name: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        
    def validate(self) -> bool:
        """設定の妥当性をチェック"""
        if not self.project_id:
            raise ValueError(f"GOOGLE_CLOUD_PROJECT環境変数が設定されていません。現在の値: {self.project_id}")
        if not self.credentials_path:
            raise ValueError(f"GOOGLE_APPLICATION_CREDENTIALS環境変数が設定されていません。現在の値: {self.credentials_path}")
        if not os.path.exists(self.credentials_path):
            raise ValueError(f"認証情報ファイルが見つかりません: {self.credentials_path}")
        return True


# グローバル設定インスタンス
vertex_config = VertexAIConfig()
