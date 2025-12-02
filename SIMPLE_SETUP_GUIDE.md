# GASのみ版 セットアップガイド

## 📋 概要

このガイドでは、**GASのみで動作するシンプルな議事録自動生成ツール**のセットアップ方法を説明します。

**従来版（GAS + Python/Heroku）と比較して：**
- ✅ シンプル（1つのファイルのみ）
- ✅ エラーが少ない
- ✅ 管理が容易
- ✅ 無料で動作

## 🎯 前提条件

- Google Workspace アカウント
- Slack ワークスペース（Bot Token が必要）
- Google Drive の適切なアクセス権限

## 📝 セットアップ手順

### ステップ1: Google Apps Script プロジェクトの作成

1. [Google Apps Script](https://script.google.com/) にアクセス
2. 「新しいプロジェクト」をクリック
3. プロジェクト名を変更（例: `meeting-minutes-auto`）

### ステップ2: コードの配置

1. プロジェクトに `Code.gs` ファイルが表示されていることを確認
2. `gas/Code.gs.simple` の内容をコピー
3. `Code.gs` の内容を全て削除し、コピーした内容を貼り付け
4. 保存（Ctrl+S または Cmd+S）

### ステップ3: 設定の確認と変更

`Code.gs` の先頭部分にある設定を確認・変更します：

```javascript
const CONFIG = {
  // 文字起こしファイルを保存するフォルダID
  TRANSCRIPT_FOLDER_ID: '1qHsTK30zKVl2bt2IhlXG79jCNW2IfUb_',
  
  // 議事録ファイルの保存先フォルダID
  PROCESSED_FOLDER_ID: '1w1u0bBBtt8wHFbJOx8h3UzBMvO1PzQZi',
  
  // 検索する日付範囲（過去N日）
  SEARCH_DAYS: 30,
  
  // 文字起こしファイルの命名パターン
  TRANSCRIPT_PATTERN: /Gemini によるメモ|文字起こし|transcript|meeting.*transcript/i
};
```

#### フォルダIDの取得方法

1. Google Driveでフォルダを開く
2. ブラウザのアドレスバーからIDを確認
   - URL例: `https://drive.google.com/drive/folders/1qHsTK30zKVl2bt2IhlXG79jCNW2IfUb_`
   - `1qHsTK30zKVl2bt2IhlXG79jCNW2IfUb_` の部分がフォルダID

### ステップ4: 参加者名マッピングの設定

`Code.gs` の中の `PARTICIPANT_MAPPING` を編集します：

```javascript
const PARTICIPANT_MAPPING = {
  'Co., Ltd OKAMOTO BROTHERS': '山形',
  'Creative Team ziek': '銅金',
  'R O': '竜',
  'Rico Yamazaki': 'リコ',
  'Tatsuya Okamoto': '龍允',
  'TAT': '龍允',
  'johnny leatherreport': 'ジョニー'
  // 必要に応じて追加
};
```

### ステップ5: Slack設定

1. GASのエディタで「プロジェクトの設定」（歯車アイコン）をクリック
2. 「スクリプト プロパティ」セクションで以下を追加：

| プロパティ | 値 | 説明 |
|-----------|-----|------|
| `SLACK_BOT_TOKEN` | `xoxb-...` | Slack Bot Token（後述） |
| `SLACK_CHANNEL` | `#meeting-minutes` | 投稿先チャンネル（オプション） |

#### Slack Bot Token の取得方法

1. [Slack API](https://api.slack.com/apps) にアクセス
2. 「Create New App」をクリック
3. 「From scratch」を選択
4. App名とワークスペースを選択
5. 「OAuth & Permissions」を開く
6. 「Scopes」セクションの「Bot Token Scopes」に以下を追加：
   - `chat:write`（メッセージを投稿する権限）
7. 「Install to Workspace」をクリック
8. 表示された「Bot User OAuth Token」（`xoxb-` で始まる）をコピー
9. 上記の `SLACK_BOT_TOKEN` に設定

### ステップ6: 権限の承認

1. GASのエディタで関数 `testGetMeetingTranscripts` を選択
2. 「実行」ボタンをクリック
3. 「権限を確認」をクリック
4. 自分のGoogleアカウントを選択
5. 「詳細」→「[プロジェクト名]に移動（安全ではないページ）」をクリック
6. 権限を承認：
   - Google Drive へのアクセス
   - Google Docs へのアクセス

### ステップ7: テスト実行

1. `testGetMeetingTranscripts` 関数を実行
2. 実行ログを確認（「表示」→「ログ」）
3. エラーがないか確認

### ステップ8: 定期実行の設定（トリガー）

1. GASのエディタで「トリガー」アイコン（時計）をクリック
2. 「トリガーを追加」をクリック
3. 以下の設定でトリガーを作成：
   - **実行する関数**: `getMeetingTranscripts`
   - **イベントのソース**: `時間主導型`
   - **時間ベースのトリガー**: `時間ベースのタイマー`
   - **時間の間隔**: `1時間おき` または `6時間おき`
4. 「保存」をクリック

## 🔧 トラブルシューティング

### フォルダが見つからないエラー

- フォルダIDが正しいか確認
- GASを実行しているアカウントがフォルダにアクセス権限を持っているか確認

### ファイルが読み込めない

- ファイルがGoogle Document形式か確認
- ファイルのアクセス権限を確認

### Slackに投稿されない

- `SLACK_BOT_TOKEN` が正しく設定されているか確認
- Botがチャンネルに追加されているか確認（`/invite @bot名`）
- 実行ログでエラーメッセージを確認

### 処理済みファイルが再度処理される

- ファイルの説明欄に `PROCESSED:` が含まれているか確認
- 処理済みマークが正しく追加されているか確認

## 📊 実行ログの確認

1. GASのエディタで「表示」→「ログ」をクリック
2. 実行時のログを確認
3. エラーがあれば、エラーメッセージを確認して対処

## 🔍 デバッグ機能

### ファイル検索のデバッグ

`debugListFiles` 関数を実行すると、検索対象のファイル一覧が表示されます。

## 📝 注意事項

1. **実行時間制限**
   - GASの通常のトリガーは6分でタイムアウト
   - 大量のファイルを処理する場合は、処理を分割する必要がある可能性があります

2. **同時実行の制限**
   - 同時実行できるスクリプト数に制限があります
   - トリガーの実行間隔を適切に設定してください

3. **参加者名マッピング**
   - 新しい参加者が追加された場合は、`PARTICIPANT_MAPPING` を更新してください

## ✅ 移行チェックリスト

現在の複雑な構造（GAS + Python/Heroku）から移行する場合：

- [ ] 新しいGASプロジェクトを作成
- [ ] `Code.gs.simple` の内容をコピー
- [ ] 設定（フォルダID、参加者マッピング）を確認・変更
- [ ] Slack設定を追加
- [ ] 権限を承認
- [ ] テスト実行
- [ ] トリガーを設定
- [ ] 動作確認
- [ ] 旧システム（Heroku）を停止（オプション）

## 🎉 完了

これで、GASのみで動作するシンプルな議事録自動生成ツールが使用できます！

問題が発生した場合は、実行ログを確認してトラブルシューティングセクションを参照してください。

