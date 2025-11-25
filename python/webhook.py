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

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from python.main import process_transcript
from python.config import Config

app = Flask(__name__)
logger = logging.getLogger(__name__)

# 設定の読み込み
config = Config()


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

