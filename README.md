# Google Meet 議事録自動生成・Slack投稿ツール

## 📋 プロジェクト概要

Google Meetの文字起こしを取得し、自社フォーマットに整形してGoogle Documentとして保存、Slackに自動投稿するツールです。

**GASのみで動作するシンプルな構成**になっています。

## 🎯 主な機能

- ✅ Google Meetの文字起こしを自動取得
- ✅ 参加者名の自動修正（ニックネーム → 正式名）
- ✅ 指定フォーマットに沿った議事録の自動生成
- ✅ Google Documentとして自動保存
- ✅ Slackチャンネルへの自動投稿
- ✅ （オプション）Gemini APIを使用したAI分類機能

## 🛠️ 使用技術

- **Google Apps Script (GAS)**: 全ての処理（ファイル検索・テキスト処理・Document作成・Slack投稿）
- **Slack API**: 自動投稿
- **Google Workspace API**: Document作成・管理（GASのDocumentAppを使用）
- **Gemini API**（オプション）: AI分類機能

## 🎨 構成の特徴

- ✅ **GASのみで動作**（Python/Heroku不要）
- ✅ **シンプルで管理が容易**
- ✅ **エラーが少ない**
- ✅ **完全無料**

## 📁 プロジェクト構成

```
meeting_minutes for everyone/
├── README.md                          # このファイル
├── セットアップガイド.md               # セットアップ手順（統合版）
├── TECHNOLOGY_CHOICE_GUIDE.md        # 技術選択ガイド（Heroku vs GAS）
├── gas/                              # Google Apps Script
│   ├── Code.gs                      # メインスクリプト
│   └── appsscript.json              # マニフェスト
├── config/                           # 設定ファイル（参考用）
│   └── participants.json            # 参加者名マッピング（参考用）
└── _archive/                        # アーカイブ（旧構成のドキュメント）
    ├── HEROKU_DOCS.md
    ├── TROUBLESHOOTING.md
    └── COMPLEX_DOCS.md
```

## 🚀 クイックスタート

### 1. GASプロジェクトを作成

1. [Google Apps Script](https://script.google.com/) にアクセス
2. 「新しいプロジェクト」を作成
3. `gas/Code.gs` の内容をコピーして貼り付け

### 2. 設定を確認・変更

`Code.gs` の先頭部分で以下を設定：

```javascript
const CONFIG = {
  TRANSCRIPT_FOLDER_ID: 'あなたのフォルダID',
  PROCESSED_FOLDER_ID: 'あなたのフォルダID',
  SEARCH_DAYS: 30
};

const PARTICIPANT_MAPPING = {
  'ニックネーム': '正式名',
  // ...
};
```

### 3. Slack設定

GASの「プロジェクトの設定」→「スクリプト プロパティ」で：
- `SLACK_BOT_TOKEN`: Slack Bot Token
- `SLACK_CHANNEL`: 投稿先チャンネル（オプション）

### 4. テスト実行

`testGetMeetingTranscripts` 関数を実行して動作確認

詳細は **[セットアップガイド.md](./セットアップガイド.md)** を参照してください。

## 📚 ドキュメント

このプロジェクトのドキュメントは以下の3つに集約されています：

1. **[セットアップガイド.md](./セットアップガイド.md)** - 完全なセットアップガイド
   - 初期設定手順
   - Slack設定方法
   - Gemini API設定方法
   - Herokuからの移行手順
   - トラブルシューティング

2. **[TECHNOLOGY_CHOICE_GUIDE.md](./TECHNOLOGY_CHOICE_GUIDE.md)** - 技術選択ガイド
   - Heroku vs GAS の比較
   - 技術選択の判断基準
   - 各技術の特徴と適性

3. **README.md**（このファイル）- プロジェクト概要とクイックスタート

## ⚙️ 必要な準備

### アカウント・アクセス権限
- Google Workspace アカウント（管理者権限推奨）
- Slack ワークスペース（管理者権限推奨）

### API トークン・認証情報
- Slack App の作成（Bot Token）
- （オプション）Gemini API Key（AI分類機能を使用する場合）

## 🔐 セキュリティ注意事項

- Slack Bot TokenはGASのプロパティサービスで管理（GitHubにコミットしない）
- Gemini API KeyはGASのプロパティサービスで管理（GitHubにコミットしない）
- フォルダIDはコード内で管理（必要に応じてプロパティサービスに移行可能）

## 📞 サポート

実装中に問題が発生した場合は、`セットアップガイド.md`のトラブルシューティングセクションを参照してください。

## 📝 ライセンス

このプロジェクトは社内利用を想定しています。

---

## 🔄 旧構成からの移行について

このプロジェクトは、以前は **GAS + Python/Heroku** の構成でしたが、**GASのみ版**に移行しました。

**移行理由：**
- シンプルで管理が容易
- エラーが少ない
- 完全無料
- 機能は同等に実現可能

詳細は **[セットアップガイド.md](./セットアップガイド.md)** の「HerokuからGASのみ版への移行」セクションを参照してください。
