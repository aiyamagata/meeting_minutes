# Herokuデプロイガイド - ステップバイステップ

このガイドでは、初心者でもわかりやすくHerokuへのデプロイを進めます。

---

## 📋 デプロイ前のチェックリスト

- [ ] Herokuアカウントを作成済み
- [ ] GitHubアカウントを作成済み
- [ ] ローカル環境で動作確認済み
- [ ] `config/config.json` が正しく設定されている

---

## ステップ1: Heroku CLI のインストール確認

### 確認方法

```bash
heroku --version
```

**✅ インストール済みの場合**: バージョン番号が表示されます
**❌ 未インストールの場合**: 以下の手順でインストール

### macOS でのインストール

```bash
brew tap heroku/brew && brew install heroku
```

### その他のOS

[Heroku CLI インストールガイド](https://devcenter.heroku.com/articles/heroku-cli) を参照

---

## ステップ2: Heroku へのログイン

### 手順

1. **ログインコマンドを実行**
   ```bash
   heroku login
   ```

2. **ブラウザが自動的に開きます**
   - Herokuのログインページが表示されます
   - メールアドレスとパスワードでログイン
   - 「Log in」をクリック

3. **ログイン成功の確認**
   - ターミナルに「Logged in as ...」と表示されれば成功

### トラブルシューティング

- ブラウザが開かない場合: `heroku login -i` でコマンドラインからログイン

---

## ステップ3: Heroku アプリの作成

### 手順

1. **アプリを作成**
   ```bash
   heroku create meeting-minutes-bot
   ```
   
   **注意**: アプリ名は一意である必要があります。既に使用されている場合は、別の名前に変更してください。
   例: `meeting-minutes-bot-2024`

2. **作成成功の確認**
   - 以下のような出力が表示されます：
     ```
     Creating ⬢ meeting-minutes-bot... done
     https://meeting-minutes-bot.herokuapp.com/ | https://git.heroku.com/meeting-minutes-bot.git
     ```

3. **アプリのURLをメモ**
   - 後でWebhook URLとして使用します

---

## ステップ4: 環境変数の設定

### 必要な環境変数

1. **Slack Bot Token**
2. **Google Drive フォルダID**（オプション）
3. **OAuth認証情報**（OAuth 2.0を使用している場合）

### 設定方法

#### 方法1: コマンドラインから設定（推奨）

```bash
# Slack Bot Token（実際のトークンに置き換える）
heroku config:set SLACK_BOT_TOKEN="xoxb-your-token-here"

# Google Drive フォルダID（オプション）
heroku config:set GOOGLE_DRIVE_FOLDER_ID="1w1u0bBBtt8wHFbJOx8h3UzBMvO1PzQZi"

# OAuth認証方法
heroku config:set GOOGLE_AUTH_METHOD="oauth2"
```

#### 方法2: Heroku Dashboardから設定

1. [Heroku Dashboard](https://dashboard.heroku.com/) にアクセス
2. アプリを選択
3. 「Settings」タブを選択
4. 「Config Vars」セクションで「Reveal Config Vars」をクリック
5. 環境変数を追加

### 環境変数の確認

```bash
heroku config
```

---

## ステップ5: OAuth認証情報の設定（重要）

OAuth 2.0を使用している場合、認証情報をHerokuに配置する必要があります。

### 方法1: 環境変数として設定（推奨）

```bash
# credentials.json を環境変数として設定
heroku config:set OAUTH_CREDENTIALS_JSON="$(cat config/credentials.json)"

# token.json を環境変数として設定（ローカルで作成したもの）
heroku config:set OAUTH_TOKEN_JSON="$(cat config/token.json)"
```

### 方法2: コードを修正して環境変数から読み込む

環境変数から認証情報を読み込むようにコードを修正する必要があります。

---

## ステップ6: GitHub との連携

### 6-1. Gitリポジトリの初期化

```bash
# プロジェクトルートで実行
git init
```

### 6-2. .gitignore の確認

機密情報がコミットされないように確認：

```bash
cat .gitignore
```

以下のファイルが含まれていることを確認：
- `config/config.json`
- `config/credentials.json`
- `config/token.json`
- `config/service_account.json`

### 6-3. 初回コミット

```bash
git add .
git commit -m "Initial commit: Meeting minutes automation tool"
```

### 6-4. GitHub リポジトリの作成

1. [GitHub](https://github.com/) にアクセス
2. 「New repository」をクリック
3. リポジトリ名を入力（例: `meeting-minutes-bot`）
4. 「Create repository」をクリック

### 6-5. GitHub へのプッシュ

```bash
# リモートリポジトリを追加（URLは実際のリポジトリURLに置き換える）
git remote add origin https://github.com/your-username/meeting-minutes-bot.git

# ブランチ名を main に変更
git branch -M main

# GitHub にプッシュ
git push -u origin main
```

### 6-6. Heroku と GitHub の連携

1. [Heroku Dashboard](https://dashboard.heroku.com/) にアクセス
2. アプリを選択
3. 「Deploy」タブを選択
4. 「Deployment method」セクションで「GitHub」を選択
5. GitHubアカウントと連携（初回のみ）
6. リポジトリを検索して選択
7. 「Connect」をクリック
8. 「Enable Automatic Deploys」を有効化（オプション）
9. 「Deploy Branch」をクリックして初回デプロイ

---

## ステップ7: デプロイの確認

### ログの確認

```bash
heroku logs --tail
```

### アプリの状態確認

```bash
heroku ps
```

### エラーの確認

```bash
heroku logs --tail | grep -i error
```

---

## ステップ8: スケジューラーの設定（オプション）

定期実行が必要な場合：

### 8-1. Heroku Scheduler の追加

```bash
heroku addons:create scheduler:standard
```

### 8-2. ジョブの設定

1. [Heroku Scheduler](https://dashboard.heroku.com/scheduler) にアクセス
2. アプリを選択
3. 「Create job」をクリック
4. 以下の設定：
   - Run Command: `python python/main.py`
   - Schedule: `Every 10 minutes`（必要に応じて調整）
5. 「Save job」をクリック

---

## 🎉 デプロイ完了！

これでHerokuへのデプロイが完了しました。

### 次のステップ

1. GAS（Google Apps Script）の設定
2. Webhook URLの設定
3. エンドツーエンドテスト

---

## ⚠️ 注意事項

1. **無料プランの制限**
   - 月550時間の実行時間制限
   - 30分間アクセスがないとスリープ

2. **環境変数の管理**
   - 機密情報は環境変数で管理
   - GitHubにコミットしない

3. **ログの確認**
   - 定期的にログを確認してエラーがないかチェック

