"""
テキスト処理モジュール
参加者名の修正、フォーマット整形などを行う
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List


class ParticipantMapper:
    """参加者名のマッピングクラス"""
    
    def __init__(self, mapping_file: str):
        """
        初期化
        
        Args:
            mapping_file: 参加者名マッピングファイルのパス
        """
        self.logger = logging.getLogger(__name__)
        self.mapping = self._load_mapping(mapping_file)
        self.logger.info(f'参加者名マッピングを読み込みました: {len(self.mapping)}件')
    
    def _load_mapping(self, mapping_file: str) -> Dict[str, str]:
        """マッピングファイルを読み込む"""
        try:
            file_path = Path(mapping_file)
            if not file_path.exists():
                self.logger.warning(f'マッピングファイルが見つかりません: {mapping_file}')
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            
            return mapping
            
        except Exception as e:
            self.logger.error(f'マッピングファイルの読み込みに失敗しました: {str(e)}')
            return {}
    
    def map(self, name: str) -> str:
        """
        参加者名をマッピング
        
        Args:
            name: 元の名前
            
        Returns:
            マッピング後の名前（マッピングがない場合は元の名前）
        """
        # 前後の空白を削除
        name = name.strip()
        
        # マッピングがある場合は置換
        if name in self.mapping:
            mapped_name = self.mapping[name]
            self.logger.debug(f'名前をマッピング: {name} -> {mapped_name}')
            return mapped_name
        
        return name


class TextProcessor:
    """テキスト処理クラス"""
    
    def __init__(self, config):
        """
        初期化
        
        Args:
            config: 設定オブジェクト
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # 参加者名マッパーの初期化
        mapping_file = config.get('participants.mapping_file', 'config/participants.json')
        self.participant_mapper = ParticipantMapper(mapping_file)
        
        # フォーマット設定
        self.date_format = config.get('format.date_format', '%Y年%m月%d日')
    
    def process(self, text: str) -> str:
        """
        テキストを処理して議事録フォーマットに整形
        
        Args:
            text: 元のテキスト
            
        Returns:
            整形されたテキスト
        """
        try:
            self.logger.info('テキスト処理を開始します')
            
            # 1. 参加者名の修正
            text = self._fix_participant_names(text)
            
            # 2. フォーマットの整形
            text = self._format_text(text)
            
            # 3. 不要な部分の削除
            text = self._clean_text(text)
            
            self.logger.info('テキスト処理が完了しました')
            return text
            
        except Exception as e:
            self.logger.error(f'テキスト処理中にエラーが発生しました: {str(e)}')
            raise
    
    def _fix_participant_names(self, text: str) -> str:
        """参加者名を修正"""
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            # 発言者のパターンを検出（例: "たろう: こんにちは"）
            # 様々なパターンに対応
            patterns = [
                r'^([^:：]+)[:：]\s*(.+)$',  # "名前: 発言"
                r'^([^（(]+)[（(].*?[）)]\s*[:：]\s*(.+)$',  # "名前（役職）: 発言"
            ]
            
            for pattern in patterns:
                match = re.match(pattern, line.strip())
                if match:
                    name = match.group(1).strip()
                    speech = match.group(2).strip() if len(match.groups()) > 1 else ''
                    
                    # 名前をマッピング
                    fixed_name = self.participant_mapper.map(name)
                    
                    # 行を再構築
                    if speech:
                        processed_lines.append(f'{fixed_name}: {speech}')
                    else:
                        processed_lines.append(f'{fixed_name}:')
                    break
            else:
                # パターンに一致しない場合はそのまま
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _format_text(self, text: str) -> str:
        """テキストをフォーマット"""
        lines = text.split('\n')
        formatted_lines = []
        
        # ヘッダー情報の抽出
        header_info = self._extract_header_info(lines)
        
        # フォーマットに従って整形
        formatted_lines.append('=' * 50)
        formatted_lines.append('議事録')
        formatted_lines.append('=' * 50)
        formatted_lines.append('')
        
        if header_info.get('date'):
            formatted_lines.append(f'日時: {header_info["date"]}')
        if header_info.get('title'):
            formatted_lines.append(f'件名: {header_info["title"]}')
        if header_info.get('participants'):
            formatted_lines.append(f'参加者: {", ".join(header_info["participants"])}')
        
        formatted_lines.append('')
        formatted_lines.append('-' * 50)
        formatted_lines.append('')
        
        # 本文を追加
        in_body = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # ヘッダー部分をスキップ
            if not in_body and self._is_header_line(line):
                continue
            
            in_body = True
            formatted_lines.append(line)
        
        formatted_lines.append('')
        formatted_lines.append('=' * 50)
        
        return '\n'.join(formatted_lines)
    
    def _extract_header_info(self, lines: List[str]) -> Dict:
        """ヘッダー情報を抽出"""
        info = {
            'date': None,
            'title': None,
            'participants': []
        }
        
        # 日付パターン
        date_pattern = r'(\d{4}年\d{1,2}月\d{1,2}日|\d{4}/\d{1,2}/\d{1,2}|\d{4}-\d{1,2}-\d{1,2})'
        
        # タイトルパターン
        title_patterns = [
            r'会議[:：]\s*(.+)',
            r'件名[:：]\s*(.+)',
            r'タイトル[:：]\s*(.+)',
        ]
        
        for line in lines[:10]:  # 最初の10行をチェック
            line = line.strip()
            
            # 日付の検出
            if not info['date']:
                match = re.search(date_pattern, line)
                if match:
                    info['date'] = match.group(1)
            
            # タイトルの検出
            if not info['title']:
                for pattern in title_patterns:
                    match = re.search(pattern, line)
                    if match:
                        info['title'] = match.group(1).strip()
                        break
        
        return info
    
    def _is_header_line(self, line: str) -> bool:
        """ヘッダー行かどうかを判定"""
        header_patterns = [
            r'^\d{4}年\d{1,2}月\d{1,2}日',
            r'会議[:：]',
            r'件名[:：]',
            r'タイトル[:：]',
        ]
        
        for pattern in header_patterns:
            if re.search(pattern, line):
                return True
        
        return False
    
    def _clean_text(self, text: str) -> str:
        """不要な部分を削除"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 空行の連続を1つに
            if not line:
                if cleaned_lines and cleaned_lines[-1]:
                    cleaned_lines.append('')
                continue
            
            # 特定のパターンを削除（必要に応じて追加）
            skip_patterns = [
                r'^\[.*?\]$',  # [音声認識] などのメタ情報
                r'^\(.*?\)$',  # (笑) などの補足
            ]
            
            should_skip = False
            for pattern in skip_patterns:
                if re.match(pattern, line):
                    should_skip = True
                    break
            
            if not should_skip:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

