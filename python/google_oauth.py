"""
Google OAuth 2.0認証モジュール
サービスアカウントキーが使えない場合の代替認証方法
"""

import os
import json
import logging
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleOAuth:
    """Google OAuth 2.0認証クラス"""
    
    # 必要なスコープ
    SCOPES = [
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/drive'
    ]
    
    def __init__(self, config):
        """
        初期化
        
        Args:
            config: 設定オブジェクト
        """
        self.logger = logging.getLogger(__name__)
        
        # 環境変数から認証情報を取得（Heroku用）
        oauth_credentials_json = os.getenv('OAUTH_CREDENTIALS_JSON')
        oauth_token_json = os.getenv('OAUTH_TOKEN_JSON')
        
        if oauth_credentials_json:
            # 環境変数から読み込む（Heroku）
            import json
            import tempfile
            
            # 一時ファイルに保存
            temp_dir = Path(tempfile.gettempdir())
            self.credentials_file = temp_dir / 'credentials.json'
            with open(self.credentials_file, 'w', encoding='utf-8') as f:
                json.dump(json.loads(oauth_credentials_json), f, indent=2)
            
            self.logger.info('環境変数からOAuth認証情報を読み込みました')
        else:
            # ファイルパスから読み込む（ローカル）
            credentials_path = config.get('google.oauth_credentials_path')
            if not credentials_path:
                raise ValueError(
                    'Google OAuth 2.0認証情報のパスが設定されていません。\n'
                    'config.json の google.oauth_credentials_path を設定するか、\n'
                    '環境変数 OAUTH_CREDENTIALS_JSON を設定してください。'
                )
            
            project_root = Path(__file__).parent.parent
            self.credentials_file = project_root / credentials_path
            
            if not self.credentials_file.exists():
                raise FileNotFoundError(
                    f'OAuth 2.0認証情報ファイルが見つかりません: {self.credentials_file}\n'
                    f'Google Cloud ConsoleでOAuth 2.0認証情報を作成し、ダウンロードしてください。'
                )
        
        # トークン保存ファイルのパス
        if oauth_token_json:
            # 環境変数から読み込む（Heroku）
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            self.token_file = temp_dir / 'token.json'
            # 環境変数からトークンを読み込んで保存
            import json
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(json.loads(oauth_token_json), f, indent=2)
            self.logger.info('環境変数からOAuthトークンを読み込みました')
        else:
            # ファイルパスから読み込む（ローカル）
            token_path = config.get('google.oauth_token_path', 'config/token.json')
            project_root = Path(__file__).parent.parent
            self.token_file = project_root / token_path
        
        # 認証情報を取得
        self.credentials = self._get_credentials()
        
        self.logger.info('Google OAuth 2.0認証モジュールを初期化しました')
    
    def _get_credentials(self) -> Credentials:
        """
        OAuth 2.0認証情報を取得（初回はブラウザ認証、次回以降は保存されたトークンを使用）
        
        Returns:
            認証情報オブジェクト
        """
        creds = None
        
        # 保存されたトークンがある場合は読み込む
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r', encoding='utf-8') as token:
                    creds = Credentials.from_authorized_user_info(
                        json.load(token), self.SCOPES
                    )
                self.logger.info('保存されたトークンを読み込みました')
            except Exception as e:
                self.logger.warning(f'トークンの読み込みに失敗しました: {str(e)}')
        
        # トークンが無効または存在しない場合は、新しいトークンを取得
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # トークンをリフレッシュ
                try:
                    self.logger.info('トークンをリフレッシュします')
                    creds.refresh(Request())
                except Exception as e:
                    self.logger.warning(f'トークンのリフレッシュに失敗しました: {str(e)}')
                    creds = None
            
            if not creds:
                # 初回認証フロー
                self.logger.info('OAuth 2.0認証フローを開始します')
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), self.SCOPES
                )
                
                # ブラウザで認証（ローカル環境の場合）
                # Herokuなどの本番環境では、事前に認証済みトークンを使用
                if os.getenv('FLASK_ENV') != 'production' and os.getenv('HEROKU') is None:
                    creds = flow.run_local_server(port=0)
                else:
                    # 本番環境では、認証URLを表示して手動で認証
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    self.logger.warning(
                        f'本番環境では手動認証が必要です。以下のURLにアクセスしてください:\n'
                        f'{auth_url}\n'
                        f'認証後、表示されたコードを環境変数 OAUTH_CODE に設定してください。'
                    )
                    raise RuntimeError(
                        '本番環境では事前に認証済みトークンが必要です。'
                        'ローカル環境で認証を行い、token.jsonを本番環境に配置してください。'
                    )
            
            # トークンを保存
            self._save_credentials(creds)
        
        return creds
    
    def _save_credentials(self, creds: Credentials):
        """認証情報をファイルに保存"""
        try:
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.token_file, 'w', encoding='utf-8') as token:
                token.write(creds.to_json())
            
            self.logger.info(f'認証情報を保存しました: {self.token_file}')
            
        except Exception as e:
            self.logger.error(f'認証情報の保存に失敗しました: {str(e)}')
            raise
    
    def get_docs_service(self):
        """Google Docs APIサービスを取得"""
        return build('docs', 'v1', credentials=self.credentials)
    
    def get_drive_service(self):
        """Google Drive APIサービスを取得"""
        return build('drive', 'v3', credentials=self.credentials)

