# ファイル整理のまとめ

## ✅ 実施した作業

### 1. アーカイブフォルダの作成
- `_archive/` フォルダを作成
- 以下のアーカイブファイルを作成：
  - `_archive/HEROKU_DOCS.md` - Heroku関連ドキュメント
  - `_archive/TROUBLESHOOTING.md` - トラブルシューティング関連
  - `_archive/COMPLEX_DOCS.md` - 複雑な構成に関するドキュメント

### 2. Code.gsの更新
- `gas/Code.gs.simple` の内容を `gas/Code.gs` に上書き

### 3. README.mdの更新
- GASのみ版に合わせて更新

## 🗑️ 削除対象のファイル

以下のファイルは削除することを推奨します（既にアーカイブにまとめています）：

### Python関連
- `python/` フォルダ全体

### Heroku設定ファイル
- `Procfile`
- `requirements.txt`
- `runtime.txt`

### Pythonスクリプト
- `get_channel_id.py`
- `test_slack_connection.py`

### ログファイル（古いもの）
- `logs/` フォルダ（必要に応じて）

### アーカイブ済みドキュメント（個別ファイル）
以下のファイルは `_archive/` にまとめたため削除可能：

#### Heroku関連
- `HEROKU_DEPLOY_GUIDE.md`
- `HEROKU_GITHUB_LINK.md`
- `HEROKU_STATUS_CHECK.md`

#### トラブルシューティング
- `FOLDER_MOVE_TROUBLESHOOTING.md`
- `TROUBLESHOOTING_FILE_NOT_FOUND.md`
- `SLACK_TROUBLESHOOTING.md`
- `DEBUG_GUIDE.md`

#### 複雑な構成関連
- `CURRENT_STATUS_AND_ALTERNATIVES.md`
- `SETUP_GUIDE.md`
- `FOLDER_SETUP_GUIDE.md`
- `GAS_DEPLOY_GUIDE.md`
- `GAS_DEPLOY_STEP_BY_STEP.md`
- `GAS_UPDATE_CHECKLIST.md`
- `OAUTH_SETUP.md`
- `FORMAT_CUSTOMIZATION_GUIDE.md`
- `FORMAT_IMPLEMENTATION.md`
- `MINUTES_FORMAT_GUIDE.md`
- `SLACK_CHANNEL_ID_GUIDE.md`
- `GITHUB_SETUP.md`
- `REQUIREMENTS_CHECK.md`
- `QUICK_START.md`
- `QUICK_FIX_FOLDER.md`
- `HOW_TO_RUN.md`
- `SCHEDULE.md`
- `NEXT_STEPS.md`

## 📝 残すファイル

### 必須ファイル
- `README.md`
- `SIMPLE_SETUP_GUIDE.md`
- `移行ガイド.md`
- `TECHNOLOGY_CHOICE_GUIDE.md`（学びのため）
- `gas/Code.gs`
- `gas/appsscript.json`
- `gas/Code.gs.simple`（参考用として残すか削除）

### 参考ファイル
- `要約_構造の整理とシンプル化.md`
- `STRUCTURE_ANALYSIS.md`
- `STRUCTURE_COMPARISON.md`
- `技術選択_簡潔版.md`

### 設定ファイル（参考用）
- `config/participants.json`

## ⚠️ 注意

削除する前に、必要な情報がアーカイブに保存されていることを確認してください。

