# OAuth 2.0認証セットアップガイド

サービスアカウントキーが作成できない場合の、OAuth 2.0認証のセットアップ手順です。

## 📋 前提条件

- Google Cloud Platform プロジェクトが作成済み
- 必要なAPIが有効化済み（Google Drive API、Google Docs API）
- Python環境がセットアップ済み

## 🚀 セットアップ手順

### Step 1: OAuth同意画面の設定

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを選択
3. 「APIとサービス」→「OAuth同意画面」を選択
4. **ユーザータイプを選択**
   - **内部**: 組織内のユーザーのみ（Google Workspaceアカウントの場合）
   - **外部**: 一般ユーザーも含む（個人アカウントの場合）
5. **アプリ情報を入力**
   - アプリ名: `Meeting Minutes Tool`
   - ユーザーサポートメール: 自分のメールアドレス
   - デベロッパーの連絡先情報: 自分のメールアドレス
6. 「保存して次へ」をクリック
7. スコープはそのまま「保存して次へ」
8. テストユーザー（必要に応じて）を追加して「保存して次へ」
9. 「ダッシュボードに戻る」をクリック

### Step 2: OAuth 2.0認証情報の作成

1. 「APIとサービス」→「認証情報」を選択
2. 「認証情報を作成」→「OAuth クライアント ID」を選択
3. **アプリケーションの種類を選択**
   - 「デスクトップアプリ」を選択
   - 名前を入力（例: `Meeting Minutes Desktop Client`）
4. 「作成」をクリック
5. **認証情報をダウンロード**
   - 表示されたダイアログで「JSONをダウンロード」をクリック
   - ダウンロードしたJSONファイルを `config/credentials.json` として保存

### Step 3: 設定ファイルの更新

`config/config.json` を編集：

```json
{
  "google": {
    "auth_method": "oauth2",
    "oauth_credentials_path": "config/credentials.json",
    "oauth_token_path": "config/token.json",
    "drive_folder_id": "your-folder-id-here"
  }
}
```

### Step 4: 初回認証の実行

1. 仮想環境を有効化：
   ```bash
   source venv/bin/activate  # macOS/Linux
   # または
   venv\Scripts\activate  # Windows
   ```

2. 依存パッケージをインストール（未インストールの場合）：
   ```bash
   pip install -r requirements.txt
   ```

3. 初回認証を実行：
   ```bash
   python python/main.py --test
   ```

4. **ブラウザが自動的に開きます**
   - Googleアカウントでログイン
   - 「このアプリは確認されていません」と表示される場合：
     - 「詳細」をクリック
     - 「（アプリ名）に移動」をクリック
   - アプリへのアクセス許可を承認

5. 認証が完了すると、`config/token.json` が自動的に作成されます

### Step 5: 動作確認

認証が成功したら、以下のようなログが表示されます：

```
INFO - OAuth 2.0認証モジュールを初期化しました
INFO - 保存されたトークンを読み込みました
INFO - Google Document作成モジュールを初期化しました
INFO - テキスト処理が完了しました
INFO - Google Documentを作成しました: https://docs.google.com/...
```

## 🔧 本番環境（Heroku）へのデプロイ

### 方法1: 環境変数を使用（推奨）

1. ローカルで作成した `token.json` の内容を環境変数として設定：
   ```bash
   heroku config:set OAUTH_TOKEN_JSON="$(cat config/token.json)"
   ```

2. 認証方法とパスを設定：
   ```bash
   heroku config:set GOOGLE_AUTH_METHOD="oauth2"
   heroku config:set OAUTH_CREDENTIALS_PATH="config/credentials.json"
   ```

3. `credentials.json` も環境変数として設定（またはHerokuのファイルシステムに配置）：
   ```bash
   heroku config:set OAUTH_CREDENTIALS_JSON="$(cat config/credentials.json)"
   ```

4. コードを修正して環境変数から読み込むようにする（必要に応じて）

### 方法2: ファイルとして配置（一時的）

1. `token.json` と `credentials.json` をHerokuのファイルシステムに配置
2. セキュリティ上の注意: これらのファイルは機密情報なので、適切に保護してください

## 🔄 トークンのリフレッシュ

OAuth 2.0トークンには有効期限があります。コードは自動的にトークンをリフレッシュしますが、リフレッシュトークンが無効になった場合は、再度認証が必要です。

再認証が必要な場合：

1. `config/token.json` を削除
2. 再度 `python python/main.py --test` を実行
3. ブラウザで再認証

## ⚠️ 注意事項

1. **機密情報の管理**
   - `credentials.json` と `token.json` は機密情報です
   - GitHubにコミットしないでください（`.gitignore`に追加済み）
   - 本番環境では環境変数を使用することを推奨

2. **トークンの有効期限**
   - アクセストークンは通常1時間で期限切れ
   - リフレッシュトークンは長期間有効（無効化されない限り）
   - コードは自動的にリフレッシュを試みます

3. **テストユーザー**
   - 外部アプリの場合、テストユーザーを追加する必要があります
   - OAuth同意画面でテストユーザーを追加してください

## 🐛 トラブルシューティング

### エラー: `OAuth 2.0認証情報ファイルが見つかりません`

- `config/credentials.json` が存在するか確認
- ファイルパスが正しいか確認

### エラー: `このアプリは確認されていません`

- OAuth同意画面で「テストユーザー」に自分のメールアドレスを追加
- または、アプリを公開（本番環境の場合）

### エラー: `トークンのリフレッシュに失敗しました`

- `config/token.json` を削除して再認証
- リフレッシュトークンが無効になっている可能性があります

### ブラウザが開かない

- ローカル環境で実行していることを確認
- ファイアウォールやセキュリティソフトがブロックしていないか確認

## 📚 参考リンク

- [Google OAuth 2.0 ドキュメント](https://developers.google.com/identity/protocols/oauth2)
- [Google API Python Client ドキュメント](https://github.com/googleapis/google-api-python-client)
- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - 詳細な実装手引き

