"""
Google Document作成モジュール
サービスアカウントキーとOAuth 2.0の両方に対応
"""

import logging
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# OAuth 2.0認証モジュール（オプション）
try:
    from .google_oauth import GoogleOAuth
    OAUTH_AVAILABLE = True
except ImportError:
    try:
        from google_oauth import GoogleOAuth
        OAUTH_AVAILABLE = True
    except ImportError:
        OAUTH_AVAILABLE = False


class GoogleDocCreator:
    """Google Document作成クラス"""
    
    def __init__(self, config):
        """
        初期化
        
        Args:
            config: 設定オブジェクト
        """
        self.logger = logging.getLogger(__name__)
        
        # 認証方法の判定
        auth_method = config.get('google.auth_method', 'service_account')
        
        if auth_method == 'oauth2' or not config.get('google.service_account_path'):
            # OAuth 2.0認証を使用
            if not OAUTH_AVAILABLE:
                raise ImportError(
                    'OAuth 2.0認証を使用するには、google-auth-oauthlibが必要です。\n'
                    'pip install google-auth-oauthlib を実行してください。'
                )
            
            self.logger.info('OAuth 2.0認証を使用します')
            oauth = GoogleOAuth(config)
            self.docs_service = oauth.get_docs_service()
            self.drive_service = oauth.get_drive_service()
            
        else:
            # サービスアカウント認証を使用（従来の方法）
            self.logger.info('サービスアカウント認証を使用します')
            service_account_path = config.get('google.service_account_path')
            if not service_account_path:
                raise ValueError('Google Service Accountのパスが設定されていません')
            
            project_root = Path(__file__).parent.parent
            service_account_file = project_root / service_account_path
            
            if not service_account_file.exists():
                raise FileNotFoundError(
                    f'サービスアカウントファイルが見つかりません: {service_account_file}\n'
                    f'OAuth 2.0認証を使用する場合は、config.jsonで auth_method を "oauth2" に設定してください。'
                )
            
            # 認証情報の読み込み
            credentials = service_account.Credentials.from_service_account_file(
                str(service_account_file),
                scopes=[
                    'https://www.googleapis.com/auth/documents',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
            
            # APIサービスの構築
            self.docs_service = build('docs', 'v1', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
        
        # 保存先フォルダID
        self.folder_id = config.get('google.drive_folder_id')
        
        self.logger.info('Google Document作成モジュールを初期化しました')
    
    def create_document(self, title: str, content: str) -> str:
        """
        Google Documentを作成
        
        Args:
            title: ドキュメントのタイトル
            content: ドキュメントの内容
            
        Returns:
            ドキュメントのURL
        """
        try:
            self.logger.info(f'Google Documentを作成します: {title}')
            
            # ドキュメントを作成
            document = self.docs_service.documents().create(
                body={'title': title}
            ).execute()
            
            document_id = document.get('documentId')
            self.logger.info(f'ドキュメントを作成しました (ID: {document_id})')
            
            # 内容を挿入
            self._insert_text(document_id, content)
            
            # フォルダに移動（フォルダIDが指定されている場合）
            if self.folder_id:
                self._move_to_folder(document_id, self.folder_id)
            
            # ドキュメントのURLを取得
            doc_url = f'https://docs.google.com/document/d/{document_id}'
            
            self.logger.info(f'Google Documentの作成が完了しました: {doc_url}')
            return doc_url
            
        except HttpError as e:
            self.logger.error(f'Google APIエラーが発生しました: {str(e)}')
            raise
        except Exception as e:
            self.logger.error(f'Google Document作成中にエラーが発生しました: {str(e)}')
            raise
    
    def _insert_text(self, document_id: str, content: str):
        """テキストをドキュメントに挿入"""
        try:
            # テキストを行ごとに分割
            lines = content.split('\n')
            
            requests = []
            for i, line in enumerate(lines):
                # 改行を追加（最後の行以外）
                text = line + ('\n' if i < len(lines) - 1 else '')
                
                requests.append({
                    'insertText': {
                        'location': {
                            'index': 1
                        },
                        'text': text
                    }
                })
            
            # バッチリクエストで挿入
            self.docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()
            
            self.logger.debug('テキストをドキュメントに挿入しました')
            
        except Exception as e:
            self.logger.error(f'テキスト挿入中にエラーが発生しました: {str(e)}')
            raise
    
    def _move_to_folder(self, document_id: str, folder_id: str):
        """ドキュメントをフォルダに移動"""
        try:
            # 現在の親フォルダを取得
            file = self.drive_service.files().get(
                fileId=document_id,
                fields='parents'
            ).execute()
            
            previous_parents = ','.join(file.get('parents', []))
            
            # 新しいフォルダに移動
            self.drive_service.files().update(
                fileId=document_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            self.logger.debug(f'ドキュメントをフォルダに移動しました: {folder_id}')
            
        except Exception as e:
            self.logger.warning(f'フォルダへの移動に失敗しました（ドキュメントは作成されています）: {str(e)}')
            # フォルダへの移動に失敗してもドキュメントは作成されているので、エラーは出さない

