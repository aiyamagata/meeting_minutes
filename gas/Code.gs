/**
 * Google Meet 文字起こし取得スクリプト
 * 
 * このスクリプトは、Google Drive内のGoogle Meet文字起こしファイルを検索し、
 * 未処理のファイルを取得して処理対象としてマークします。
 */

// 設定
const CONFIG = {
  // 文字起こしファイルを保存するフォルダID（空の場合はルートフォルダ）
  TRANSCRIPT_FOLDER_ID: '',
  
  // 処理済みファイルを保存するフォルダID
  PROCESSED_FOLDER_ID: '',
  
  // 検索する日付範囲（過去N日）
  SEARCH_DAYS: 7,
  
  // 文字起こしファイルの命名パターン（正規表現）
  TRANSCRIPT_PATTERN: /文字起こし|transcript|meeting.*transcript/i
};

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
 */
function isProcessed(file) {
  // ファイルの説明欄に処理済みフラグがあるか確認
  const description = file.getDescription();
  if (description && description.includes('PROCESSED')) {
    return true;
  }
  
  // 処理済みフォルダに移動されているか確認
  if (CONFIG.PROCESSED_FOLDER_ID) {
    try {
      const processedFolder = DriveApp.getFolderById(CONFIG.PROCESSED_FOLDER_ID);
      const parents = file.getParents();
      while (parents.hasNext()) {
        const parent = parents.next();
        if (parent.getId() === processedFolder.getId()) {
          return true;
        }
      }
    } catch (error) {
      Logger.log('処理済みフォルダの確認中にエラーが発生しました');
    }
  }
  
  return false;
}

/**
 * 文字起こしファイルを処理
 * @param {File} file - 処理するファイル
 */
function processTranscriptFile(file) {
  Logger.log(`処理開始: ${file.getName()}`);
  
  try {
    // ファイルの内容を取得
    const content = file.getBlob().getDataAsString();
    
    // ファイル情報を取得
    const fileInfo = {
      id: file.getId(),
      name: file.getName(),
      url: file.getUrl(),
      created: file.getDateCreated(),
      modified: file.getLastUpdated(),
      content: content
    };
    
    // 処理済みとしてマーク
    markAsProcessed(file);
    
    // Pythonスクリプトに送信するためのデータを準備
    // 実際の実装では、WebhookやPub/Subなどを使用
    sendToProcessor(fileInfo);
    
    Logger.log(`処理完了: ${file.getName()}`);
    
  } catch (error) {
    Logger.log(`ファイル処理中にエラーが発生しました: ${file.getName()}`);
    Logger.log(error.toString());
    throw error;
  }
}

/**
 * ファイルを処理済みとしてマーク
 * @param {File} file - マークするファイル
 */
function markAsProcessed(file) {
  try {
    // 方法1: ファイルの説明欄にフラグを追加
    const currentDescription = file.getDescription() || '';
    file.setDescription(currentDescription + '\nPROCESSED: ' + new Date().toISOString());
    
    // 方法2: 処理済みフォルダに移動（オプション）
    if (CONFIG.PROCESSED_FOLDER_ID) {
      const processedFolder = DriveApp.getFolderById(CONFIG.PROCESSED_FOLDER_ID);
      file.moveTo(processedFolder);
    }
    
  } catch (error) {
    Logger.log('処理済みマーク中にエラーが発生しました');
    Logger.log(error.toString());
  }
}

/**
 * 処理データをPythonスクリプトに送信
 * @param {Object} fileInfo - ファイル情報
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
      return;
    }
    
    const payload = {
      file_id: fileInfo.id,
      file_name: fileInfo.name,
      file_url: fileInfo.url,
      created: fileInfo.created.toISOString(),
      modified: fileInfo.modified.toISOString(),
      content: fileInfo.content
    };
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(webhookUrl, options);
    
    if (response.getResponseCode() === 200) {
      Logger.log('Pythonスクリプトへの送信が成功しました');
    } else {
      Logger.log(`エラー: Pythonスクリプトへの送信に失敗しました (${response.getResponseCode()})`);
      Logger.log(response.getContentText());
    }
    
  } catch (error) {
    Logger.log('送信処理中にエラーが発生しました');
    Logger.log(error.toString());
    // エラーが発生しても処理を続行（後で再試行可能）
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

