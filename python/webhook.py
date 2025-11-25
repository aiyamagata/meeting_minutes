"""
Webhookエンドポイント
Herokuで動作するFlaskアプリケーション
GASから呼び出される想定
"""

from flask import Flask, request, jsonify
import os
import sys
import logging
from pathlib import Path

# ログ設定（Heroku用）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

app = Flask(__name__)
logger = logging.getLogger(__name__)

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    logger.info(f'プロジェクトルートをパスに追加しました: {project_root}')

# インポート（Heroku環境では python パッケージとして認識される）
try:
    logger.info('python.mainからのインポートを試行します...')
    from python.main import process_transcript
    from python.config import Config
    logger.info('インポートに成功しました: python.main, python.config')
except ImportError as e:
    logger.error(f'python.mainからのインポートに失敗しました: {str(e)}', exc_info=True)
    # フォールバック: 相対インポートを試行
    try:
        logger.info('相対インポートを試行します...')
        from main import process_transcript
        from config import Config
        logger.info('相対インポートに成功しました')
    except ImportError as e2:
        logger.error(f'相対インポートも失敗しました: {str(e2)}', exc_info=True)
        logger.error(f'sys.path: {sys.path}')
        raise

# 設定の読み込み
try:
    config = Config()
    logger.info('設定ファイルの読み込みに成功しました')
except Exception as e:
    logger.error(f'設定ファイルの読み込みに失敗しました: {str(e)}', exc_info=True)
    raise


@app.route('/webhook', methods=['POST'])
def webhook():
    """
    GASからのWebhookを受け取るエンドポイント
    
    リクエストボディの例:
    {
        "file_id": "xxx",
        "file_name": "meeting_transcript.txt",
        "file_url": "https://...",
        "content": "文字起こしの内容..."
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid request'}), 400
        
        # 必須フィールドの確認
        required_fields = ['file_id', 'file_name', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400
        
        logger.info(f'Webhook受信: {data["file_name"]}')
        
        # 文字起こしを処理
        process_transcript(
            transcript_content=data['content'],
            file_name=data['file_name'],
            config=config,
            logger=logger
        )
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f'Webhook処理中にエラーが発生しました: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェックエンドポイント"""
    return jsonify({'status': 'ok'}), 200


if __name__ == '__main__':
    # ローカル実行用（Herokuではgunicornを使用）
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)

