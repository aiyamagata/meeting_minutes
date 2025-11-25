"""
Slack投稿モジュール
"""

import requests
import json
import logging
from typing import Dict, Optional


class SlackPoster:
    """Slack投稿クラス"""
    
    def __init__(self, config):
        """
        初期化
        
        Args:
            config: 設定オブジェクト
        """
        self.logger = logging.getLogger(__name__)
        self.bot_token = config.get('slack.bot_token')
        self.channel = config.get('slack.channel', '#meeting-minutes')
        
        if not self.bot_token:
            raise ValueError('Slack Bot Tokenが設定されていません')
        
        self.base_url = 'https://slack.com/api'
        self.logger.info(f'Slack投稿モジュールを初期化しました (チャンネル: {self.channel})')
    
    def post_message(self, message: Dict) -> bool:
        """
        メッセージをSlackに投稿
        
        Args:
            message: メッセージオブジェクト（textまたはblocksを含む）
            
        Returns:
            成功した場合True
        """
        try:
            url = f'{self.base_url}/chat.postMessage'
            
            headers = {
                'Authorization': f'Bearer {self.bot_token}',
                'Content-Type': 'application/json'
            }
            
            # メッセージ形式を確認・修正
            payload = {
                'channel': self.channel
            }
            
            # text と blocks の両方がある場合、blocks を優先
            if 'blocks' in message:
                payload['blocks'] = message['blocks']
                # blocks がある場合、text はフォールバックとして使用
                if 'text' in message:
                    payload['text'] = message['text']
            elif 'text' in message:
                payload['text'] = message['text']
            else:
                self.logger.error('メッセージに text または blocks が含まれていません')
                return False
            
            self.logger.debug(f'投稿ペイロード: {json.dumps(payload, ensure_ascii=False, indent=2)}')
            
            response = requests.post(url, headers=headers, json=payload)
            
            # HTTPステータスコードを確認（200以外の場合はエラー）
            if response.status_code != 200:
                self.logger.error(f'HTTPエラー: {response.status_code}')
                self.logger.error(f'レスポンス: {response.text}')
                response.raise_for_status()
            
            result = response.json()
            
            # デバッグ: レスポンスの詳細をログに出力
            self.logger.debug(f'Slack APIレスポンス: {json.dumps(result, ensure_ascii=False, indent=2)}')
            
            if result.get('ok'):
                self.logger.info(f'Slackにメッセージを投稿しました: {self.channel}')
                return True
            else:
                error = result.get('error', 'unknown')
                error_detail = result.get('response_metadata', {}).get('messages', [])
                self.logger.error(
                    f'Slack投稿に失敗しました: {error}\n'
                    f'チャンネル: {self.channel}\n'
                    f'詳細: {result}\n'
                    f'エラーメッセージ: {error_detail}'
                )
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f'Slack APIリクエスト中にエラーが発生しました: {str(e)}')
            return False
        except Exception as e:
            self.logger.error(f'Slack投稿中にエラーが発生しました: {str(e)}')
            return False
    
    def post_file(self, file_path: str, title: Optional[str] = None) -> bool:
        """
        ファイルをSlackに投稿
        
        Args:
            file_path: ファイルのパス
            title: ファイルのタイトル
            
        Returns:
            成功した場合True
        """
        try:
            url = f'{self.base_url}/files.upload'
            
            headers = {
                'Authorization': f'Bearer {self.bot_token}'
            }
            
            with open(file_path, 'rb') as f:
                files = {
                    'file': f
                }
                
                data = {
                    'channels': self.channel
                }
                
                if title:
                    data['title'] = title
                
                response = requests.post(url, headers=headers, files=files, data=data)
                response.raise_for_status()
                
                result = response.json()
                
                if result.get('ok'):
                    self.logger.info(f'Slackにファイルを投稿しました: {file_path}')
                    return True
                else:
                    error = result.get('error', 'unknown')
                    self.logger.error(f'Slackファイル投稿に失敗しました: {error}')
                    return False
                    
        except Exception as e:
            self.logger.error(f'Slackファイル投稿中にエラーが発生しました: {str(e)}')
            return False

