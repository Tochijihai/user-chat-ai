# AI API (FastAPI × Poetry)

## 概要

Python + FastAPI + Poetry で構築した最小構成の AI マイクロサービスです。
Google Cloud Vertex AI（Gemini）との連携により、チャット形式の AI 会話機能を提供します。

## 使用技術

- Python 3.11
- FastAPI
- Poetry（依存管理・仮想環境）
- Pytest（テストフレームワーク）
- Ruff（静的解析・リント）

## 前提条件

| 必要ソフト | 推奨バージョン | インストール例                                                                     |             |
| ---------- | -------------- | ---------------------------------------------------------------------------------- | ----------- |
| **Python** | 3.11 系        | `brew install python@3.11` など                                                    |             |
| **Poetry** | 1.7 以上       | \`curl -sSL [https://install.python-poetry.org](https://install.python-poetry.org) | python3 -\` |
| **Git**    | ―              | `brew install git`                                                                 |             |

> **補足**: Homebrew で `poetry` を入れることもできますが、Poetry チームはスクリプト
> (`install-poetry.py`) 経由のインストールを推奨しています。

## フォルダ構成

```text
ai-api/
├── app/
│   ├── main.py                   # FastAPIアプリケーション（エントリーポイント）
│   ├── router.py                 # ルーティング管理（コントローラー）
│   ├── spec.py                   # API仕様とPydanticモデル定義
│   ├── domain/                   # ドメイン層（ビジネスロジック）
│   ├── infrastructure/           # インフラ層（外部API連携）
│   │   ├── config.py             # 設定管理（環境変数読み込み）
│   │   └── vertex_client.py      # VertexAI/Gemini クライアント
│   └── services/                 # アプリケーションサービス
│       └── gateways              # アプリケーションが依存する抽象（ポート）定義
├── tests/                        # テストファイル
├── .env                          # 環境変数設定
├── pyproject.toml                # Poetry設定・依存関係
└── README.md                     # このファイル
```

### 依存関係の流れ

router → services → domain ← infrastructure

---

## 端末に poetry を入れる

```bash
# 1. poetryを入れる
curl -sSL https://install.python-poetry.org | python3 -
```

```bash
# 2. パスを通す
export PATH="$HOME/.local/bin:$PATH"
```

## セットアップ手順

```bash
# 1. リポジトリ取得
git clone https://github.com/ai-agent-hackathon-team-kitamura/ai-agent-hackathon.git
cd ai-api

# 2. 依存インストール
poetry install   # ← npm で言う「npm install」に相当
```

> Poetry は自動でローカル仮想環境 (`.venv/`) を作り、その中に依存を展開します。

---

## 開発サーバーの起動

```bash
make dev
```

- [http://127.0.0.1:8000](http://127.0.0.1:8000) で稼働確認
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **ヘルスチェック**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

`--reload` オプションを付けるとファイル保存のたびにホットリロードされます。

---

## Poetry コマンド早見表

| npm コマンド         | Poetry コマンド            | 説明                 |
| -------------------- | -------------------------- | -------------------- |
| `npm install`        | `poetry install`           | 依存を一括導入       |
| `npm i axios --save` | `poetry add requests`      | ランタイム依存を追加 |
| `npm i jest -D`      | `poetry add -G dev pytest` | 開発依存を追加       |
| `npx eslint .`       | `poetry run ruff check .`  | 仮想環境内ツール実行 |
| `npm update`         | `poetry update`            | 依存を最新化         |

---

## テスト & リント

```bash
# ユニットテスト
poetry run pytest -q

# コードスタイル / 静的解析
poetry run ruff check .         # チェックのみ
poetry run ruff check . --fix   # 自動修正
```

`ruff` は flake8・isort・black 相当のチェックを高速に行う Linte です。

## 参考リンク

- FastAPI: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- Poetry: [https://python-poetry.org/](https://python-poetry.org/)
- Ruff: [https://docs.astral.sh/ruff/](https://docs.astral.sh/ruff/)

---
