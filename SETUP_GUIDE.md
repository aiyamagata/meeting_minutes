# 実装手引き - Google Meet 議事録自動生成ツール

## 📖 目次

1. [事前準備](#事前準備)
2. [環境構築](#環境構築)
3. [Google Apps Script の実装](#google-apps-script-の実装)
4. [Python スクリプトの実装](#python-スクリプトの実装)
5. [Heroku へのデプロイ](#heroku-へのデプロイ)
6. [動作確認](#動作確認)
7. [トラブルシューティング](#トラブルシューティング)

---

## 事前準備

### 1. 必要なアカウントの準備

#### Google Workspace アカウント
- [ ] Google Workspace アカウントにログイン
- [ ] Google Drive へのアクセス権限を確認
- [ ] Google Meet の録音・文字起こし機能が有効か確認

#### Slack ワークスペース
- [ ] Slack ワークスペースに管理者権限でログイン
- [ ] 投稿先のチャンネルを事前に作成（例: `#meeting-minutes`）

#### Heroku アカウント
- [ ] [Heroku](https://www.heroku.com/) でアカウント作成
- [ ] Heroku CLI をインストール（後述）

#### GitHub アカウント
- [ ] [GitHub](https://github.com/) でアカウント作成
- [ ] 新しいリポジトリを作成

---

## 環境構築

### 1. ローカル環境のセットアップ

#### Python のインストール確認
```bash
python3 --version
# Python 3.8以上が必要
```

#### 仮想環境の作成
```bash
cd "meeting_minutes for everyone"
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate  # Windows
```

#### 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

### 2. Google Cloud Platform の設定

#### プロジェクトの作成
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成（例: `meeting-minutes-tool`）
3. プロジェクトを選択

#### API の有効化
以下のAPIを有効化します：
- [ ] Google Drive API
- [ ] Google Docs API
- [ ] Google Meet API（利用可能な場合）

**手順：**
1. 「APIとサービス」→「ライブラリ」を選択
2. 上記のAPIを検索して有効化

#### サービスアカウントの作成
1. 「APIとサービス」→「認証情報」を選択
2. 「認証情報を作成」→「サービスアカウント」を選択
3. サービスアカウント名を入力（例: `meeting-minutes-bot`）
4. 「作成して続行」をクリック
5. ロールは「編集者」を選択
6. 「完了」をクリック

#### 認証情報のダウンロード

**⚠️ 重要：サービスアカウントキーの作成が無効になっている場合**

組織ポリシー（`iam.disableServiceAccountKeyCreation`）によってキー作成がブロックされている場合、以下のいずれかの方法で対処してください：

##### 方法1: 組織ポリシー管理者に依頼（推奨）

1. **組織ポリシー管理者に連絡**
   - `roles/orgpolicy.policyAdmin` 権限を持つ管理者に依頼
   - サービスアカウントキー作成の必要性を説明
   - 一時的にポリシーを無効化してもらうか、例外を追加してもらう

2. **ポリシーが解除されたら、通常の手順を実行**
   - 作成したサービスアカウントをクリック
   - 「キー」タブを選択
   - 「キーを追加」→「新しいキーを作成」
   - JSON形式を選択してダウンロード
   - ダウンロードしたJSONファイルを `config/service_account.json` として保存

##### 方法2: OAuth 2.0認証を使用（代替案）✅ 実装済み

サービスアカウントキーが使えない場合、OAuth 2.0認証を使用できます。コードは既に対応済みです。

**📋 全体の流れ（5つのステップ）**

1. ✅ OAuth同意画面の設定
2. ✅ OAuth 2.0認証情報の作成・ダウンロード
3. ⬇️ ダウンロードしたファイルの配置
4. ⬇️ 設定ファイルの更新
5. ⬇️ 初回認証の実行

---

**手順1: OAuth同意画面の設定**

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを選択
3. 「APIとサービス」→「OAuth同意画面」を選択
4. **ユーザータイプを選択**
   - **内部**: 組織内のユーザーのみ（Google Workspaceアカウントの場合）
   - **外部**: 一般ユーザーも含む（個人アカウントの場合）
5. **アプリ情報を入力**
   - アプリ名: `Meeting Minutes Tool`（任意）
   - ユーザーサポートメール: 自分のメールアドレス
   - デベロッパーの連絡先情報: 自分のメールアドレス
6. 「保存して次へ」をクリック
7. スコープはそのまま「保存して次へ」
8. テストユーザー（必要に応じて）を追加して「保存して次へ」
9. 「ダッシュボードに戻る」をクリック

**✅ 手順1完了！** 次はOAuth 2.0認証情報を作成します。

---

**手順2: OAuth 2.0認証情報の作成**

1. 「APIとサービス」→「認証情報」を選択
2. 「認証情報を作成」→「OAuth クライアント ID」を選択
3. **アプリケーションの種類を選択**
   - 「デスクトップアプリ」を選択
   - 名前を入力（例: `Meeting Minutes Desktop Client`）
4. 「作成」をクリック
5. **認証情報をダウンロード**
   - 表示されたダイアログで「JSONをダウンロード」をクリック
   - ダウンロードしたJSONファイルを `config/credentials.json` として保存

**✅ 手順2完了！** ダウンロードしたファイルは、次の手順3でプロジェクトフォルダに配置します。

---

**手順3: ダウンロードしたファイルの配置**

1. **ダウンロードしたJSONファイルを確認**
   - ダウンロードフォルダに `client_secret_xxxxx.json` のような名前のファイルがあるはずです
   - このファイル名は長いので、後でリネームします

2. **プロジェクトフォルダに移動**
   ```bash
   cd "/Users/yamagataai/meeting_minutes for everyone"
   ```

3. **ファイルを配置**
   - ダウンロードしたJSONファイルを `config/credentials.json` にリネームして配置
   - または、コピーして配置：
     ```bash
     # 例: ダウンロードフォルダからコピーする場合
     cp ~/Downloads/client_secret_*.json config/credentials.json
     ```

4. **ファイルが正しく配置されたか確認**
   ```bash
   ls -la config/credentials.json
   # ファイルが存在し、サイズが0でないことを確認
   ```

**✅ 手順3完了！** 次は設定ファイルを更新します。

---

**手順4: 設定ファイルの作成・更新**

1. **設定ファイルが存在しない場合は作成**
   ```bash
   cp config/config.json.example config/config.json
   ```

2. **設定ファイルを編集**
   - テキストエディタで `config/config.json` を開く
   - 以下のように `google` セクションを更新：

   ```json
   {
     "slack": {
       "bot_token": "xoxb-your-bot-token-here",
       "channel": "#meeting-minutes"
     },
     "google": {
       "auth_method": "oauth2",
       "oauth_credentials_path": "config/credentials.json",
       "oauth_token_path": "config/token.json",
       "drive_folder_id": "your-folder-id-here"
     },
     "format": {
       "template": "default",
       "date_format": "%Y年%m月%d日"
     },
     "participants": {
       "mapping_file": "config/participants.json"
     }
   }
   ```

3. **重要なポイント**
   - `auth_method` を `"oauth2"` に設定（これが重要！）
   - `oauth_credentials_path` は `"config/credentials.json"` のまま
   - `drive_folder_id` は後で設定できます（今は空欄でもOK）

**✅ 手順4完了！** 次は初回認証を実行します。

---

**手順5: 初回認証の実行**

1. **仮想環境を有効化**（まだ有効化していない場合）
   ```bash
   source venv/bin/activate  # macOS/Linux
   # または
   venv\Scripts\activate  # Windows
   ```

2. **依存パッケージをインストール**（まだインストールしていない場合）
   ```bash
   pip install -r requirements.txt
   ```

3. **初回認証を実行**
   ```bash
   python python/main.py --test
   ```

4. **ブラウザが自動的に開きます**
   - 以下のような画面が表示されます：
     - 「Googleアカウントを選択」画面
     - 使用するGoogleアカウントを選択
   - 「このアプリは確認されていません」と表示される場合：
     - 「詳細」をクリック
     - 「（アプリ名）に移動（安全ではないページ）」をクリック
   - 「Meeting Minutes Tool があなたの Google アカウントへのアクセスをリクエストしています」画面で：
     - 「許可」をクリック

5. **認証完了の確認**
   - ブラウザに「認証フローが完了しました」と表示されます
   - ターミナルに以下のようなログが表示されます：
     ```
     INFO - OAuth 2.0認証モジュールを初期化しました
     INFO - OAuth 2.0認証フローを開始します
     INFO - 認証情報を保存しました: config/token.json
     INFO - Google Document作成モジュールを初期化しました
     ```

6. **`token.json` が作成されたか確認**
   ```bash
   ls -la config/token.json
   # ファイルが存在することを確認
   ```

**✅ 手順5完了！** OAuth 2.0認証のセットアップが完了しました！

---

**🎉 おめでとうございます！**

ここまで完了したら、OAuth 2.0認証のセットアップは完了です。次は動作確認を行います。

**手順6: 動作確認**

認証が完了したら、実際に動作するか確認します：

```bash
python python/main.py --test
```

以下のようなログが表示されれば成功です：
```
INFO - テキスト処理が完了しました
INFO - Google Documentを作成しました: https://docs.google.com/document/d/...
INFO - Slackに投稿しました
```

**⚠️ エラーが発生した場合**

よくあるエラーと対処法：

1. **`FileNotFoundError: credentials.json`**
   - `config/credentials.json` が正しい場所にあるか確認
   - ファイル名が正確か確認（`credentials.json` であること）

2. **`このアプリは確認されていません`**
   - OAuth同意画面で「テストユーザー」に自分のメールアドレスを追加
   - または、「詳細」→「（アプリ名）に移動」をクリック

3. **`認証フローが完了しました` と表示されるが、エラーが出る**
   - `config/token.json` が作成されているか確認
   - 再度実行してみる

**手順7: 本番環境（Heroku）へのデプロイ**（後で実施）

ローカル環境で動作確認ができたら、本番環境にデプロイします。詳細は「Herokuへのデプロイ」セクションを参照してください。

---

**📝 注意事項**

- ✅ `token.json` には有効期限がありますが、自動的にリフレッシュされます
- ✅ リフレッシュトークンが無効になった場合は、再度認証が必要です（`token.json` を削除して再実行）
- ✅ `credentials.json` と `token.json` は機密情報なので、GitHubにコミットしないでください（`.gitignore`に追加済み）
- ✅ 次回以降は、`token.json` が存在するため、ブラウザ認証は不要です

##### 方法3: 個人のGoogleアカウントを使用（開発・テスト用）

組織アカウントでない場合、個人のGoogleアカウントでプロジェクトを作成：

1. 個人のGoogleアカウントでGoogle Cloud Consoleにアクセス
2. 新しいプロジェクトを作成
3. 上記の手順でサービスアカウントキーを作成

**注意**: 本番環境では組織のポリシーに従って適切な認証方法を選択してください。

##### 方法4: Workload Identity Federation（高度）

Google Cloud外部の環境から認証する場合、Workload Identity Federationを使用できます。詳細は [Workload Identity Federation ドキュメント](https://cloud.google.com/iam/docs/workload-identity-federation) を参照してください。

---

**通常の手順（ポリシーが有効でない場合）:**

1. 作成したサービスアカウントをクリック
2. 「キー」タブを選択
3. 「キーを追加」→「新しいキーを作成」
4. JSON形式を選択してダウンロード
5. ダウンロードしたJSONファイルを `config/service_account.json` として保存

### 3. Slack App の作成

#### Slack App の作成手順
1. [Slack API](https://api.slack.com/apps) にアクセス
2. 「Create New App」→「From scratch」を選択
3. App名を入力（例: `Meeting Minutes Bot`）
4. ワークスペースを選択

#### Bot Token の取得
1. 「OAuth & Permissions」を選択
2. 「Scopes」セクションで以下の権限を追加：
   - `chat:write` - メッセージを投稿
   - `files:write` - ファイルをアップロード（必要に応じて）
3. 「Install to Workspace」をクリック
4. 表示された「Bot User OAuth Token」をコピー（`xoxb-`で始まる文字列）

#### チャンネルへの追加
1. Slackで投稿先チャンネルを開く
2. チャンネル名をクリック→「統合」を選択
3. 作成したAppを追加

### 4. 設定ファイルの作成

#### config.json の作成
```bash
cp config/config.json.example config/config.json
```

`config/config.json` を編集：
```json
{
  "slack": {
    "bot_token": "xoxb-your-bot-token-here",
    "channel": "#meeting-minutes"
  },
  "google": {
    "drive_folder_id": "your-folder-id-here",
    "service_account_path": "config/service_account.json"
  },
  "format": {
    "template": "default",
    "date_format": "%Y年%m月%d日"
  }
}
```

#### participants.json の作成
参加者名のマッピングを設定：
```json
{
  "ニックネーム": "正式な名前",
  "たろう": "山田 太郎",
  "はなこ": "佐藤 花子"
}
```

---

## Google Apps Script の実装

### 1. GAS プロジェクトの作成

1. [Google Apps Script](https://script.google.com/) にアクセス
2. 「新しいプロジェクト」をクリック
3. プロジェクト名を変更（例: `Meeting Minutes Getter`）

### 2. コードの実装

`gas/Code.gs` の内容をコピーして、GASエディタに貼り付けます。

### 3. トリガーの設定

1. GASエディタで「時計アイコン（トリガー）」をクリック
2. 「トリガーを追加」を選択
3. 以下の設定：
   - 実行する関数: `getMeetingTranscripts`
   - イベントのソース: 時間主導型
   - 時間ベースのトリガー: 1時間おき
   - エラー通知設定: 毎日

### 4. 権限の付与

初回実行時に権限の許可を求められます：
1. 「権限を確認」をクリック
2. Googleアカウントを選択
3. 「詳細」→「（プロジェクト名）に移動」をクリック
4. 「許可」をクリック

---

## Python スクリプトの実装

### 1. ローカルでの動作確認

#### テスト実行

**⚠️ 重要: プロジェクトルートから実行してください**

```bash
# プロジェクトルートに移動（pythonディレクトリから実行しない）
cd "/Users/yamagataai/meeting_minutes for everyone"

# テスト実行
python python/main.py --test
```

**注意**: `cd python` してから実行すると、設定ファイルの相対パスが間違います。

#### 参加者名マッピングのテスト
```bash
python -c "from text_processor import ParticipantMapper; pm = ParticipantMapper('config/participants.json'); print(pm.map('たろう'))"
```

### 2. ログの確認

ログファイルは `logs/` ディレクトリに保存されます：
```bash
tail -f logs/app.log
```

---

## Heroku へのデプロイ

### 1. Heroku CLI のインストール

#### macOS
```bash
brew tap heroku/brew && brew install heroku
```

#### その他のOS
[Heroku CLI インストールガイド](https://devcenter.heroku.com/articles/heroku-cli) を参照

### 2. Heroku へのログイン
```bash
heroku login
```

### 3. Heroku アプリの作成
```bash
heroku create meeting-minutes-bot
```

### 4. 環境変数の設定
```bash
heroku config:set SLACK_BOT_TOKEN="xoxb-your-token"
heroku config:set GOOGLE_DRIVE_FOLDER_ID="your-folder-id"
heroku config:set SERVICE_ACCOUNT_JSON="$(cat config/service_account.json)"
```

### 5. GitHub との連携

#### リポジトリの初期化
```bash
git init
git add .
git commit -m "Initial commit"
```

#### GitHub へのプッシュ
```bash
git remote add origin https://github.com/your-username/meeting-minutes.git
git branch -M main
git push -u origin main
```

#### Heroku と GitHub の連携
1. [Heroku Dashboard](https://dashboard.heroku.com/) にアクセス
2. アプリを選択
3. 「Deploy」タブを選択
4. 「GitHub」を選択して連携
5. リポジトリを選択
6. 「Enable Automatic Deploys」を有効化

### 6. スケジューラーの設定

#### Heroku Scheduler の追加
```bash
heroku addons:create scheduler:standard
```

#### ジョブの設定
1. [Heroku Scheduler](https://dashboard.heroku.com/scheduler) にアクセス
2. 「Create job」をクリック
3. 以下の設定：
   - Run Command: `python python/main.py`
   - Schedule: `Every 10 minutes`（必要に応じて調整）

---

## 動作確認

### 1. 手動実行での確認

#### GAS の手動実行
1. GASエディタで `getMeetingTranscripts` 関数を選択
2. 「実行」ボタンをクリック
3. 実行ログを確認

#### Python の手動実行
```bash
python python/main.py
```

### 2. エンドツーエンドテスト

1. テスト用のGoogle Meetを録音
2. 文字起こしが生成されるまで待機（通常数分）
3. GASが文字起こしを取得
4. Pythonスクリプトが処理を実行
5. Google Documentが作成されることを確認
6. Slackに投稿されることを確認

### 3. ログの確認

#### GAS のログ
- GASエディタの「実行」タブで確認

#### Python のログ
```bash
# ローカル
tail -f logs/app.log

# Heroku
heroku logs --tail
```

---

## トラブルシューティング

### よくある問題と解決方法

#### 1. GAS で権限エラーが発生する
**問題**: 「このアプリは確認されていません」と表示される
**解決策**:
- GASエディタで「公開」→「ウェブアプリとして公開」を実行
- テストモードで実行する場合は、自分のアカウントで承認

#### 2. サービスアカウントキーの作成が無効になっている
**問題**: 「サービス アカウント キーの作成が無効になっています」と表示される
**原因**: 組織ポリシー（`iam.disableServiceAccountKeyCreation`）によってキー作成がブロックされている
**解決策**:
1. **組織ポリシー管理者に依頼**（推奨）
   - `roles/orgpolicy.policyAdmin` 権限を持つ管理者に連絡
   - サービスアカウントキー作成の必要性を説明
   - 一時的にポリシーを無効化してもらうか、例外を追加してもらう
2. **代替認証方法を使用**
   - OAuth 2.0認証を使用（個人アカウントの場合）
   - Workload Identity Federationを使用（外部環境から認証する場合）
3. **個人のGoogleアカウントでプロジェクトを作成**（開発・テスト用のみ）
   - 組織アカウントでない場合、個人アカウントでプロジェクトを作成
   - 詳細は上記の「認証情報のダウンロード」セクションを参照

#### 3. Google Drive API のエラー
**問題**: `403 Forbidden` エラー
**解決策**:
- Google Cloud ConsoleでAPIが有効化されているか確認
- サービスアカウントに適切な権限が付与されているか確認
- サービスアカウントのJSONファイルのパスが正しいか確認
- サービスアカウントキーが正しく作成されているか確認（上記の問題2を参照）

#### 4. Slack への投稿が失敗する
**問題**: `not_in_channel` エラー
**解決策**:
- Botをチャンネルに追加しているか確認
- Bot Tokenが正しいか確認
- `chat:write` スコープが付与されているか確認

#### 5. 参加者名が修正されない
**問題**: `participants.json` のマッピングが機能しない
**解決策**:
- JSONファイルの形式が正しいか確認（カンマ、引用符など）
- ファイルパスが正しいか確認
- ログでマッピング処理の結果を確認

#### 6. Heroku で環境変数が読み込めない
**問題**: `KeyError` や `None` が返される
**解決策**:
```bash
# 環境変数を確認
heroku config

# 環境変数を再設定
heroku config:set KEY="value"
```

#### 7. 文字起こしが取得できない
**問題**: GASが文字起こしを見つけられない
**解決策**:
- Google Meetの録音が完了しているか確認
- 文字起こしファイルがGoogle Driveに保存されているか確認
- 検索条件（日付範囲など）を調整

### デバッグのコツ

1. **段階的にテスト**
   - 各機能を個別にテスト
   - 小さな変更を加えて動作確認

2. **ログを活用**
   - 詳細なログを出力
   - エラー発生時のコンテキストを記録

3. **エラーメッセージを確認**
   - エラーメッセージの全文を読む
   - スタックトレースを確認

4. **ドキュメントを参照**
   - [Google Apps Script リファレンス](https://developers.google.com/apps-script/reference)
   - [Slack API ドキュメント](https://api.slack.com/docs)
   - [Heroku ドキュメント](https://devcenter.heroku.com/)

---

## 次のステップ

実装が完了したら、以下を検討してください：

1. **カスタマイズ**
   - 議事録フォーマットの調整
   - 参加者名マッピングの拡充
   - 通知内容のカスタマイズ

2. **最適化**
   - 処理速度の改善
   - エラーハンドリングの強化
   - ログの整理

3. **機能追加**
   - 複数チャンネルへの投稿
   - 議事録の要約機能
   - アクションポイントの自動抽出

---

## 参考リンク

- [Google Apps Script ドキュメント](https://developers.google.com/apps-script)
- [Slack API ドキュメント](https://api.slack.com/)
- [Heroku Python サポート](https://devcenter.heroku.com/articles/python-support)
- [Google Cloud Platform ドキュメント](https://cloud.google.com/docs)

