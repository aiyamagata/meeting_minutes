/**
 * Google Meet 議事録自動生成ツール（GASのみ版）
 * 
 * このスクリプトは、Google Drive内のGoogle Meet文字起こしファイルを検索し、
 * 処理して議事録を作成、Slackに投稿します。
 * 
 * 【特徴】
 * - GASのみで動作（Python/Heroku不要）
 * - シンプルで管理が容易
 * - エラーが少ない
 */

// ==================== 設定 ====================

const CONFIG = {
  // 文字起こしファイルを保存するフォルダID（「Meet Recordings」フォルダ）
  TRANSCRIPT_FOLDER_ID: '1qHsTK30zKVl2bt2IhlXG79jCNW2IfUb_',
  
  // 議事録ファイル（Google Document）の保存先フォルダID（「議事録」フォルダ）
  PROCESSED_FOLDER_ID: '1w1u0bBBtt8wHFbJOx8h3UzBMvO1PzQZi',
  
  // 検索する日付範囲（過去N日）
  SEARCH_DAYS: 30,
  
  // 文字起こしファイルの命名パターン（正規表現）
  TRANSCRIPT_PATTERN: /Gemini によるメモ|文字起こし|transcript|meeting.*transcript/i
};

// 注意: Slack設定はGASの「プロジェクトの設定」→「スクリプト プロパティ」で設定します
// - SLACK_BOT_TOKEN: Slack Bot Token（必須）
// - SLACK_CHANNEL: 投稿先チャンネル（例: #議事録、省略可・デフォルト: #議事録）

// 参加者名のマッピング（Google SheetsまたはGASプロパティで管理可能）
// 現在は直接定義していますが、後でGoogle Sheetsから読み込むように変更可能
const PARTICIPANT_MAPPING = {
  'Co., Ltd OKAMOTO BROTHERS': '山形',
  'Creative Team ziek': '銅金',
  'R O': '竜',
  'Rico Yamazaki': 'リコ',
  'Tatsuya Okamoto': '龍允',
  'TAT': '龍允',
  'johnny leatherreport': 'ジョニー'
};

// ==================== メイン処理 ====================

/**
 * メイン関数：文字起こしファイルを取得して処理
 * トリガーから呼び出される想定
 */
function getMeetingTranscripts() {
  try {
    Logger.log('=== 議事録自動生成処理開始 ===');
    
    // 検索範囲の日付を計算
    const today = new Date();
    const searchDate = new Date(today.getTime() - (CONFIG.SEARCH_DAYS * 24 * 60 * 60 * 1000));
    
    // 文字起こしファイルを検索
    const transcriptFiles = findTranscriptFiles(searchDate);
    
    if (transcriptFiles.length === 0) {
      Logger.log('処理対象の文字起こしファイルが見つかりませんでした');
      return;
    }
    
    Logger.log(`${transcriptFiles.length}件の文字起こしファイルが見つかりました`);
    
    // 各ファイルを処理
    for (let i = 0; i < transcriptFiles.length; i++) {
      const file = transcriptFiles[i];
      try {
        processTranscriptFile(file);
      } catch (error) {
        Logger.log(`エラー: ファイル ${file.getName()} の処理に失敗しました`);
        Logger.log(error.toString());
        Logger.log(error.stack);
        // エラーが発生しても次のファイルの処理を続行
      }
    }
    
    Logger.log('=== 議事録自動生成処理完了 ===');
    
  } catch (error) {
    Logger.log('致命的なエラーが発生しました');
    Logger.log(error.toString());
    Logger.log(error.stack);
    sendErrorNotification(error);
  }
}

/**
 * 文字起こしファイルを検索
 * @param {Date} searchDate - 検索開始日
 * @return {File[]} 見つかったファイルの配列
 */
function findTranscriptFiles(searchDate) {
  const files = [];
  
  try {
    const folder = DriveApp.getFolderById(CONFIG.TRANSCRIPT_FOLDER_ID);
    const searchQuery = `modifiedDate > "${searchDate.toISOString()}" and trashed=false`;
    const fileIterator = folder.searchFiles(searchQuery);
    
    while (fileIterator.hasNext()) {
      const file = fileIterator.next();
      const fileName = file.getName();
      
      // ファイル名が文字起こしパターンに一致するか確認
      if (CONFIG.TRANSCRIPT_PATTERN.test(fileName)) {
        // 処理済みでないか確認
        if (!isProcessed(file)) {
          files.push(file);
        }
      }
    }
    
  } catch (error) {
    Logger.log('ファイル検索中にエラーが発生しました');
    Logger.log(error.toString());
  }
  
  return files;
}

/**
 * ファイルが処理済みかどうかを確認
 * @param {File} file - 確認するファイル
 * @return {boolean} 処理済みの場合true
 */
function isProcessed(file) {
  const description = file.getDescription();
  if (description && description.includes('PROCESSED')) {
    return true;
  }
  return false;
}

/**
 * 文字起こしファイルを処理
 * @param {File} file - 処理するファイル
 */
function processTranscriptFile(file) {
  Logger.log(`処理開始: ${file.getName()}`);
  
  let isMarkedAsProcessed = false;
  
  try {
    // ファイルのMIMEタイプを確認
    const mimeType = file.getMimeType();
    Logger.log(`ファイルタイプ: ${mimeType}`);
    
    // ファイルの内容を取得
    const content = extractFileContent(file, mimeType);
    
    if (!content || content.trim().length === 0) {
      Logger.log('警告: ファイルの内容が空です。スキップします。');
      return;
    }
    
    Logger.log(`ファイルサイズ: ${content.length} 文字`);
    
    // ファイルを処理済みとしてマーク
    markAsProcessed(file);
    isMarkedAsProcessed = true;
    
    // テキスト処理
    Logger.log('テキスト処理を開始します...');
    const processedText = processText(content);
    Logger.log(`テキスト処理が完了しました (サイズ: ${processedText.length} 文字)`);
    
    // 議事録Documentを作成
    Logger.log('議事録Documentを作成します...');
    const docTitle = `議事録_${Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyyMMdd_HHmmss')}`;
    const newDoc = DocumentApp.create(docTitle);
    const docId = newDoc.getId();
    const docBody = newDoc.getBody();
    
    // テキストを挿入
    Logger.log('テキストをドキュメントに挿入します...');
    docBody.setText(processedText);
    
    // フォルダに移動
    Logger.log(`議事録ファイルをフォルダに移動します (Document ID: ${docId})`);
    moveDocumentToFolder(docId, CONFIG.PROCESSED_FOLDER_ID);
    
    const docUrl = `https://docs.google.com/document/d/${docId}`;
    Logger.log(`議事録の作成が完了しました: ${docUrl}`);
    
    // Slackに投稿
    Logger.log('Slackに投稿します...');
    postToSlack(file.getName(), docUrl);
    
    Logger.log(`処理完了: ${file.getName()}`);
    
  } catch (error) {
    Logger.log(`ファイル処理中にエラーが発生しました: ${file.getName()}`);
    Logger.log(error.toString());
    Logger.log(error.stack);
    
    // 処理済みマークをロールバック
    if (isMarkedAsProcessed) {
      Logger.log('エラー発生のため、処理済みマークをロールバックします');
      try {
        rollbackProcessedMark(file);
      } catch (rollbackError) {
        Logger.log('ロールバック中にエラーが発生しました');
        Logger.log(rollbackError.toString());
      }
    }
    
    throw error;
  }
}

/**
 * Drive API v3を使用してGoogle Documentをテキスト形式でエクスポート
 * @param {string} fileId - ファイルID
 * @return {string} エクスポートされたテキスト
 */
function exportDocumentAsText(fileId) {
  try {
    // Drive API v3のexport endpointを使用
    const url = `https://www.googleapis.com/drive/v3/files/${fileId}/export?mimeType=text/plain`;
    
    // OAuth2トークンを取得（DriveAppサービスが有効な場合、自動的に認証される）
    const token = ScriptApp.getOAuthToken();
    
    const options = {
      method: 'get',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();
    
    if (responseCode === 200) {
      const content = response.getContentText('UTF-8');
      return content;
    } else {
      const errorText = response.getContentText();
      throw new Error(`Drive API export failed: HTTP ${responseCode} - ${errorText}`);
    }
    
  } catch (error) {
    Logger.log(`Drive API v3でのエクスポート中にエラーが発生しました: ${error.toString()}`);
    throw error;
  }
}

/**
 * ファイルタイプに応じてファイルの内容を抽出
 * @param {File} file - ファイルオブジェクト
 * @param {string} mimeType - MIMEタイプ
 * @return {string} ファイルの内容（テキスト）
 */
function extractFileContent(file, mimeType) {
  // Google Documentの場合
  if (mimeType === 'application/vnd.google-apps.document') {
    Logger.log('Google Documentとして処理します');
    const fileId = file.getId();
    
    try {
      // 方法1: DocumentAppを試行
      try {
        const doc = DocumentApp.openById(fileId);
        const body = doc.getBody();
        const text = body.getText();
        Logger.log('Google Documentからテキストを取得しました（DocumentApp使用）');
        return text;
      } catch (docError) {
        Logger.log(`DocumentAppでの読み込みに失敗しました: ${docError.toString()}`);
        Logger.log('Drive API v3を使用してエクスポートします...');
        
        // 方法2: Drive API v3のexportメソッドを使用（フォールバック）
        try {
          const content = exportDocumentAsText(fileId);
          Logger.log('Google Documentからテキストを取得しました（Drive API v3使用）');
          return content;
        } catch (exportError) {
          Logger.log(`Drive API v3でのエクスポートに失敗しました: ${exportError.toString()}`);
          throw exportError;
        }
      }
    } catch (error) {
      Logger.log(`Google Documentの読み込みに失敗しました: ${error.toString()}`);
      Logger.log(`ファイルID: ${fileId}`);
      Logger.log('以下の点を確認してください:');
      Logger.log('1. GASを実行しているアカウントがファイルにアクセス権限を持っているか');
      Logger.log('2. ファイルが存在するか');
      Logger.log('3. GASプロジェクトにDrive APIのアクセス権限があるか');
      Logger.log('   権限を再承認する場合は、関数を実行して「権限を確認」をクリックしてください');
      throw new Error(`Google Documentの読み込みに失敗しました: ${error.toString()}`);
    }
  }
  
  // テキストファイルの場合
  if (mimeType.startsWith('text/')) {
    Logger.log('テキストファイルとして処理します');
    try {
      const blob = file.getBlob();
      const content = blob.getDataAsString('UTF-8');
      Logger.log('テキストファイルから内容を取得しました');
      return content;
    } catch (error) {
      Logger.log(`テキストファイルの読み込みに失敗しました: ${error.toString()}`);
      throw error;
    }
  }
  
  // その他のファイルタイプ
  Logger.log(`警告: サポートされていないファイルタイプです (${mimeType})`);
  throw new Error(`サポートされていないファイルタイプです: ${mimeType}`);
}

/**
 * ファイルを処理済みとしてマーク
 * @param {File} file - マークするファイル
 */
function markAsProcessed(file) {
  try {
    const currentDescription = file.getDescription() || '';
    const processedMark = '\nPROCESSED: ' + new Date().toISOString();
    file.setDescription(currentDescription + processedMark);
    Logger.log(`ファイルを処理済みとしてマークしました: ${file.getName()}`);
  } catch (error) {
    Logger.log('処理済みマーク中にエラーが発生しました');
    Logger.log(error.toString());
    throw error;
  }
}

/**
 * 処理済みマークをロールバック（エラー時に使用）
 * @param {File} file - ロールバックするファイル
 */
function rollbackProcessedMark(file) {
  try {
    const currentDescription = file.getDescription() || '';
    const lines = currentDescription.split('\n');
    const filteredLines = lines.filter(line => !line.trim().startsWith('PROCESSED:'));
    const newDescription = filteredLines.join('\n').trim();
    file.setDescription(newDescription);
    Logger.log(`処理済みマークをロールバックしました: ${file.getName()}`);
  } catch (error) {
    Logger.log('ロールバック中にエラーが発生しました');
    Logger.log(error.toString());
  }
}

/**
 * 議事録ファイル（Google Document）を指定フォルダに移動
 * @param {string} documentId - Google DocumentのID
 * @param {string} folderId - 移動先フォルダのID
 */
function moveDocumentToFolder(documentId, folderId) {
  try {
    Logger.log(`議事録ファイルをフォルダに移動します (Document ID: ${documentId}, Folder ID: ${folderId})`);
    
    const folder = DriveApp.getFolderById(folderId);
    const file = DriveApp.getFileById(documentId);
    
    // 現在の親フォルダを取得して削除
    const parents = file.getParents();
    while (parents.hasNext()) {
      parents.next().removeFile(file);
    }
    
    // 新しいフォルダに追加
    folder.addFile(file);
    
    Logger.log(`議事録ファイルをフォルダに移動しました`);
    
  } catch (error) {
    Logger.log(`議事録ファイルの移動中にエラーが発生しました: ${error.toString()}`);
    Logger.log('議事録ファイルは作成されていますが、フォルダへの移動に失敗しました');
  }
}

// ==================== テキスト処理 ====================

/**
 * テキストを処理（参加者名のみ修正、フォーマットは元のまま）
 * @param {string} text - 元のテキスト
 * @return {string} 処理後のテキスト（参加者名のみ修正済み）
 */
function processText(text) {
  Logger.log('テキスト処理を開始します（参加者名のみ修正）');
  
  // 参加者名の修正のみ（フォーマットと内容は元のまま）
  text = fixParticipantNames(text);
  
  Logger.log('テキスト処理が完了しました（参加者名のみ修正）');
  return text;
}

/**
 * 参加者名を修正
 * @param {string} text - 元のテキスト
 * @return {string} 修正後のテキスト
 */
function fixParticipantNames(text) {
  Logger.log('参加者名の修正を開始します');
  
  // テキスト全体で参加者名を置換
  // マッピングのキーを長い順にソート（部分一致を防ぐため）
  const sortedKeys = Object.keys(PARTICIPANT_MAPPING).sort((a, b) => b.length - a.length);
  
  for (let i = 0; i < sortedKeys.length; i++) {
    const originalName = sortedKeys[i];
    const mappedName = PARTICIPANT_MAPPING[originalName];
    
    // テキスト全体で名前を置換
    // 単語境界を考慮して置換（部分一致を防ぐ）
    const regex = new RegExp(escapeRegex(originalName), 'g');
    const beforeReplace = text;
    text = text.replace(regex, mappedName);
    
    if (beforeReplace !== text) {
      Logger.log(`参加者名を置換: "${originalName}" -> "${mappedName}"`);
    }
  }
  
  Logger.log('参加者名の修正が完了しました');
  return text;
}

/**
 * 正規表現の特殊文字をエスケープ
 * @param {string} str - エスケープする文字列
 * @return {string} エスケープ後の文字列
 */
function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * 参加者名をマッピング
 * @param {string} name - 元の名前
 * @return {string} マッピング後の名前
 */
function mapParticipantName(name) {
  const trimmedName = name.trim();
  
  // 正確なマッチングを試行
  if (PARTICIPANT_MAPPING[trimmedName]) {
    Logger.log(`名前をマッピング: ${trimmedName} -> ${PARTICIPANT_MAPPING[trimmedName]}`);
    return PARTICIPANT_MAPPING[trimmedName];
  }
  
  // 大文字小文字を無視してマッチング
  for (const key in PARTICIPANT_MAPPING) {
    if (key.toLowerCase() === trimmedName.toLowerCase()) {
      Logger.log(`名前をマッピング（大文字小文字無視）: "${trimmedName}" -> "${PARTICIPANT_MAPPING[key]}"`);
      return PARTICIPANT_MAPPING[key];
    }
  }
  
  // 部分マッチングも試行（スペースの違いなどに対応）
  for (const key in PARTICIPANT_MAPPING) {
    const normalizedKey = key.replace(/\s+/g, ' ').trim();
    const normalizedName = trimmedName.replace(/\s+/g, ' ').trim();
    
    if (normalizedName === normalizedKey || 
        normalizedName.includes(normalizedKey) || 
        normalizedKey.includes(normalizedName)) {
      Logger.log(`名前をマッピング（部分一致）: "${trimmedName}" -> "${PARTICIPANT_MAPPING[key]}"`);
      return PARTICIPANT_MAPPING[key];
    }
  }
  
  return trimmedName;
}

/**
 * セクション名を変更
 * @param {string} text - 元のテキスト
 * @return {string} 変更後のテキスト
 */
function replaceSectionNames(text) {
  // 「推奨される次のステップ」→「次にやること」に変更
  text = text.replace(/推奨される次のステップ/g, '次にやること');
  Logger.log('セクション名を変更しました: 推奨される次のステップ → 次にやること');
  return text;
}

/**
 * まとめセクションのフォーマット（まとまりごとに改行）
 * @param {string} text - 元のテキスト
 * @return {string} フォーマット後のテキスト
 */
function formatSummarySection(text) {
  const lines = text.split('\n');
  const processedLines = [];
  let inSummarySection = false;
  let summaryLines = [];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    // まとめセクションの開始を検出
    if (line.includes('まとめ') || line.includes('要約')) {
      inSummarySection = true;
      processedLines.push(line);
      continue;
    }
    
    // まとめセクションが終了する条件（次のセクション開始）
    if (inSummarySection) {
      if (line.includes('推奨') || line.includes('次に') || line.includes('アクション') || 
          line.includes('次回') || line.trim() === '' && i + 1 < lines.length && 
          (lines[i + 1].includes('推奨') || lines[i + 1].includes('次に') || lines[i + 1].includes('アクション'))) {
        // まとめセクションの終了
        // まとめ内容をフォーマット
        if (summaryLines.length > 0) {
          const formattedSummary = formatSummaryContent(summaryLines.join('\n'));
          processedLines.push(formattedSummary);
          summaryLines = [];
        }
        inSummarySection = false;
        processedLines.push(line);
        continue;
      }
      
      // まとめセクションの内容を収集
      summaryLines.push(line);
    } else {
      processedLines.push(line);
    }
  }
  
  // 最後までまとめセクションだった場合
  if (inSummarySection && summaryLines.length > 0) {
    const formattedSummary = formatSummaryContent(summaryLines.join('\n'));
    processedLines.push(formattedSummary);
  }
  
  return processedLines.join('\n');
}

/**
 * まとめ内容をフォーマット（まとまりごとに改行）
 * @param {string} summaryText - まとめテキスト
 * @return {string} フォーマット後のテキスト
 */
function formatSummaryContent(summaryText) {
  if (!summaryText || summaryText.trim().length === 0) {
    return summaryText;
  }
  
  // 文末記号（。、.、！、？）で区切って、まとまりごとに改行
  const sentences = summaryText.split(/([。.！!？?])/);
  const formatted = [];
  let currentSentence = '';
  
  for (let i = 0; i < sentences.length; i++) {
    currentSentence += sentences[i];
    
    // 文末記号の後に改行を追加
    if (sentences[i] === '。' || sentences[i] === '.' || 
        sentences[i] === '！' || sentences[i] === '!' ||
        sentences[i] === '？' || sentences[i] === '?') {
      const trimmed = currentSentence.trim();
      if (trimmed && trimmed.length > 0) {
        formatted.push(trimmed);
        formatted.push(''); // 空行を追加（まとまりごとに改行）
      }
      currentSentence = '';
    }
  }
  
  // 残りのテキストを追加
  if (currentSentence.trim()) {
    formatted.push(currentSentence.trim());
  }
  
  return formatted.join('\n');
}

/**
 * 文字起こしスクリプトを削除
 * @param {string} text - 元のテキスト
 * @return {string} 削除後のテキスト
 */
function removeTranscriptScript(text) {
  const lines = text.split('\n');
  const processedLines = [];
  let inTranscriptSection = false;
  let transcriptStartKeywords = ['文字起こし', 'transcript', '発言内容', '会話', '発言'];
  let transcriptEndKeywords = ['まとめ', '要約', '推奨', '次に', 'やること', 'アクション', '次回'];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    // 文字起こしセクションの開始を検出
    if (inTranscriptSection === false) {
      for (let j = 0; j < transcriptStartKeywords.length; j++) {
        if (line.includes(transcriptStartKeywords[j])) {
          inTranscriptSection = true;
          // セクションタイトル行自体は残すかどうか...
          // 削除する場合はここでcontinue
          continue;
        }
      }
    }
    
    // 文字起こしセクション内かどうか
    if (inTranscriptSection) {
      // 文字起こしセクションの終了を検出
      for (let j = 0; j < transcriptEndKeywords.length; j++) {
        if (line.includes(transcriptEndKeywords[j])) {
          inTranscriptSection = false;
          processedLines.push(line);
          continue;
        }
      }
      
      // 文字起こしセクションの内容はスキップ
      continue;
    }
    
    // 通常の行は追加
    processedLines.push(line);
  }
  
  // 連続する空行を1つに
  const cleanedLines = [];
  for (let i = 0; i < processedLines.length; i++) {
    if (processedLines[i].trim() === '' && cleanedLines.length > 0 && cleanedLines[cleanedLines.length - 1].trim() === '') {
      continue; // 連続する空行はスキップ
    }
    cleanedLines.push(processedLines[i]);
  }
  
  Logger.log('文字起こしスクリプトを削除しました');
  return cleanedLines.join('\n');
}

/**
 * テキストをフォーマット（議事録形式）
 * @param {string} text - 元のテキスト
 * @return {string} フォーマットされたテキスト
 */
function formatText(text) {
  const lines = text.split('\n');
  
  // ヘッダー情報の抽出
  const headerInfo = extractHeaderInfo(lines);
  
  // アクション項目の抽出
  const actionItems = extractActionItems(lines);
  
  // 本文（話し合ったことの要点）の抽出
  const mainContent = extractMainContent(lines);
  
  // フォーマットに従って整形
  const formattedLines = [];
  
  formattedLines.push('='.repeat(50));
  formattedLines.push('議事録');
  formattedLines.push('='.repeat(50));
  formattedLines.push('');
  
  if (headerInfo.date) {
    formattedLines.push(`日時: ${headerInfo.date}`);
  }
  if (headerInfo.title) {
    formattedLines.push(`件名: ${headerInfo.title}`);
  }
  if (headerInfo.participants && headerInfo.participants.length > 0) {
    formattedLines.push(`参加者: ${headerInfo.participants.join(', ')}`);
  }
  
  formattedLines.push('');
  formattedLines.push('-'.repeat(50));
  formattedLines.push('');
  
  // [話し合ったことの要点]セクション
  formattedLines.push('[話し合ったことの要点]');
  formattedLines.push('');
  formattedLines.push(...mainContent);
  formattedLines.push('');
  formattedLines.push('-'.repeat(50));
  formattedLines.push('');
  
  // [各々が次取るべきアクション]セクション
  formattedLines.push('[各々が次取るべきアクション]');
  formattedLines.push('');
  
  if (actionItems && actionItems.length > 0) {
    for (let i = 0; i < actionItems.length; i++) {
      const action = actionItems[i];
      let actionText = action.name;
      if (action.action) {
        actionText += `: ${action.action}`;
      }
      if (action.deadline) {
        actionText += ` （${action.deadline}までに）`;
      }
      formattedLines.push(`□ ${actionText}`);
    }
  } else {
    formattedLines.push('（アクション項目は自動抽出できませんでした。手動で追加してください）');
  }
  
  formattedLines.push('');
  formattedLines.push('='.repeat(50));
  
  return formattedLines.join('\n');
}

/**
 * ヘッダー情報を抽出
 * @param {Array<string>} lines - テキストの行配列
 * @return {Object} ヘッダー情報
 */
function extractHeaderInfo(lines) {
  const info = {
    date: null,
    title: null,
    participants: []
  };
  
  const datePattern = /(\d{4}年\d{1,2}月\d{1,2}日|\d{4}\/\d{1,2}\/\d{1,2}|\d{4}-\d{1,2}-\d{1,2})/;
  const titlePatterns = [
    /会議[:：]\s*(.+)/,
    /件名[:：]\s*(.+)/,
    /タイトル[:：]\s*(.+)/
  ];
  
  for (let i = 0; i < Math.min(10, lines.length); i++) {
    const line = lines[i].trim();
    
    // 日付の検出
    if (!info.date) {
      const dateMatch = line.match(datePattern);
      if (dateMatch) {
        info.date = dateMatch[1];
      }
    }
    
    // タイトルの検出
    if (!info.title) {
      for (let j = 0; j < titlePatterns.length; j++) {
        const titleMatch = line.match(titlePatterns[j]);
        if (titleMatch) {
          info.title = titleMatch[1].trim();
          break;
        }
      }
    }
  }
  
  return info;
}

/**
 * 本文（話し合ったことの要点）を抽出
 * @param {Array<string>} lines - テキストの行配列
 * @return {Array<string>} 本文の行配列
 */
function extractMainContent(lines) {
  const contentLines = [];
  let inBody = false;
  
  const actionKeywords = ['アクション', 'todo', 'to do', 'やること', '次回', '課題'];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // ヘッダー部分をスキップ
    if (!inBody) {
      if (isHeaderLine(line)) {
        continue;
      }
      if (line && !isHeaderLine(line)) {
        inBody = true;
      }
    }
    
    if (inBody) {
      // アクション項目のキーワードが含まれている場合は本文終了
      const hasActionKeyword = actionKeywords.some(keyword => 
        line.toLowerCase().includes(keyword.toLowerCase())
      );
      
      if (hasActionKeyword) {
        break;
      }
      
      if (line) {
        contentLines.push(line);
      }
    }
  }
  
  return contentLines.length > 0 ? contentLines : ['（内容を手動で追加してください）'];
}

/**
 * ヘッダー行かどうかを判定
 * @param {string} line - 行
 * @return {boolean} ヘッダー行の場合true
 */
function isHeaderLine(line) {
  const headerPatterns = [
    /^\d{4}年\d{1,2}月\d{1,2}日/,
    /会議[:：]/,
    /件名[:：]/,
    /タイトル[:：]/
  ];
  
  for (let i = 0; i < headerPatterns.length; i++) {
    if (headerPatterns[i].test(line)) {
      return true;
    }
  }
  
  return false;
}

/**
 * アクション項目を抽出
 * @param {Array<string>} lines - テキストの行配列
 * @return {Array<Object>} アクション項目の配列
 */
function extractActionItems(lines) {
  const actionItems = [];
  const actionKeywords = ['アクション', 'todo', 'to do', 'やること', '次回', '課題', 'タスク'];
  
  let inActionSection = false;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // アクションセクションの開始を検出
    const hasActionKeyword = actionKeywords.some(keyword => 
      line.toLowerCase().includes(keyword.toLowerCase())
    );
    
    if (hasActionKeyword) {
      inActionSection = true;
      continue;
    }
    
    if (inActionSection || line.includes(':') || line.includes('：')) {
      // アクション項目のパターン（例: "名前: アクション内容 (期日までに)"）
      const pattern = /^([^:：]+)[:：]\s*(.+?)(?:（(.+?)までに）|\((.+?)までに\))?$/;
      const match = line.match(pattern);
      
      if (match) {
        const name = match[1].trim();
        const actionText = match[2] || '';
        const deadline = match[3] || match[4] || null;
        
        const mappedName = mapParticipantName(name);
        
        actionItems.push({
          name: mappedName,
          action: actionText || null,
          deadline: deadline ? deadline.trim() : null
        });
      }
    }
  }
  
  return actionItems;
}

/**
 * 不要な部分を削除
 * @param {string} text - 元のテキスト
 * @return {string} クリーンアップされたテキスト
 */
function cleanText(text) {
  const lines = text.split('\n');
  const cleanedLines = [];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 空行の連続を1つに
    if (!line) {
      if (cleanedLines.length > 0 && cleanedLines[cleanedLines.length - 1]) {
        cleanedLines.push('');
      }
      continue;
    }
    
    // 特定のパターンを削除
    const skipPatterns = [
      /^\[.*?\]$/,  // [音声認識] などのメタ情報
      /^\(.*?\)$/   // (笑) などの補足
    ];
    
    let shouldSkip = false;
    for (let j = 0; j < skipPatterns.length; j++) {
      if (skipPatterns[j].test(line)) {
        shouldSkip = true;
        break;
      }
    }
    
    if (!shouldSkip) {
      cleanedLines.push(line);
    }
  }
  
  return cleanedLines.join('\n');
}

// ==================== Slack投稿 ====================

/**
 * Slackに投稿
 * @param {string} fileName - ファイル名
 * @param {string} docUrl - 議事録のURL
 */
function postToSlack(fileName, docUrl) {
  try {
    const botToken = PropertiesService.getScriptProperties().getProperty('SLACK_BOT_TOKEN');
    const channel = PropertiesService.getScriptProperties().getProperty('SLACK_CHANNEL') || '#議事録';
    
    if (!botToken) {
      Logger.log('警告: SLACK_BOT_TOKENが設定されていません。Slackへの投稿をスキップします。');
      return;
    }
    
    const dateStr = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy年MM月dd日');
    
    const message = {
      channel: channel,
      text: '📝 議事録が生成されました',
      blocks: [
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: `*📝 議事録が生成されました*\n\n` +
                  `*ファイル名:* ${fileName}\n` +
                  `*日付:* ${dateStr}\n` +
                  `*Document:* <${docUrl}|議事録を開く>`
          }
        }
      ]
    };
    
    const url = 'https://slack.com/api/chat.postMessage';
    const options = {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'Authorization': `Bearer ${botToken}`
      },
      payload: JSON.stringify(message),
      muteHttpExceptions: true
    };
    
    Logger.log(`Slackに投稿します: ${channel}`);
    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    if (responseCode === 200) {
      const result = JSON.parse(responseText);
      if (result.ok) {
        Logger.log('Slackにメッセージを投稿しました');
      } else {
        Logger.log(`Slack投稿に失敗しました: ${result.error}`);
      }
    } else {
      Logger.log(`Slack投稿に失敗しました (HTTP ${responseCode})`);
      Logger.log(`レスポンス: ${responseText}`);
    }
    
  } catch (error) {
    Logger.log(`Slack投稿中にエラーが発生しました: ${error.toString()}`);
    // エラーが発生しても処理は続行
  }
}

// ==================== エラー通知 ====================

/**
 * エラー通知を送信
 * @param {Error} error - エラーオブジェクト
 */
function sendErrorNotification(error) {
  // Slack通知やメール通知を実装（必要に応じて）
  Logger.log('エラー通知を送信しました');
  Logger.log(`エラー: ${error.toString()}`);
}

// ==================== テスト・デバッグ ====================

/**
 * テスト用関数：手動実行用
 */
function testGetMeetingTranscripts() {
  Logger.log('=== テスト実行開始 ===');
  getMeetingTranscripts();
  Logger.log('=== テスト実行完了 ===');
}

/**
 * デバッグ用関数：フォルダ内のファイルを全て表示
 */
function debugListFiles() {
  try {
    Logger.log('=== デバッグ: フォルダ内のファイル一覧 ===');
    
    const folder = DriveApp.getFolderById(CONFIG.TRANSCRIPT_FOLDER_ID);
    Logger.log(`フォルダID: ${CONFIG.TRANSCRIPT_FOLDER_ID}`);
    Logger.log(`フォルダ名: ${folder.getName()}`);
    
    const today = new Date();
    const searchDate = new Date(today.getTime() - (CONFIG.SEARCH_DAYS * 24 * 60 * 60 * 1000));
    Logger.log(`検索日付範囲: ${searchDate.toISOString()} 以降`);
    
    const searchQuery = `modifiedDate > "${searchDate.toISOString()}" and trashed=false`;
    const fileIterator = folder.searchFiles(searchQuery);
    
    Logger.log('--- 検索されたファイル一覧 ---');
    let fileCount = 0;
    let matchedCount = 0;
    let processedCount = 0;
    
    while (fileIterator.hasNext()) {
      const file = fileIterator.next();
      fileCount++;
      const fileName = file.getName();
      
      Logger.log(`\n[${fileCount}] ファイル名: ${fileName}`);
      
      const matchesPattern = CONFIG.TRANSCRIPT_PATTERN.test(fileName);
      Logger.log(`  パターン一致: ${matchesPattern}`);
      
      if (matchesPattern) {
        matchedCount++;
        const isProcessedFile = isProcessed(file);
        Logger.log(`  処理済み: ${isProcessedFile}`);
        
        if (isProcessedFile) {
          processedCount++;
        } else {
          Logger.log(`  ✅ 処理対象として認識されました`);
        }
      }
    }
    
    Logger.log('\n--- サマリー ---');
    Logger.log(`検索されたファイル数: ${fileCount}`);
    Logger.log(`パターンに一致したファイル数: ${matchedCount}`);
    Logger.log(`処理済みファイル数: ${processedCount}`);
    Logger.log(`処理対象ファイル数: ${matchedCount - processedCount}`);
    
    Logger.log('=== デバッグ完了 ===');
    
  } catch (error) {
    Logger.log('デバッグ中にエラーが発生しました');
    Logger.log(error.toString());
    Logger.log(error.stack);
  }
}

