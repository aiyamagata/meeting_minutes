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
                    try:
                        name = match.group(1).strip()
                        # group(2)が存在するか安全に確認
                        if match.lastindex and match.lastindex >= 2:
                            speech = match.group(2).strip()
                        else:
                            speech = ''
                        
                        # 名前をマッピング
                        fixed_name = self.participant_mapper.map(name)
                        
                        # 行を再構築
                        if speech:
                            processed_lines.append(f'{fixed_name}: {speech}')
                        else:
                            processed_lines.append(f'{fixed_name}:')
                        break
                    except IndexError as e:
                        self.logger.warning(f'正規表現マッチングエラー (行: {line[:50]}): {str(e)}')
                        # エラーが発生した場合はそのまま追加
                        processed_lines.append(line)
                        break
            else:
                # パターンに一致しない場合はそのまま
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _format_text(self, text: str) -> str:
        """テキストをフォーマット（新しいフォーマット）"""
        lines = text.split('\n')
        formatted_lines = []
        
        # ヘッダー情報の抽出
        header_info = self._extract_header_info(lines)
        
        # アクション項目の抽出
        action_items = self._extract_action_items(lines)
        
        # 本文（話し合ったことの要点）の抽出
        main_content = self._extract_main_content(lines)
        
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
        
        # [話し合ったことの要点]セクション
        formatted_lines.append('[話し合ったことの要点]')
        formatted_lines.append('')
        formatted_lines.extend(main_content)
        formatted_lines.append('')
        formatted_lines.append('-' * 50)
        formatted_lines.append('')
        
        # [各々が次取るべきアクション]セクション
        formatted_lines.append('[各々が次取るべきアクション]')
        formatted_lines.append('')
        
        if action_items:
            for action in action_items:
                action_text = action['name']
                if action.get('action'):
                    action_text += f": {action['action']}"
                if action.get('deadline'):
                    action_text += f" （{action['deadline']}までに）"
                formatted_lines.append(f"□ {action_text}")
        else:
            formatted_lines.append('（アクション項目は自動抽出できませんでした。手動で追加してください）')
        
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
    
    def _extract_main_content(self, lines: List[str]) -> List[str]:
        """本文（話し合ったことの要点）を抽出"""
        content_lines = []
        in_body = False
        
        for line in lines:
            line = line.strip()
            
            # ヘッダー部分をスキップ
            if not in_body:
                if self._is_header_line(line):
                    continue
                # 空行の後の最初の非ヘッダー行から本文開始
                if line and not self._is_header_line(line):
                    in_body = True
            
            if in_body:
                # アクション項目のキーワードが含まれている場合は本文終了
                action_keywords = ['アクション', 'todo', 'to do', 'やること', '次回', '課題']
                if any(keyword in line.lower() for keyword in action_keywords):
                    break
                    
                if line:
                    content_lines.append(line)
        
        return content_lines if content_lines else ['（内容を手動で追加してください）']
    
    def _extract_action_items(self, lines: List[str]) -> List[Dict[str, str]]:
        """アクション項目を抽出"""
        action_items = []
        
        # アクション項目のパターン
        action_patterns = [
            # "名前: アクション内容 (期日までに)" 形式
            r'^([^:：]+)[:：]\s*(.+?)(?:（(.+?)までに）|\((.+?)までに\))?$',
            # "名前 - アクション内容" 形式
            r'^([^-]+?)\s*-\s*(.+)$',
        ]
        
        action_keywords = ['アクション', 'todo', 'to do', 'やること', '次回', '課題', 'タスク']
        
        in_action_section = False
        for line in lines:
            line = line.strip()
            
            # アクションセクションの開始を検出
            if any(keyword in line.lower() for keyword in action_keywords):
                in_action_section = True
                continue
            
            if in_action_section or ':' in line or '：' in line:
                # パターンマッチングでアクション項目を抽出
                for pattern in action_patterns:
                    match = re.search(pattern, line)
                    if match:
                        try:
                            name = match.group(1).strip()
                            # group(2)が存在するか安全に確認
                            if match.lastindex and match.lastindex >= 2:
                                action_text = match.group(2).strip()
                            else:
                                action_text = ''
                            # deadlineはgroup(3)またはgroup(4)から取得
                            deadline = None
                            try:
                                if match.lastindex and match.lastindex >= 3:
                                    deadline = match.group(3)
                                elif match.lastindex and match.lastindex >= 4:
                                    deadline = match.group(4)
                            except IndexError:
                                # グループが存在しない場合はNoneのまま
                                deadline = None
                            
                            # 名前をマッピング
                            mapped_name = self.participant_mapper.map(name)
                            
                            action_items.append({
                                'name': mapped_name,
                                'action': action_text if action_text else None,
                                'deadline': deadline.strip() if deadline else None
                            })
                            break
                        except IndexError as e:
                            self.logger.warning(f'アクション項目抽出エラー (行: {line[:50]}): {str(e)}')
                            # エラーが発生した場合はスキップ
                            break
        
        return action_items
    
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

