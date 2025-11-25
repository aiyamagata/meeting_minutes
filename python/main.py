#!/usr/bin/env python3
"""
Google Meet 議事録自動生成・Slack投稿ツール
メインスクリプト
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from python.text_processor import TextProcessor
from python.slack_poster import SlackPoster
from python.config import Config
from python.google_doc_creator import GoogleDocCreator


def setup_logging():
    """ログ設定"""
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f'app_{datetime.now().strftime("%Y%m%d")}.log'
    
    # DEBUGレベルでログを出力（問題の特定のため）
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def main():
    """メイン処理"""
    logger = setup_logging()
    logger.info('=== 議事録自動生成ツール 開始 ===')
    
    try:
        # 設定の読み込み
        config = Config()
        logger.info('設定ファイルを読み込みました')
        
        # テストモードの確認
        test_mode = '--test' in sys.argv
        if test_mode:
            logger.info('テストモードで実行します')
            run_test_mode(config, logger)
            return
        
        # 実際の処理（HerokuやWebhookから呼び出される想定）
        # ここでは、Google Sheetsからデータを取得する例を示す
        process_from_sheet(config, logger)
        
    except Exception as e:
        logger.error(f'エラーが発生しました: {str(e)}', exc_info=True)
        sys.exit(1)
    
    logger.info('=== 議事録自動生成ツール 完了 ===')


def run_test_mode(config, logger):
    """テストモードの実行"""
    logger.info('テストモード: サンプルデータで処理を実行します')
    
    # サンプルデータ
    sample_transcript = """
    2024年01月15日 10:00 - 11:00
    会議: プロジェクト進捗確認
    
    たろう: おはようございます。今日はプロジェクトの進捗を確認したいと思います。
    はなこ: 了解です。現在、開発は順調に進んでいます。
    たろう: 良いですね。来週までに完成させたいです。
    はなこ: はい、問題ありません。
    """
    
    # 処理を実行
    process_transcript(
        transcript_content=sample_transcript,
        file_name='test_meeting_20240115.txt',
        config=config,
        logger=logger
    )


def process_from_sheet(config, logger):
    """Google Sheetsからデータを取得して処理"""
    # 実装は環境に応じて変更
    # 例: Google Sheets APIを使用してデータを取得
    logger.info('Google Sheetsからデータを取得します')
    
    # ここにGoogle Sheets APIの実装を追加
    # または、Webhookから呼び出される場合は、request bodyから取得
    
    logger.warning('Google Sheetsからの取得機能は未実装です')
    logger.info('Webhook経由で呼び出される場合は、request bodyからデータを取得してください')


def process_transcript(transcript_content, file_name, config, logger):
    """文字起こしを処理して議事録を生成"""
    try:
        logger.info(f'処理開始: {file_name}')
        
        # テキスト処理
        processor = TextProcessor(config)
        processed_text = processor.process(transcript_content)
        logger.info('テキスト処理が完了しました')
        
        # Google Documentの作成
        doc_creator = GoogleDocCreator(config)
        doc_url = doc_creator.create_document(
            title=f'議事録_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            content=processed_text
        )
        logger.info(f'Google Documentを作成しました: {doc_url}')
        
        # Slackに投稿
        slack_poster = SlackPoster(config)
        message = create_slack_message(file_name, doc_url, config)
        slack_poster.post_message(message)
        logger.info('Slackに投稿しました')
        
        logger.info(f'処理完了: {file_name}')
        
    except Exception as e:
        logger.error(f'処理中にエラーが発生しました: {str(e)}', exc_info=True)
        raise


def create_slack_message(file_name, doc_url, config):
    """Slackメッセージを作成"""
    date_str = datetime.now().strftime(config.get('format.date_format', '%Y年%m月%d日'))
    
    message = {
        'text': f'📝 議事録が生成されました',
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'*📝 議事録が生成されました*\n\n'
                           f'*ファイル名:* {file_name}\n'
                           f'*日付:* {date_str}\n'
                           f'*Document:* <{doc_url}|議事録を開く>'
                }
            }
        ]
    }
    
    return message


if __name__ == '__main__':
    main()

