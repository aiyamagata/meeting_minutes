# Google Meet 議事録自動生成・Slack投稿ツール

## 📋 プロジェクト概要

Google Meetの文字起こしを取得し、自社フォーマットに整形してGoogle Documentとして保存、Slackに自動投稿するツールです。

## 🎯 主な機能

- ✅ Google Meetの文字起こしを自動取得
- ✅ 参加者名の自動修正（ニックネーム → 正式名）
- ✅ 指定フォーマットに沿った議事録の自動生成
- ✅ Google Documentとして自動保存
- ✅ Slackチャンネルへの自動投稿

## 🛠️ 使用技術

- **Google Apps Script (GAS)**: Google Meet文字起こしの取得
- **Python**: テキスト処理・整形
- **Heroku**: 定期実行・スケジューリング
- **GitHub**: コード管理
- **Slack API**: 自動投稿
- **Google Workspace API**: Document作成・管理

## 📁 プロジェクト構成

```
meeting_minutes for everyone/
├── README.md                 # このファイル
├── SETUP_GUIDE.md           # 詳細な実装手引き
├── SCHEDULE.md              # 実装スケジュール
├── gas/                     # Google Apps Script
│   ├── Code.gs             # メインスクリプト
│   └── appsscript.json     # マニフェスト
├── python/                   # Pythonスクリプト
│   ├── main.py             # メイン処理
│   ├── webhook.py          # Webhookエンドポイント（Heroku用）
│   ├── text_processor.py   # テキスト処理
│   ├── slack_poster.py     # Slack投稿
│   ├── google_doc_creator.py # Google Document作成
│   ├── google_oauth.py     # OAuth 2.0認証（サービスアカウント代替）
│   └── config.py           # 設定管理
├── config/                  # 設定ファイル
│   ├── config.json.example # 設定テンプレート
│   └── participants.json   # 参加者名マッピング
└── requirements.txt        # Python依存関係
```

## 🚀 クイックスタート

**最短で始める場合は [QUICK_START.md](./QUICK_START.md) を参照してください。**

詳細な実装手順：

1. **セットアップ手引きを確認**
   ```bash
   cat SETUP_GUIDE.md
   ```

2. **スケジュールを確認**
   ```bash
   cat SCHEDULE.md
   ```

3. **実装を開始**
   - `SETUP_GUIDE.md`に従って順番に実装を進めてください
   - 各ステップで動作確認を行いながら進めます

## 📚 ドキュメント

- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - 詳細な実装手引き
- [SCHEDULE.md](./SCHEDULE.md) - 実装スケジュール（2週間計画）
- [QUICK_START.md](./QUICK_START.md) - クイックスタートガイド
- [OAUTH_SETUP.md](./OAUTH_SETUP.md) - OAuth 2.0認証セットアップガイド（サービスアカウントキーが使えない場合）

## ⚙️ 必要な準備

### アカウント・アクセス権限
- Google Workspace アカウント（管理者権限推奨）
- Slack ワークスペース（管理者権限推奨）
- Heroku アカウント（無料プラン可）
- GitHub アカウント

### API トークン・認証情報
- Google Cloud Platform プロジェクト
- Slack App の作成（Bot Token）
- Heroku API Key

## 🔐 セキュリティ注意事項

- 認証情報は絶対にGitHubにコミットしないでください
- `.env`ファイルや`config.json`は`.gitignore`に追加済みです
- 本番環境では環境変数を使用してください

## 📞 サポート

実装中に問題が発生した場合は、`SETUP_GUIDE.md`のトラブルシューティングセクションを参照してください。

## 📝 ライセンス

このプロジェクトは社内利用を想定しています。

