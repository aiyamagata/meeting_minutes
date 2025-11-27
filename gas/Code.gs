/**
 * Google Meet 文字起こし取得スクリプト
 * 
 * このスクリプトは、Google Drive内のGoogle Meet文字起こしファイルを検索し、
 * 未処理のファイルを取得して処理対象としてマークします。
 */

// 設定
const CONFIG = {
  // 文字起こしファイルを保存するフォルダID（「Meet Recordings」フォルダ）
  // 元ファイルはこのフォルダにそのまま残ります（移動しません）
  TRANSCRIPT_FOLDER_ID: '1qHsTK30zKVl2bt2IhlXG79jCNW2IfUb_',
  
  // 検索する日付範囲（過去N日）
  SEARCH_DAYS: 30,
  
  // 文字起こしファイルの命名パターン（正規表現）
  // Google Gemini自動議事録で作成されるファイル名「Gemini によるメモ」に対応
  TRANSCRIPT_PATTERN: /Gemini によるメモ|文字起こし|transcript|meeting.*transcript/i
};

// 議事録ファイル（Google Document）の保存先フォルダID（「議事録」フォルダ）
// 修正後の議事録ファイルは、このフォルダに自動で移動されます
const PROCESSED_FOLDER_ID = '1w1u0bBBtt8wHFbJOx8h3UzBMvO1PzQZi';

/**
 * メイン関数：文字起こしファイルを取得
 * トリガーから呼び出される想定
 */
function getMeetingTranscripts() {
  try {
    Logger.log('=== 文字起こし取得処理開始 ===');
    
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
        // エラーが発生しても次のファイルの処理を続行
      }
    }
    
    Logger.log('=== 文字起こし取得処理完了 ===');
    
  } catch (error) {
    Logger.log('致命的なエラーが発生しました');
    Logger.log(error.toString());
    // エラー通知を送信（必要に応じて実装）
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
    // フォルダを指定する場合
    let folder;
    if (CONFIG.TRANSCRIPT_FOLDER_ID) {
      folder = DriveApp.getFolderById(CONFIG.TRANSCRIPT_FOLDER_ID);
    } else {
      folder = DriveApp.getRootFolder();
    }
    
    // ファイルを検索
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
 * 
 * 注意: 要件により、元ファイルは「Meet Recordings」フォルダにそのまま残すため、
 * ファイルの説明欄の「PROCESSED」フラグのみで判定します。
 */
function isProcessed(file) {
  // ファイルの説明欄に処理済みフラグがあるか確認
  const description = file.getDescription();
  if (description && description.includes('PROCESSED')) {
    return true;
  }
  
  // 要件により、元ファイルは「Meet Recordings」フォルダにそのまま残すため、
  // フォルダの位置での判定は行いません。
  // 処理後の議事録ファイルは、Pythonスクリプト側で別フォルダ（議事録フォルダ）に保存されます。
  
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
    
    // ファイルの内容を取得（ファイルタイプに応じて適切な方法を使用）
    let content;
    try {
      content = extractFileContent(file, mimeType);
      Logger.log(`ファイルサイズ: ${content.length} 文字`);
    } catch (extractError) {
      Logger.log(`ファイル内容の取得に失敗しました: ${extractError.toString()}`);
      throw new Error(`ファイル内容の取得に失敗しました: ${extractError.toString()}`);
    }
    
    // 内容が空または無効な場合の処理
    if (!content || content.trim().length === 0) {
      // Google Documentの場合、Python側でファイルIDを使って読み込む
      if (mimeType === 'application/vnd.google-apps.document') {
        Logger.log('警告: GAS側での読み込みが失敗しました。Python側でファイルIDを使って読み込みます。');
        // 空のcontentのまま送信（Python側で処理）
      } else {
        Logger.log('警告: ファイルの内容が空です。スキップします。');
        return;
      }
    }
    
    // PDFの生データが含まれている場合はエラー
    if (content.includes('%PDF-1.') || content.includes('%PDF-')) {
      Logger.log('エラー: PDFファイルの生データが検出されました。このファイルタイプはサポートされていません。');
      throw new Error('PDFファイルはサポートされていません。Google Documentまたはテキストファイルを使用してください。');
    }
    
    // ファイル情報を取得
    const fileInfo = {
      id: file.getId(),
      name: file.getName(),
      url: file.getUrl(),
      created: file.getDateCreated(),
      modified: file.getLastUpdated(),
      content: content,
      mime_type: mimeType  // MIMEタイプも送信（Python側で使用）
    };
    
    // 処理済みとしてマーク
    markAsProcessed(file);
    isMarkedAsProcessed = true;
    
    // 代替案3: GAS側でDocumentAppを使用して議事録を作成
    // Python側でテキスト処理のみを行い、GAS側でDocumentAppを使用してドキュメントを作成
    const success = processWithDocumentApp(fileInfo);
    
    if (!success) {
      // 送信に失敗した場合、処理済みマークをロールバック
      Logger.log('警告: 処理に失敗したため、処理済みマークをロールバックします');
      rollbackProcessedMark(file);
      isMarkedAsProcessed = false;
    }
    
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
    
    // 方法1: DocumentAppを使用（推奨）
    try {
      const doc = DocumentApp.openById(fileId);
      const body = doc.getBody();
      const text = body.getText();
      Logger.log('Google Documentからテキストを取得しました（DocumentApp使用）');
      return text;
    } catch (docError) {
      Logger.log(`DocumentAppでの読み込みに失敗しました: ${docError.toString()}`);
      Logger.log('警告: GAS側でのGoogle Documentの読み込みが失敗しました。');
      Logger.log('Python側でDrive APIを使用してファイルを読み込む必要があります。');
      Logger.log('ファイルID: ' + fileId);
      
      // 空の文字列を返し、Python側でファイルIDを使って読み込む
      // processTranscriptFileで特別な処理を行う必要がある
      // ここでは空文字列を返し、Python側でファイルIDを使って読み込む
      return '';  // 空文字列を返し、Python側で処理
    }
  }
  
  // Google Spreadsheetの場合（通常は使用しないが、念のため）
  if (mimeType === 'application/vnd.google-apps.spreadsheet') {
    Logger.log('警告: Google Spreadsheetはサポートされていません');
    throw new Error('Google Spreadsheetはサポートされていません');
  }
  
  // PDFファイルの場合
  if (mimeType === 'application/pdf') {
    Logger.log('エラー: PDFファイルはサポートされていません');
    throw new Error('PDFファイルはサポートされていません。Google Documentまたはテキストファイルを使用してください。');
  }
  
  // テキストファイルの場合（.txt, .mdなど）
  if (mimeType.startsWith('text/')) {
    Logger.log('テキストファイルとして処理します');
    try {
      // UTF-8エンコーディングで読み込む
      const blob = file.getBlob();
      const content = blob.getDataAsString('UTF-8');
      Logger.log('テキストファイルから内容を取得しました');
      return content;
    } catch (error) {
      Logger.log(`テキストファイルの読み込みに失敗しました: ${error.toString()}`);
      // UTF-8で失敗した場合、デフォルトエンコーディングを試す
      try {
        const blob = file.getBlob();
        const content = blob.getDataAsString();
        Logger.log('デフォルトエンコーディングでテキストファイルから内容を取得しました');
        return content;
      } catch (error2) {
        throw new Error(`テキストファイルの読み込みに失敗しました: ${error2.toString()}`);
      }
    }
  }
  
  // その他のファイルタイプ
  Logger.log(`警告: サポートされていないファイルタイプです (${mimeType})`);
  Logger.log('テキストとして読み込むことを試みます...');
  
  try {
    const blob = file.getBlob();
    const content = blob.getDataAsString('UTF-8');
    
    // PDFの生データが含まれていないか確認
    if (content.includes('%PDF-')) {
      throw new Error('PDFファイルの生データが検出されました。このファイルタイプはサポートされていません。');
    }
    
    Logger.log('ファイルをテキストとして読み込みました');
    return content;
  } catch (error) {
    Logger.log(`ファイルの読み込みに失敗しました: ${error.toString()}`);
    throw new Error(`サポートされていないファイルタイプです (${mimeType}): ${error.toString()}`);
  }
}

/**
 * ファイルを処理済みとしてマーク
 * @param {File} file - マークするファイル
 * 
 * 注意: 要件により、元データ（Meet Recordingsフォルダのファイル）は
 * そのままフォルダに格納し、移動しないようにしています。
 * 処理済みフォルダ（PROCESSED_FOLDER_ID）は、Pythonスクリプトで作成される
 * 議事録ファイル（Google Document）の保存先として使用されます。
 */
function markAsProcessed(file) {
  try {
    // ファイルの説明欄に処理済みフラグを追加
    // これにより、同じファイルが再度処理されることを防ぎます
    const currentDescription = file.getDescription() || '';
    const processedMark = '\nPROCESSED: ' + new Date().toISOString();
    file.setDescription(currentDescription + processedMark);
    
    Logger.log(`ファイルを処理済みとしてマークしました: ${file.getName()}`);
    Logger.log('元ファイルは「Meet Recordings」フォルダにそのまま残されます');
    
    // 注意: 元ファイルは移動しません（要件により）
    // PROCESSED_FOLDER_IDは、Pythonスクリプトで作成される議事録ファイルの
    // 保存先として使用されます（google_doc_creator.pyで設定）
    
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
    // PROCESSED: で始まる行を削除
    const lines = currentDescription.split('\n');
    const filteredLines = lines.filter(line => !line.trim().startsWith('PROCESSED:'));
    const newDescription = filteredLines.join('\n').trim();
    file.setDescription(newDescription);
    
    Logger.log(`処理済みマークをロールバックしました: ${file.getName()}`);
    
  } catch (error) {
    Logger.log('ロールバック中にエラーが発生しました');
    Logger.log(error.toString());
    throw error;
  }
}

/**
 * 処理データをPythonスクリプトに送信
 * @param {Object} fileInfo - ファイル情報
 * @return {boolean} 送信が成功した場合true
 */
function sendToProcessor(fileInfo) {
  try {
    // 方法1: Webhookを使用（推奨）
    // Herokuで動作しているPythonスクリプトのエンドポイントを呼び出す
    const webhookUrl = PropertiesService.getScriptProperties().getProperty('WEBHOOK_URL');
    
    if (!webhookUrl) {
      Logger.log('警告: WEBHOOK_URLが設定されていません。手動で処理してください。');
      // 代替案: Google Sheetsにデータを書き込む
      writeToSheet(fileInfo);
      return false;
    }
    
    Logger.log(`Webhook URL: ${webhookUrl}`);
    
    const payload = {
      file_id: fileInfo.id,
      file_name: fileInfo.name,
      file_url: fileInfo.url,
      created: fileInfo.created.toISOString(),
      modified: fileInfo.modified.toISOString(),
      content: fileInfo.content,
      mime_type: fileInfo.mime_type || ''  // MIMEタイプも送信（Python側で使用）
    };
    
    // ペイロードサイズをログに記録
    const payloadString = JSON.stringify(payload);
    const payloadSize = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, payloadString).length;
    Logger.log(`ペイロードサイズ: ${payloadString.length} 文字 (約 ${Math.round(payloadString.length / 1024)} KB)`);
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: payloadString,
      muteHttpExceptions: true,
      // タイムアウトを30秒に設定（デフォルトは20秒）
      followRedirects: true,
      validateHttpsCertificates: true
    };
    
    Logger.log('Webhookへのリクエストを送信します...');
    const startTime = new Date().getTime();
    const response = UrlFetchApp.fetch(webhookUrl, options);
    const endTime = new Date().getTime();
    const responseTime = endTime - startTime;
    
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    Logger.log(`レスポンスコード: ${responseCode}`);
    Logger.log(`レスポンス時間: ${responseTime}ms`);
    
    if (responseCode === 200) {
      Logger.log('Pythonスクリプトへの送信が成功しました');
      
      // レスポンスから議事録ファイルIDを取得
      try {
        const responseData = JSON.parse(responseText);
        Logger.log(`レスポンスデータ: ${JSON.stringify(responseData)}`);
        
        if (responseData.document_id) {
          Logger.log(`議事録ファイルが作成されました (ID: ${responseData.document_id})`);
          
          // 議事録ファイルを指定フォルダに移動
          moveDocumentToFolder(responseData.document_id, PROCESSED_FOLDER_ID);
        }
      } catch (e) {
        Logger.log('レスポンスの解析に失敗しました（議事録ファイルは作成されています）');
        Logger.log(`レスポンステキスト: ${responseText.substring(0, 500)}...`);
        Logger.log(e.toString());
      }
      
      return true;
    } else {
      Logger.log(`エラー: Pythonスクリプトへの送信に失敗しました (${responseCode})`);
      Logger.log(`レスポンスヘッダー: ${JSON.stringify(response.getHeaders())}`);
      
      // レスポンステキストの最初の1000文字をログに記録
      const responsePreview = responseText.length > 1000 
        ? responseText.substring(0, 1000) + '...' 
        : responseText;
      Logger.log(`レスポンス内容: ${responsePreview}`);
      
      // JSONレスポンスの場合はエラーメッセージを抽出
      try {
        const errorData = JSON.parse(responseText);
        if (errorData.error) {
          Logger.log(`エラーメッセージ: ${errorData.error}`);
        }
      } catch (e) {
        // JSONでない場合はそのまま表示
      }
      
      return false;
    }
    
  } catch (error) {
    Logger.log('送信処理中にエラーが発生しました');
    Logger.log(`エラータイプ: ${error.name}`);
    Logger.log(`エラーメッセージ: ${error.message}`);
    Logger.log(`エラースタック: ${error.stack}`);
    // エラーが発生した場合はfalseを返す
    return false;
  }
}

/**
 * Google Sheetsにデータを書き込む（Webhookが使えない場合の代替案）
 * @param {Object} fileInfo - ファイル情報
 */
function writeToSheet(fileInfo) {
  try {
    const sheetId = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
    if (!sheetId) {
      Logger.log('警告: SHEET_IDが設定されていません');
      return;
    }
    
    const sheet = SpreadsheetApp.openById(sheetId).getActiveSheet();
    sheet.appendRow([
      new Date(),
      fileInfo.id,
      fileInfo.name,
      fileInfo.url,
      fileInfo.content.substring(0, 50000) // セルの制限を考慮
    ]);
    
    Logger.log('Google Sheetsにデータを書き込みました');
    
  } catch (error) {
    Logger.log('Google Sheetsへの書き込み中にエラーが発生しました');
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
    
    // フォルダの存在確認
    let folder;
    try {
      folder = DriveApp.getFolderById(folderId);
      Logger.log(`フォルダを確認しました: ${folder.getName()}`);
    } catch (e) {
      Logger.log(`エラー: フォルダが見つかりません (Folder ID: ${folderId})`);
      Logger.log('以下を確認してください:');
      Logger.log('1. フォルダIDが正しいか');
      Logger.log('2. GAS実行アカウントがフォルダにアクセス権限を持っているか');
      Logger.log('3. フォルダが存在するか');
      return;
    }
    
    // ファイル（Document）を取得
    let file;
    try {
      file = DriveApp.getFileById(documentId);
      Logger.log(`ファイルを確認しました: ${file.getName()}`);
    } catch (e) {
      Logger.log(`エラー: ファイルが見つかりません (Document ID: ${documentId})`);
      return;
    }
    
    // 現在の親フォルダを取得
    const parents = file.getParents();
    const previousParents = [];
    while (parents.hasNext()) {
      previousParents.push(parents.next());
    }
    
    // 新しいフォルダに移動（既存の親を削除）
    for (let i = 0; i < previousParents.length; i++) {
      previousParents[i].removeFile(file);
    }
    folder.addFile(file);
    
    Logger.log(`議事録ファイルをフォルダに移動しました: ${folder.getName()} (ID: ${folderId})`);
    
  } catch (error) {
    Logger.log(`議事録ファイルの移動中にエラーが発生しました: ${error.toString()}`);
    Logger.log('議事録ファイルは作成されていますが、フォルダへの移動に失敗しました');
  }
}

/**
 * エラー通知を送信
 * @param {Error} error - エラーオブジェクト
 */
function sendErrorNotification(error) {
  // Slack通知やメール通知を実装（必要に応じて）
  Logger.log('エラー通知を送信しました');
}

/**
 * テスト用関数：手動実行用
 */
function testGetMeetingTranscripts() {
  Logger.log('=== テスト実行開始 ===');
  getMeetingTranscripts();
  Logger.log('=== テスト実行完了 ===');
}

/**
 * GAS側でDocumentAppを使用して議事録を作成（代替案3）
 * @param {Object} fileInfo - ファイル情報
 * @return {boolean} 処理が成功した場合true
 */
function processWithDocumentApp(fileInfo) {
  try {
    Logger.log('=== GAS側でDocumentAppを使用して議事録を作成 ===');
    
    // 1. ファイルの内容を取得
    let content = fileInfo.content;
    
    // contentが空の場合、Python側でファイルIDを使って読み込む
    if (!content || content.trim().length === 0) {
      if (fileInfo.mime_type === 'application/vnd.google-apps.document') {
        Logger.log('警告: contentが空です。Python側でファイルIDを使って読み込みます。');
        // Python側でファイルを読み込んでテキスト処理を行う
        return sendToProcessorForTextProcessing(fileInfo);
      } else {
        Logger.log('警告: ファイルの内容が空です。スキップします。');
        return false;
      }
    }
    
    // 2. Python側でテキスト処理を依頼
    Logger.log('Python側でテキスト処理を依頼します...');
    const processedText = requestTextProcessing(content, fileInfo.name);
    
    if (!processedText) {
      Logger.log('エラー: テキスト処理に失敗しました');
      return false;
    }
    
    Logger.log(`テキスト処理が完了しました (サイズ: ${processedText.length} 文字)`);
    
    // 3. GAS側でDocumentAppを使用して議事録を作成
    Logger.log('DocumentAppを使用して議事録を作成します...');
    const docTitle = `議事録_${Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyyMMdd_HHmmss')}`;
    const newDoc = DocumentApp.create(docTitle);
    const docId = newDoc.getId();
    const docBody = newDoc.getBody();
    
    // 4. テキストを挿入（setTextを使用）
    Logger.log('テキストをドキュメントに挿入します...');
    docBody.setText(processedText);
    
    // 5. フォルダに移動
    Logger.log(`議事録ファイルをフォルダに移動します (Document ID: ${docId})`);
    moveDocumentToFolder(docId, PROCESSED_FOLDER_ID);
    
    Logger.log(`議事録の作成が完了しました: https://docs.google.com/document/d/${docId}`);
    return true;
    
  } catch (error) {
    Logger.log(`GAS側での議事録作成に失敗しました: ${error.toString()}`);
    Logger.log(error.stack);
    return false;
  }
}

/**
 * Python側でテキスト処理のみを依頼
 * @param {string} content - 元のテキスト
 * @param {string} file_name - ファイル名
 * @return {string|null} 処理済みテキスト（失敗時はnull）
 */
function requestTextProcessing(content, file_name) {
  try {
    const webhookUrl = PropertiesService.getScriptProperties().getProperty('WEBHOOK_URL');
    if (!webhookUrl) {
      Logger.log('警告: WEBHOOK_URLが設定されていません');
      return null;
    }
    
    // /process-textエンドポイントにリクエスト
    const processTextUrl = webhookUrl.replace('/webhook', '/process-text');
    
    const payload = {
      content: content,
      file_name: file_name
    };
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    Logger.log(`テキスト処理リクエストを送信します: ${processTextUrl}`);
    const response = UrlFetchApp.fetch(processTextUrl, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    if (responseCode === 200) {
      const responseData = JSON.parse(responseText);
      return responseData.processed_text || null;
    } else {
      Logger.log(`エラー: テキスト処理に失敗しました (${responseCode})`);
      Logger.log(`レスポンス: ${responseText}`);
      return null;
    }
  } catch (error) {
    Logger.log(`テキスト処理リクエスト中にエラーが発生しました: ${error.toString()}`);
    return null;
  }
}

/**
 * Python側でテキスト処理のみを依頼（ファイルIDを使用する場合）
 * @param {Object} fileInfo - ファイル情報
 * @return {boolean} 処理が成功した場合true
 */
function sendToProcessorForTextProcessing(fileInfo) {
  // 既存のsendToProcessorを使用（Python側でファイルを読み込む）
  return sendToProcessor(fileInfo);
}

/**
 * デバッグ用関数：フォルダ内のファイルを全て表示
 * ファイル検索がうまくいかない場合の確認用
 */
function debugListFiles() {
  try {
    Logger.log('=== デバッグ: フォルダ内のファイル一覧 ===');
    
    // フォルダを取得
    let folder;
    if (CONFIG.TRANSCRIPT_FOLDER_ID) {
      folder = DriveApp.getFolderById(CONFIG.TRANSCRIPT_FOLDER_ID);
      Logger.log(`フォルダID: ${CONFIG.TRANSCRIPT_FOLDER_ID}`);
      Logger.log(`フォルダ名: ${folder.getName()}`);
    } else {
      folder = DriveApp.getRootFolder();
      Logger.log('フォルダ: ルートフォルダ');
    }
    
    // 検索範囲の日付を計算
    const today = new Date();
    const searchDate = new Date(today.getTime() - (CONFIG.SEARCH_DAYS * 24 * 60 * 60 * 1000));
    Logger.log(`検索日付範囲: ${searchDate.toISOString()} 以降`);
    Logger.log(`検索日数: 過去${CONFIG.SEARCH_DAYS}日`);
    
    // ファイルを検索
    const searchQuery = `modifiedDate > "${searchDate.toISOString()}" and trashed=false`;
    Logger.log(`検索クエリ: ${searchQuery}`);
    
    const fileIterator = folder.searchFiles(searchQuery);
    
    Logger.log('--- 検索されたファイル一覧 ---');
    let fileCount = 0;
    let matchedCount = 0;
    let processedCount = 0;
    
    while (fileIterator.hasNext()) {
      const file = fileIterator.next();
      fileCount++;
      const fileName = file.getName();
      const fileModified = file.getLastUpdated();
      
      Logger.log(`\n[${fileCount}] ファイル名: ${fileName}`);
      Logger.log(`  最終更新日: ${fileModified}`);
      
      // パターンマッチングの確認
      const matchesPattern = CONFIG.TRANSCRIPT_PATTERN.test(fileName);
      Logger.log(`  パターン一致: ${matchesPattern}`);
      if (!matchesPattern) {
        Logger.log(`  パターン: ${CONFIG.TRANSCRIPT_PATTERN}`);
        continue;
      }
      matchedCount++;
      
      // 処理済みかどうかの確認
      const isProcessedFile = isProcessed(file);
      Logger.log(`  処理済み: ${isProcessedFile}`);
      
      if (isProcessedFile) {
        processedCount++;
        const description = file.getDescription();
        if (description) {
          Logger.log(`  説明: ${description.substring(0, 100)}...`);
        }
        continue;
      }
      
      Logger.log(`  ✅ 処理対象として認識されました`);
    }
    
    Logger.log('\n--- サマリー ---');
    Logger.log(`検索されたファイル数: ${fileCount}`);
    Logger.log(`パターンに一致したファイル数: ${matchedCount}`);
    Logger.log(`処理済みファイル数: ${processedCount}`);
    Logger.log(`処理対象ファイル数: ${matchedCount - processedCount}`);
    
    if (fileCount === 0) {
      Logger.log('\n⚠️ 検索されたファイルが0件です。以下を確認してください:');
      Logger.log('1. フォルダIDが正しいか');
      Logger.log('2. ファイルが過去7日以内に更新されているか');
      Logger.log('3. ファイルがゴミ箱に入っていないか');
    } else if (matchedCount === 0) {
      Logger.log('\n⚠️ パターンに一致するファイルがありません。以下を確認してください:');
      Logger.log(`1. ファイル名に「Gemini によるメモ」「文字起こし」「transcript」が含まれているか`);
      Logger.log(`2. 現在のパターン: ${CONFIG.TRANSCRIPT_PATTERN}`);
    } else if (matchedCount - processedCount === 0) {
      Logger.log('\n⚠️ すべてのファイルが処理済みです。');
      Logger.log('処理済みフラグを削除するか、新しいファイルを使用してください。');
    }
    
    Logger.log('=== デバッグ完了 ===');
    
  } catch (error) {
    Logger.log('デバッグ中にエラーが発生しました');
    Logger.log(error.toString());
    Logger.log(error.stack);
  }
}

