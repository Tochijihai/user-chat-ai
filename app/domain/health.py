from dataclasses import dataclass

@dataclass
class Health:
    """健康状態ドメインモデル"""
    score: int  # 1〜100 のスコア
    note: str   # 特記事項

    def to_dict(self) -> dict:
        """辞書形式に変換（LLM返却形式に揃える用途）"""
        return {"score": self.score, "note": self.note}

    @staticmethod
    def from_dict(data: dict) -> "Health":
        """辞書からインスタンス生成"""
        return Health(score=data["score"], note=data["note"])
