# 開発サーバーの起動
dev:
	poetry run uvicorn app.main:app --reload

# 初回セットアップ：Poetryインストール＆パッケージインストール
setup:
	@echo "==> Poetry インストール"
	curl -sSL https://install.python-poetry.org | python3 - || true
	@echo "==> PATH を一時適用"
	export PATH="$$HOME/.local/bin:$$PATH"
	@echo "==> 依存関係インストール"
	poetry install

# AWS SAM関連コマンド
# poetry依存関係から、requirements.txtを生成（本番依存関係のみ）
export-lambda-req:
	@echo "==> Lambda用requirements.txtを生成"
	poetry export -f requirements.txt --output requirements.txt --without-hashes --only=main

# SAMビルド
sam-build: export-lambda-req
	@echo "==> SAM ビルド開始"
	sam build -t aws_sam/template.yaml

# SAMデプロイ（初回）
sam-deploy-guided: sam-build
	@echo "==> SAM デプロイ（初回設定）"
	sam deploy --guided

# SAMデプロイ（通常）
sam-deploy: sam-build
	@echo "==> SAM デプロイ"
	AWS_ACCESS_KEY_ID="AKXXXXXXXXXXXXX" AWS_SECRET_ACCESS_KEY="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" sam deploy

# SAMローカルテスト
sam-local:
	sam local start-api -t aws_sam/template.yaml

# デプロイされたAPIのテスト
test-api:
	@echo "==> ルートエンドポイントテスト"
	curl https://6mid2ndlv4.execute-api.ap-northeast-1.amazonaws.com/
	@echo "\n==> ヘルスチェックテスト"
	curl https://6mid2ndlv4.execute-api.ap-northeast-1.amazonaws.com/health
	@echo "\n==> チャットエンドポイントテスト"
	curl -X POST https://6mid2ndlv4.execute-api.ap-northeast-1.amazonaws.com/chat \
		-H "Content-Type: application/json" \
		-d '{"messages": [{"role": "user", "content": "こんにちは"}]}'

# SAMスタック削除
sam-delete:
	AWS_ACCESS_KEY_ID="AKXXXXXXXXXXXXX" AWS_SECRET_ACCESS_KEY="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" sam delete --stack-name user-chat-ai-api
