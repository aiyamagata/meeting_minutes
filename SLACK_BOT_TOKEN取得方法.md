# Slack Bot Token の取得方法

## 📋 手順

### 1. Slack APIにアクセス
- [Slack API](https://api.slack.com/apps) にアクセス
- Slackアカウントでログイン

### 2. 新しいAppを作成
- 「Create New App」をクリック
- 「From scratch」を選択
- App名を入力（例: `Meeting Minutes Bot`）
- ワークスペースを選択
- 「Create App」をクリック

### 3. Bot Token Scopesを設定
1. 左側のメニューから「OAuth & Permissions」をクリック
2. 下にスクロールして「Scopes」セクションを表示
3. 「Bot Token Scopes」セクションで「Add an OAuth Scope」をクリック
4. 以下のスコープを追加：
   - `chat:write` - メッセージを投稿する権限

### 4. ワークスペースにインストール
1. ページ上部の「Install to Workspace」をクリック
2. 権限の確認画面が表示されるので、「許可する」をクリック
3. ワークスペースにBotがインストールされます

### 5. Bot Tokenをコピー
1. インストール後、「OAuth & Permissions」ページに戻る
2. 「Bot User OAuth Token」セクションに表示されるトークンをコピー
   - トークンは `xoxb-` で始まります
   - 例: `xoxb-xxxxxxxxxxxx-xxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx`

### 6. GASのプロパティサービスに設定
1. GASのエディタで「プロジェクトの設定」（歯車アイコン）をクリック
2. 「スクリプト プロパティ」セクションを開く
3. 「行を追加」をクリック
4. 以下を設定：
   - **プロパティ**: `SLACK_BOT_TOKEN`
   - **値**: コピーしたトークン（`xoxb-...`）
5. 「保存」をクリック

### 7. オプション：投稿先チャンネルを設定
1. 同じ「スクリプト プロパティ」で
2. もう1行追加：
   - **プロパティ**: `SLACK_CHANNEL`
   - **値**: `#meeting-minutes`（または投稿したいチャンネル名）
3. 「保存」をクリック

### 8. Botをチャンネルに追加
1. Slackで投稿先チャンネルを開く（例: `#meeting-minutes`）
2. チャンネル名をクリック
3. 「統合」タブを選択
4. 「アプリを追加」をクリック
5. 作成したBotを検索して追加

または、チャンネルで以下のコマンドを実行：
```
/invite @Bot名
```

## ✅ 完了チェックリスト

- [ ] Slack APIでAppを作成
- [ ] `chat:write` スコープを追加
- [ ] ワークスペースにインストール
- [ ] Bot Tokenをコピー
- [ ] GASのプロパティサービスに設定
- [ ] Botをチャンネルに追加

## ⚠️ 注意事項

- Bot Tokenは機密情報です。GitHubにコミットしないでください
- Bot Tokenを共有しないでください
- トークンが漏洩した場合は、Slack APIで再生成してください

