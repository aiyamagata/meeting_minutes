# クイックスタートガイド

このガイドは、最短でツールを動作させるための手順です。
詳細な手順は `SETUP_GUIDE.md` を参照してください。

## 🚀 5ステップで始める

### Step 1: 環境準備（30分）

```bash
# 1. Pythonの確認
python3 --version  # 3.8以上が必要

# 2. 仮想環境の作成
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# または venv\Scripts\activate  # Windows

# 3. 依存パッケージのインストール
pip install -r requirements.txt
```

### Step 2: Google Cloud設定（30分）

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. 以下のAPIを有効化：
   - Google Drive API
   - Google Docs API
3. サービスアカウントを作成
4. 認証情報JSONをダウンロード → `config/service_account.json` に保存

### Step 3: Slack App作成（15分）

1. [Slack API](https://api.slack.com/apps) でApp作成
2. Bot Token取得（`xoxb-`で始まる文字列）
3. `chat:write` スコープを追加
4. ワークスペースにインストール
5. 投稿先チャンネルにBotを追加

### Step 4: 設定ファイル作成（5分）

```bash
# 設定ファイルをコピー
cp config/config.json.example config/config.json

# 設定ファイルを編集
# - Slack Bot Tokenを設定
# - Google Drive フォルダIDを設定
```

`config/config.json` の例：
```json
{
  "slack": {
    "bot_token": "xoxb-実際のトークン",
    "channel": "#meeting-minutes"
  },
  "google": {
    "drive_folder_id": "実際のフォルダID",
    "service_account_path": "config/service_account.json"
  }
}
```

### Step 5: テスト実行（5分）

```bash
# テストモードで実行
python python/main.py --test
```

成功すれば、以下のような出力が表示されます：
```
INFO - テキスト処理が完了しました
INFO - Google Documentを作成しました: https://docs.google.com/...
INFO - Slackに投稿しました
```

## ✅ 動作確認チェックリスト

- [ ] Pythonスクリプトが正常に実行できる
- [ ] Google Documentが作成される
- [ ] Slackにメッセージが投稿される
- [ ] 参加者名が正しくマッピングされる

## 🔧 次のステップ

1. **GASの設定**: `gas/Code.gs` をGoogle Apps Scriptにコピー
2. **Herokuデプロイ**: `SETUP_GUIDE.md` の「Herokuへのデプロイ」セクションを参照
3. **カスタマイズ**: 議事録フォーマットや参加者名マッピングを調整

## ❓ トラブルシューティング

### エラー: `ModuleNotFoundError`
```bash
# 仮想環境が有効化されているか確認
which python  # venv内のpythonを指しているか確認

# 依存パッケージを再インストール
pip install -r requirements.txt
```

### エラー: `FileNotFoundError: service_account.json`
- `config/service_account.json` が存在するか確認
- ファイルパスが正しいか確認

### エラー: Slack投稿に失敗
- Bot Tokenが正しいか確認
- Botがチャンネルに追加されているか確認
- `chat:write` スコープが付与されているか確認

詳細なトラブルシューティングは `SETUP_GUIDE.md` を参照してください。

