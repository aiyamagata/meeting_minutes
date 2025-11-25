"""
設定管理モジュール
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Optional


class Config:
    """設定管理クラス"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初期化
        
        Args:
            config_file: 設定ファイルのパス（Noneの場合はデフォルト）
        """
        self.logger = logging.getLogger(__name__)
        
        if config_file is None:
            project_root = Path(__file__).parent.parent
            config_file = project_root / 'config' / 'config.json'
        
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self.logger.info(f'設定ファイルを読み込みました: {self.config_file}')
    
    def _load_config(self) -> dict:
        """設定ファイルを読み込む"""
        config = {}
        
        # ファイルから読み込み
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as e:
                self.logger.warning(f'設定ファイルの読み込みに失敗しました: {str(e)}')
        
        # 環境変数で上書き（優先）
        config = self._override_with_env(config)
        
        return config
    
    def _override_with_env(self, config: dict) -> dict:
        """環境変数で設定を上書き"""
        # ネストされた設定を環境変数で上書きできるようにする
        # 例: SLACK_BOT_TOKEN -> config['slack']['bot_token']
        
        env_mappings = {
            'SLACK_BOT_TOKEN': ('slack', 'bot_token'),
            'SLACK_CHANNEL': ('slack', 'channel'),
            'GOOGLE_DRIVE_FOLDER_ID': ('google', 'drive_folder_id'),
            'SERVICE_ACCOUNT_PATH': ('google', 'service_account_path'),
            'GOOGLE_AUTH_METHOD': ('google', 'auth_method'),
            'OAUTH_CREDENTIALS_PATH': ('google', 'oauth_credentials_path'),
            'OAUTH_TOKEN_PATH': ('google', 'oauth_token_path'),
            'OAUTH_CREDENTIALS_JSON': ('google', 'oauth_credentials_json'),
            'OAUTH_TOKEN_JSON': ('google', 'oauth_token_json'),
        }
        
        for env_key, (section, key) in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value:
                if section not in config:
                    config[section] = {}
                config[section][key] = env_value
                self.logger.debug(f'環境変数から設定を読み込みました: {env_key}')
        
        return config
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        設定値を取得（ドット記法でネストされたキーに対応）
        
        Args:
            key_path: キーのパス（例: 'slack.bot_token'）
            default: デフォルト値
            
        Returns:
            設定値
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """
        設定値を設定
        
        Args:
            key_path: キーのパス
            value: 設定値
        """
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def save(self):
        """設定をファイルに保存"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f'設定ファイルを保存しました: {self.config_file}')
            
        except Exception as e:
            self.logger.error(f'設定ファイルの保存に失敗しました: {str(e)}')
            raise

