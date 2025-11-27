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
            
            # Google Docs APIのinsertTextで500エラーが発生する問題を回避するため、
            # 最初からDrive APIを使用してテキストファイルをアップロードしてから変換する方法を使用
            self.logger.info('Drive APIを使用してドキュメントを作成します（insertTextの500エラーを回避）')
            document_id = self._create_document_via_drive(None, content, title)
            
            # チェックリスト項目の処理（「□」で始まる行をチェックリスト形式に変換）
            lines = content.split('\n')
            checkbox_line_indices = []
            for i, line in enumerate(lines):
                if line.strip().startswith('□'):
                    checkbox_line_indices.append(i)
            
            if checkbox_line_indices:
                self.logger.info(f'{len(checkbox_line_indices)}個のチェックリスト項目を検出しました')
                try:
                    self._apply_checklist_format(document_id, checkbox_line_indices)
                except Exception as e:
                    self.logger.warning(f'チェックリスト形式の適用に失敗しました: {str(e)}')
                    # チェックリスト形式の適用失敗は無視して続行
            
            # フォルダに移動（フォルダIDが指定されている場合）
            if self.folder_id:
                self._move_to_folder(document_id, self.folder_id)
            
            # ドキュメントのURLを取得（document_idが変更されている可能性があるため、再取得）
            doc_url = f'https://docs.google.com/document/d/{document_id}'
            
            self.logger.info(f'Google Documentの作成が完了しました: {doc_url}')
            
            # GAS側で移動処理を行うため、document_idも返す
            return {
                'url': doc_url,
                'document_id': document_id
            }
            
        except HttpError as e:
            self.logger.error(f'Google APIエラーが発生しました: {str(e)}')
            raise
        except Exception as e:
            self.logger.error(f'Google Document作成中にエラーが発生しました: {str(e)}')
            raise
    
    def _insert_text(self, document_id: str, content: str):
        """テキストをドキュメントに挿入（チェックリスト対応）"""
        self.logger.info(f'=== テキスト挿入処理を開始 ===')
        self.logger.info(f'ドキュメントID: {document_id}')
        self.logger.info(f'コンテンツサイズ: {len(content)} 文字')
        self.logger.info(f'コンテンツの最初の200文字: {repr(content[:200])}')
        
        failed_lines = []  # 失敗した行を記録
        
        try:
            # テキストを行ごとに分割
            lines = content.split('\n')
            self.logger.info(f'テキストを{len(lines)}行に分割しました')
            self.logger.info(f'最初の5行: {[repr(line[:50]) for line in lines[:5]]}')
            
            # チェックリスト項目の行番号を記録（後でチェックリスト形式を適用するため）
            checkbox_line_indices = []
            
            # すべてのテキストを結合
            full_text_parts = []
            
            for i, line in enumerate(lines):
                # 「□」で始まる行をチェックリスト項目として認識
                if line.strip().startswith('□'):
                    checkbox_line_indices.append(i)
                    # 「□」を削除してテキストを挿入
                    checkbox_text = line.replace('□', '', 1).strip()
                    full_text_parts.append(checkbox_text)
                else:
                    full_text_parts.append(line)
                
                # 最後の行以外は改行を追加
                if i < len(lines) - 1:
                    full_text_parts.append('\n')
            
            # すべてのテキストを結合
            full_text = ''.join(full_text_parts)
            
            # テキストをクリーニング（制御文字や特殊文字を除去）
            full_text = self._clean_text(full_text)
            self.logger.info(f'クリーニング後のテキストサイズ: {len(full_text)} 文字')
            
            # より安全な方法：1行ずつ挿入（最も安全な方法）
            self.logger.info(f'テキストを1行ずつ挿入します (総文字数: {len(full_text)}, 行数: {len(lines)})')
            
            # テキストが空の場合はスキップ
            if not full_text or not full_text.strip():
                self.logger.warning('テキストが空のため、挿入をスキップします')
                return
            
            # 最初の行が空でないことを確認
            first_non_empty_line = None
            for i, line in enumerate(lines):
                if line.strip():
                    first_non_empty_line = i
                    break
            
            if first_non_empty_line is None:
                self.logger.warning('すべての行が空のため、挿入をスキップします')
                return
            
            self.logger.info(f'最初の非空行: {first_non_empty_line + 1}行目')
            
            self.logger.info(f'テキスト挿入処理を開始します (行数: {len(lines)}, チェックリスト項目数: {len(checkbox_line_indices)})')
            
            try:
                failed_lines = self._insert_text_line_by_line(document_id, lines, checkbox_line_indices)
                if failed_lines:
                    self.logger.warning(f'{len(failed_lines)}行の挿入に失敗しました: {failed_lines}')
                else:
                    self.logger.info('すべての行を正常に挿入しました')
            except Exception as e:
                self.logger.error(f'テキスト挿入中にエラーが発生しました: {str(e)}')
                self.logger.error(f'エラー詳細: {repr(e)}')
                import traceback
                self.logger.error(f'トレースバック: {traceback.format_exc()}')
                # エラーが発生しても、部分的な成功を記録
                if failed_lines:
                    self.logger.warning(f'{len(failed_lines)}行の挿入に失敗しました')
                raise
            
            # チェックリスト形式を適用
            if checkbox_line_indices:
                try:
                    self._apply_checklist_format(document_id, checkbox_line_indices)
                except Exception as e:
                    self.logger.warning(f'チェックリスト形式の適用に失敗しました: {str(e)}')
                    # チェックリスト形式の適用失敗は無視して続行
            
        except HttpError as e:
            self.logger.error(f'Google Docs APIエラーが発生しました: {str(e)}')
            self.logger.error(f'エラー詳細: {repr(e)}')
            if hasattr(e, 'resp'):
                self.logger.error(f'ステータスコード: {e.resp.status}')
                self.logger.error(f'レスポンス: {e.resp}')
            if e.resp.status == 500:
                self.logger.error('500エラー: テキストが大きすぎる可能性があります')
                self.logger.error(f'テキストサイズ: {len(content)} 文字')
                self.logger.error(f'テキストの最初の200文字: {content[:200]}')
            raise
        except Exception as e:
            self.logger.error(f'テキスト挿入中にエラーが発生しました: {str(e)}')
            self.logger.error(f'エラー詳細: {repr(e)}')
            import traceback
            self.logger.error(f'トレースバック: {traceback.format_exc()}')
            raise
    
    def _clean_text(self, text: str) -> str:
        """テキストをクリーニング（制御文字や問題のある文字を除去）"""
        import re
        
        if not text:
            return text
        
        # 制御文字を除去（改行、タブ、復帰は保持）
        # 許可する制御文字: \n (LF), \r (CR), \t (TAB)
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # ゼロ幅文字を除去
        cleaned = cleaned.replace('\u200B', '')  # Zero-width space
        cleaned = cleaned.replace('\u200C', '')  # Zero-width non-joiner
        cleaned = cleaned.replace('\u200D', '')  # Zero-width joiner
        cleaned = cleaned.replace('\uFEFF', '')  # Zero-width no-break space
        
        # その他の問題のあるUnicode文字を除去
        # 右から左へのマーカーなど
        cleaned = re.sub(r'[\u200E\u200F\u202A-\u202E\u2066-\u2069]', '', cleaned)
        
        # サロゲートペアを除去（問題を引き起こす可能性がある）
        cleaned = re.sub(r'[\uD800-\uDFFF]', '', cleaned)
        
        # 非文字を除去
        cleaned = re.sub(r'[\uFFFE\uFFFF]', '', cleaned)
        
        # 過度に長い連続する空白を単一の空白に置換
        cleaned = re.sub(r' {3,}', ' ', cleaned)
        
        # 過度に長い連続する改行を2つの改行に置換
        cleaned = re.sub(r'\n{4,}', '\n\n\n', cleaned)
        
        return cleaned
    
    def _insert_text_chunk(self, document_id: str, text: str, index: int, max_retries: int = 3):
        """テキストのチャンクを挿入（リトライ機能付き）"""
        import time
        
        # テキストが空の場合はスキップ
        if not text or not text.strip():
            return
        
        # テキストサイズを再確認（念のため）
        if len(text) > 1000:
            self.logger.warning(f'チャンクサイズが大きすぎます ({len(text)}文字)。さらに分割します。')
            # さらに小さく分割（段落単位で分割）
            paragraphs = text.split('\n\n')
            if len(paragraphs) > 1:
                # 段落単位で分割
                current_chunk = []
                current_size = 0
                for para in paragraphs:
                    para_with_sep = para + '\n\n'
                    para_size = len(para_with_sep)
                    
                    if current_size + para_size > 5000 and current_chunk:
                        chunk_text = '\n\n'.join(current_chunk)
                        self._insert_text_chunk(document_id, chunk_text, index, max_retries)
                        index = self._get_document_length(document_id)
                        current_chunk = []
                        current_size = 0
                    
                    current_chunk.append(para)
                    current_size += para_size
                
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    self._insert_text_chunk(document_id, chunk_text, index, max_retries)
                return
            else:
                # 段落がない場合は改行位置で分割
                mid_point = len(text) // 2
                split_pos = text.rfind('\n', 0, mid_point)
                if split_pos == -1:
                    split_pos = mid_point
                
                first_half = text[:split_pos + 1]  # 改行を含める
                second_half = text[split_pos + 1:]
                
                self._insert_text_chunk(document_id, first_half, index, max_retries)
                # 次の位置を取得
                next_index = self._get_document_length(document_id)
                self._insert_text_chunk(document_id, second_half, next_index, max_retries)
                return
        
        for attempt in range(max_retries):
            try:
                self.logger.debug(f'テキストチャンクを挿入します (サイズ: {len(text)}文字, 位置: {index}, 試行: {attempt + 1}/{max_retries})')
                
                self.docs_service.documents().batchUpdate(
                    documentId=document_id,
                    body={
                        'requests': [{
                            'insertText': {
                                'location': {'index': index},
                                'text': text
                            }
                        }]
                    }
                ).execute()
                
                self.logger.debug(f'テキストチャンクの挿入に成功しました (サイズ: {len(text)}文字)')
                return
                
            except HttpError as e:
                error_msg = str(e)
                error_details = ''
                if hasattr(e, 'error_details'):
                    error_details = str(e.error_details)
                elif hasattr(e, 'content'):
                    try:
                        import json
                        error_content = json.loads(e.content.decode('utf-8'))
                        error_details = str(error_content)
                    except:
                        error_details = str(e.content)
                
                self.logger.error(f'Google Docs APIエラー (試行 {attempt + 1}/{max_retries}): {error_msg}')
                if error_details:
                    self.logger.error(f'エラー詳細: {error_details}')
                self.logger.error(f'テキストサイズ: {len(text)}文字, 挿入位置: {index}')
                self.logger.error(f'テキストの最初の100文字: {text[:100]}')
                
                if e.resp.status == 500:
                    if attempt < max_retries - 1:
                        # 500エラーの場合はリトライ
                        wait_time = (attempt + 1) * 2  # 2秒、4秒、6秒と待機時間を増やす
                        self.logger.warning(f'500エラーが発生しました。{wait_time}秒後にリトライします')
                        time.sleep(wait_time)
                        
                        # テキストが大きすぎる可能性があるので、さらに小さく分割
                        if len(text) > 500:
                            self.logger.warning('テキストが大きすぎる可能性があります。さらに分割します。')
                            # 段落単位で分割を試みる
                            paragraphs = text.split('\n\n')
                            if len(paragraphs) > 1:
                                current_chunk = []
                                current_size = 0
                                current_index = index
                                
                                for para in paragraphs:
                                    para_with_sep = para + '\n\n'
                                    para_size = len(para_with_sep)
                                    
                                    if current_size + para_size > 3000 and current_chunk:
                                        chunk_text = '\n\n'.join(current_chunk)
                                        self._insert_text_chunk(document_id, chunk_text, current_index, 1)
                                        current_index = self._get_document_length(document_id)
                                        time.sleep(0.5)
                                        current_chunk = []
                                        current_size = 0
                                    
                                    current_chunk.append(para)
                                    current_size += para_size
                                
                                if current_chunk:
                                    chunk_text = '\n\n'.join(current_chunk)
                                    self._insert_text_chunk(document_id, chunk_text, current_index, 1)
                                return
                            else:
                                # 段落がない場合は改行位置で分割
                                mid_point = len(text) // 2
                                split_pos = text.rfind('\n', 0, mid_point)
                                if split_pos == -1:
                                    split_pos = mid_point
                                
                                first_half = text[:split_pos + 1]
                                second_half = text[split_pos + 1:]
                                
                                self._insert_text_chunk(document_id, first_half, index, 1)
                                next_index = self._get_document_length(document_id)
                                time.sleep(0.5)
                                self._insert_text_chunk(document_id, second_half, next_index, 1)
                                return
                        continue
                    else:
                        self.logger.error(f'500エラーが{max_retries}回続きました。テキストサイズ: {len(text)}文字')
                        raise
                else:
                    # 500以外のエラーは即座に再スロー
                    raise
                    
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f'予期しないエラー (試行 {attempt + 1}/{max_retries}): {error_msg}')
                
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    self.logger.warning(f'{wait_time}秒後にリトライします')
                    time.sleep(wait_time)
                    continue
                else:
                    raise
    
    def _get_document_length(self, document_id: str) -> int:
        """ドキュメントの現在の長さ（文字数）を取得"""
        try:
            doc = self.docs_service.documents().get(documentId=document_id).execute()
            # ドキュメントのbodyのendIndexを取得（これがドキュメントの現在の長さ）
            body = doc.get('body', {})
            # bodyのendIndexが直接取得できない場合は、contentの最後の要素から取得
            content = body.get('content', [])
            if content:
                # 最後の要素のendIndexを取得
                last_element = content[-1]
                # 段落の場合
                if 'paragraph' in last_element:
                    paragraph = last_element['paragraph']
                    elements = paragraph.get('elements', [])
                    if elements:
                        return elements[-1].get('endIndex', 1)
                    else:
                        # 要素がない場合は段落のendIndexを取得
                        return paragraph.get('endIndex', 1)
                # その他の要素タイプ
                else:
                    # 一般的なendIndexを取得
                    for key in ['endIndex', 'table', 'sectionBreak']:
                        if key in last_element:
                            if key == 'endIndex':
                                return last_element[key]
                            # テーブルやセクションブレークの場合は、その中の最後の要素を確認
                            break
            # デフォルト値（空のドキュメントは1から始まる）
            return 1
        except Exception as e:
            self.logger.warning(f'ドキュメントの長さを取得できませんでした: {str(e)}')
            # エラー時は安全のため、現在の位置を1として返す（最初からやり直し）
            return 1
    
    def _insert_text_line_by_line(self, document_id: str, lines: list, checkbox_line_indices: list):
        """テキストを1行ずつ挿入（最も安全な方法）"""
        import time
        
        # 最初の挿入位置を取得（ドキュメントの現在の長さ）
        try:
            current_index = self._get_document_length(document_id)
            self.logger.info(f'ドキュメントの現在の長さ: {current_index}')
        except Exception as e:
            self.logger.warning(f'ドキュメントの長さを取得できませんでした: {str(e)}。デフォルト値1を使用します')
            current_index = 1
        
        failed_lines = []  # 失敗した行を記録
        
        self.logger.info(f'{len(lines)}行のテキストを1行ずつ挿入します')
        self.logger.info(f'最初の5行の内容: {[repr(line[:30]) for line in lines[:5]]}')
        
        for i, line in enumerate(lines):
            self.logger.info(f'=== 行 {i+1}/{len(lines)} の処理を開始 ===')
            
            # チェックリスト項目の場合は「□」を削除
            if i in checkbox_line_indices:
                original_line = line
                line = line.replace('□', '', 1).strip()
                self.logger.info(f'行 {i+1}: チェックリスト項目として処理 (元: {repr(original_line[:30])}, 処理後: {repr(line[:30])})')
            
            # 行の最後に改行を追加（最後の行以外）
            if i < len(lines) - 1:
                line_with_newline = line + '\n'
            else:
                line_with_newline = line
            
            # 空行の場合は改行のみ
            if not line.strip():
                line_with_newline = '\n'
                self.logger.info(f'行 {i+1}: 空行を挿入します')
            else:
                self.logger.info(f'行 {i+1}: 内容={repr(line[:100])} (長さ: {len(line)}文字)')
            
            # すべての行を小さなチャンク（5文字）に分割して挿入（最も安全な方法）
            # これにより、問題のある文字が含まれていても影響を最小限に抑える
            CHUNK_SIZE = 5  # 非常に小さなチャンクサイズ（さらに削減）
            
            if len(line_with_newline) > CHUNK_SIZE:
                # 行を20文字ごとに分割
                chunks = [line_with_newline[j:j+CHUNK_SIZE] for j in range(0, len(line_with_newline), CHUNK_SIZE)]
                self.logger.debug(f'行 {i+1}を{len(chunks)}個のチャンクに分割します (総文字数: {len(line_with_newline)})')
                for chunk_idx, chunk in enumerate(chunks):
                    try:
                        current_index = self._get_document_length(document_id)
                        self.logger.info(f'行 {i+1}のチャンク {chunk_idx+1}/{len(chunks)}を挿入します (位置: {current_index}, 内容: {repr(chunk)})')
                        self._insert_single_chunk_safe(document_id, chunk, current_index, i+1, chunk_idx+1, len(chunks))
                        self.logger.info(f'行 {i+1}のチャンク {chunk_idx+1}/{len(chunks)}の挿入に成功しました')
                        time.sleep(0.5)  # 各チャンクの間に待機時間を増やす
                    except Exception as e:
                        self.logger.error(f'チャンクの挿入に失敗しました (行 {i+1}, チャンク {chunk_idx+1}/{len(chunks)}): {str(e)}')
                        self.logger.error(f'失敗したチャンク: {repr(chunk)}')
                        self.logger.error(f'チャンクのバイト表現: {chunk.encode("utf-8", errors="replace")}')
                        import traceback
                        self.logger.error(f'トレースバック: {traceback.format_exc()}')
                        # エラーが発生したチャンクをスキップして続行（フォールバック）
                        self.logger.warning(f'チャンクをスキップして続行します')
                        failed_lines.append(i+1)
                        continue
            else:
                # 短い行はそのまま挿入
                try:
                    current_index = self._get_document_length(document_id)
                    self.logger.info(f'行 {i+1}を挿入します (位置: {current_index}, サイズ: {len(line_with_newline)}文字, 内容: {repr(line_with_newline[:100])})')
                    self._insert_single_chunk_safe(document_id, line_with_newline, current_index, i+1, 1, 1)
                    self.logger.info(f'行 {i+1}の挿入に成功しました')
                    time.sleep(0.5)  # 各行の間に待機時間を増やす
                except Exception as e:
                    self.logger.error(f'行の挿入に失敗しました (行 {i+1}): {str(e)}')
                    self.logger.error(f'失敗した行: {repr(line_with_newline)}')
                    self.logger.error(f'行のバイト表現: {line_with_newline.encode("utf-8", errors="replace")}')
                    import traceback
                    self.logger.error(f'トレースバック: {traceback.format_exc()}')
                    # エラーが発生した行をスキップして続行（フォールバック）
                    self.logger.warning(f'行をスキップして続行します')
                    failed_lines.append(i+1)
                    continue
        
        if failed_lines:
            self.logger.warning(f'一部の行の挿入に失敗しました: {failed_lines}')
        else:
            self.logger.info('すべての行を挿入しました')
        
        # チェックリスト形式を適用
        if checkbox_line_indices:
            try:
                self._apply_checklist_format(document_id, checkbox_line_indices)
            except Exception as e:
                self.logger.warning(f'チェックリスト形式の適用に失敗しました: {str(e)}')
        
        return failed_lines
    
    def _create_document_via_drive(self, document_id: str, content: str, title: str):
        """Drive APIを使ってテキストファイルをアップロードしてからGoogle Documentに変換（代替方法）"""
        import io
        import time
        from googleapiclient.http import MediaIoBaseUpload
        
        self.logger.info('Drive APIを使用してドキュメントを作成します')
        self.logger.info(f'コンテンツサイズ: {len(content)} 文字')
        
        try:
            # テキストをクリーニング
            content = self._clean_text(content)
            self.logger.info(f'クリーニング後のコンテンツサイズ: {len(content)} 文字')
            
            # テキストファイルをメモリ上に作成
            text_bytes = content.encode('utf-8')
            text_file = io.BytesIO(text_bytes)
            
            # Drive APIでテキストファイルをアップロード
            file_metadata = {
                'name': f'{title}.txt',
                'mimeType': 'text/plain'
            }
            
            media = MediaIoBaseUpload(
                text_file,
                mimetype='text/plain',
                resumable=True
            )
            
            self.logger.info('テキストファイルをアップロードします')
            uploaded_file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            uploaded_file_id = uploaded_file.get('id')
            self.logger.info(f'テキストファイルをアップロードしました (ID: {uploaded_file_id})')
            
            # 少し待機（アップロードの完了を待つ）
            time.sleep(1)
            
            # テキストファイルをGoogle Documentに変換
            # files().updateではMIMEタイプを変更できないため、
            # テキストファイルの内容を読み込んで、新しいGoogle Documentを作成する
            self.logger.info('テキストファイルをGoogle Documentに変換します')
            
            # テキストファイルの内容を読み込む
            try:
                downloaded_file = self.drive_service.files().get_media(fileId=uploaded_file_id).execute()
                text_content = downloaded_file.decode('utf-8')
                self.logger.info(f'テキストファイルの内容を読み込みました ({len(text_content)} 文字)')
            except Exception as e:
                self.logger.error(f'テキストファイルの読み込みに失敗しました: {str(e)}')
                raise
            
            # 新しいGoogle Documentを作成
            try:
                new_document = self.docs_service.documents().create(
                    body={'title': title}
                ).execute()
                new_document_id = new_document.get('documentId')
                self.logger.info(f'新しいGoogle Documentを作成しました (ID: {new_document_id})')
                
                # 少し待機（ドキュメントの準備を待つ）
                time.sleep(2)
                
                # テキストを挿入（非常に小さなチャンクで）
                # 500エラーを回避するため、1文字ずつ挿入する方法を試す
                self.logger.info('テキストをドキュメントに挿入します')
                self._insert_text_safely(new_document_id, text_content)
                
            except Exception as e:
                self.logger.error(f'Google Documentの作成に失敗しました: {str(e)}')
                raise
            finally:
                # 元のテキストファイルを削除
                try:
                    self.drive_service.files().delete(fileId=uploaded_file_id).execute()
                    self.logger.info('テキストファイルを削除しました')
                except Exception as e:
                    self.logger.warning(f'テキストファイルの削除に失敗しました: {str(e)}')
            
            # 元のドキュメントが指定されている場合は削除
            if document_id:
                try:
                    self.drive_service.files().delete(fileId=document_id).execute()
                    self.logger.info('元のドキュメントを削除しました')
                except Exception as e:
                    self.logger.warning(f'元のドキュメントの削除に失敗しました: {str(e)}')
            
            # 新しいドキュメントのIDを返す（呼び出し元で使用）
            return new_document_id
            
        except Exception as e:
            self.logger.error(f'Drive APIを使用した方法が失敗しました: {str(e)}')
            import traceback
            self.logger.error(f'トレースバック: {traceback.format_exc()}')
            raise
    
    def _insert_text_safely(self, document_id: str, content: str):
        """テキストを安全に挿入（非常に小さなチャンクで挿入する方法）"""
        import time
        
        self.logger.info(f'テキストを安全に挿入します (サイズ: {len(content)} 文字)')
        
        # テキストをクリーニング
        content = self._clean_text(content)
        
        if not content or not content.strip():
            self.logger.warning('クリーニング後のテキストが空です')
            return
        
        # 行単位で挿入
        lines = content.split('\n')
        current_index = 1
        failed_lines = []
        
        self.logger.info(f'{len(lines)}行を挿入します')
        
        for i, line in enumerate(lines):
            # 行の最後に改行を追加（最後の行以外）
            if i < len(lines) - 1:
                line_with_newline = line + '\n'
            else:
                line_with_newline = line
            
            # 空行の場合は改行のみ
            if not line.strip():
                line_with_newline = '\n'
            
            # 長い行はさらに小さなチャンクに分割（100文字ずつ）
            max_chunk_size = 100
            if len(line_with_newline) > max_chunk_size:
                chunks = [line_with_newline[j:j+max_chunk_size] for j in range(0, len(line_with_newline), max_chunk_size)]
            else:
                chunks = [line_with_newline]
            
            for chunk_idx, chunk in enumerate(chunks):
                try:
                    # 現在のドキュメントの長さを取得
                    try:
                        current_index = self._get_document_length(document_id)
                    except Exception as e:
                        self.logger.warning(f'ドキュメント長の取得に失敗しました: {str(e)}')
                        # デフォルト値を使用
                        if current_index < 1:
                            current_index = 1
                    
                    # チャンクをさらにクリーニング（念のため）
                    chunk = self._clean_text(chunk)
                    if not chunk:
                        continue
                    
                    # リクエストを送信
                    self.docs_service.documents().batchUpdate(
                        documentId=document_id,
                        body={
                            'requests': [{
                                'insertText': {
                                    'location': {'index': current_index},
                                    'text': chunk
                                }
                            }]
                        }
                    ).execute()
                    
                    # 各チャンクの後に少し待機
                    time.sleep(0.1)
                    
                except HttpError as e:
                    if e.resp.status == 500:
                        self.logger.error(f'500エラーが発生しました (行 {i+1}, チャンク {chunk_idx+1}/{len(chunks)}, 内容: {repr(chunk[:50])})')
                        self.logger.error(f'エラー詳細: {str(e)}')
                        # エラーが発生したチャンクをスキップして続行
                        failed_lines.append((i+1, chunk_idx+1))
                        continue
                    else:
                        self.logger.error(f'HTTPエラーが発生しました (ステータス: {e.resp.status}): {str(e)}')
                        raise
                except Exception as e:
                    self.logger.error(f'エラーが発生しました (行 {i+1}, チャンク {chunk_idx+1}/{len(chunks)}, 内容: {repr(chunk[:50])}): {str(e)}')
                    import traceback
                    self.logger.error(f'トレースバック: {traceback.format_exc()}')
                    # エラーが発生したチャンクをスキップして続行
                    failed_lines.append((i+1, chunk_idx+1))
                    continue
            
            # 5行ごとに少し待機
            if (i + 1) % 5 == 0:
                time.sleep(0.3)
        
        if failed_lines:
            self.logger.warning(f'{len(failed_lines)}個のチャンクの挿入に失敗しました')
        else:
            self.logger.info('すべてのテキストの挿入が完了しました')
    
    def _insert_single_chunk_safe(self, document_id: str, text: str, index: int, line_num: int = 0, chunk_num: int = 0, total_chunks: int = 0):
        """単一のチャンクを挿入（安全な方法、エラー時はスキップ可能）"""
        import time
        import json
        
        # テキストが空の場合はスキップ
        if not text:
            self.logger.warning(f'空のテキストをスキップします (行 {line_num}, チャンク {chunk_num})')
            return
        
        # テキストをさらにクリーニング（念のため）
        original_text = text
        text = self._clean_text(text)
        if not text:
            self.logger.warning(f'クリーニング後にテキストが空になりました (行 {line_num}, チャンク {chunk_num})')
            return
        
        # クリーニングで変更があった場合はログに記録
        if original_text != text:
            self.logger.info(f'テキストがクリーニングされました (行 {line_num}, チャンク {chunk_num}): {repr(original_text[:30])} -> {repr(text[:30])}')
        
        # indexが1未満の場合は修正
        if index < 1:
            self.logger.warning(f'無効なindex ({index})を1に修正します (行 {line_num}, チャンク {chunk_num})')
            index = 1
        
        max_retries = 2  # リトライ回数を減らす（2回）
        
        for attempt in range(max_retries):
            try:
                # リクエストボディを構築
                request_body = {
                    'requests': [{
                        'insertText': {
                            'location': {'index': index},
                            'text': text
                        }
                    }]
                }
                
                # リクエストボディのサイズをチェック
                request_size = len(json.dumps(request_body, ensure_ascii=False))
                self.logger.info(f'リクエストを送信します (行 {line_num}, チャンク {chunk_num}/{total_chunks}, 試行 {attempt + 1}/{max_retries}, 位置: {index}, サイズ: {len(text)}文字, リクエストサイズ: {request_size}バイト)')
                self.logger.info(f'挿入するテキスト: {repr(text)}')
                
                self.docs_service.documents().batchUpdate(
                    documentId=document_id,
                    body=request_body
                ).execute()
                
                self.logger.info(f'挿入に成功しました (行 {line_num}, チャンク {chunk_num}/{total_chunks})')
                return  # 成功
                
            except HttpError as e:
                error_info = {
                    'status': e.resp.status,
                    'reason': e.resp.reason if hasattr(e.resp, 'reason') else 'Unknown',
                    'url': e.uri if hasattr(e, 'uri') else 'Unknown'
                }
                
                # エラー詳細を取得
                error_details = ''
                if hasattr(e, 'content'):
                    try:
                        error_content = json.loads(e.content.decode('utf-8'))
                        error_details = json.dumps(error_content, ensure_ascii=False, indent=2)
                    except:
                        error_details = str(e.content)
                
                self.logger.error(f'Google Docs APIエラー (行 {line_num}, チャンク {chunk_num}/{total_chunks}, 試行 {attempt + 1}/{max_retries}):')
                self.logger.error(f'  ステータス: {error_info["status"]}')
                self.logger.error(f'  理由: {error_info["reason"]}')
                self.logger.error(f'  テキストサイズ: {len(text)}文字')
                self.logger.error(f'  挿入位置: {index}')
                self.logger.error(f'  テキスト内容: {repr(text)}')
                self.logger.error(f'  テキストのバイト表現: {text.encode("utf-8", errors="replace")}')
                if error_details:
                    self.logger.error(f'  エラー詳細: {error_details}')
                
                if e.resp.status == 500:
                    if attempt < max_retries - 1:
                        wait_time = 2  # 2秒待機
                        self.logger.warning(f'500エラーが発生しました。{wait_time}秒後にリトライします')
                        time.sleep(wait_time)
                        
                        # ドキュメントの状態を再確認
                        try:
                            current_length = self._get_document_length(document_id)
                            self.logger.info(f'ドキュメントの現在の長さ: {current_length} (期待値: {index})')
                            if current_length != index:
                                self.logger.warning(f'挿入位置が一致しません。{index} -> {current_length}に修正します')
                                index = current_length
                        except Exception as check_error:
                            self.logger.warning(f'ドキュメントの状態確認に失敗: {str(check_error)}')
                        
                        continue
                    else:
                        # 最終的なエラー
                        self.logger.error(f'500エラーが{max_retries}回続きました (行 {line_num}, チャンク {chunk_num})')
                        self.logger.error(f'テキスト: {repr(text)}')
                        self.logger.error(f'テキストのバイト表現: {text.encode("utf-8", errors="replace")}')
                        raise
                else:
                    # 500以外のエラーは即座に再スロー
                    raise
                    
            except Exception as e:
                self.logger.error(f'予期しないエラー (行 {line_num}, チャンク {chunk_num}, 試行 {attempt + 1}/{max_retries}): {str(e)}')
                self.logger.error(f'テキスト: {repr(text)}')
                import traceback
                self.logger.error(f'トレースバック: {traceback.format_exc()}')
                
                if attempt < max_retries - 1:
                    wait_time = 2
                    self.logger.warning(f'{wait_time}秒後にリトライします')
                    time.sleep(wait_time)
                    continue
                else:
                    raise
    
    def _insert_single_chunk(self, document_id: str, text: str, index: int):
        """単一のチャンクを挿入（エラーハンドリング付き）"""
        import time
        import json
        max_retries = 3
        
        # テキストの詳細情報をログに記録
        text_repr = repr(text[:200])  # 最初の200文字をrepr形式で表示
        self.logger.debug(f'挿入を試みます: index={index}, サイズ={len(text)}文字, テキスト={text_repr}')
        
        # テキストが空の場合はスキップ
        if not text:
            self.logger.warning('空のテキストをスキップします')
            return
        
        # indexが1未満の場合は修正
        if index < 1:
            self.logger.warning(f'無効なindex ({index})を1に修正します')
            index = 1
        
        for attempt in range(max_retries):
            try:
                # リクエストボディを構築
                request_body = {
                    'requests': [{
                        'insertText': {
                            'location': {'index': index},
                            'text': text
                        }
                    }]
                }
                
                # リクエストボディのサイズをチェック
                request_size = len(json.dumps(request_body))
                if request_size > 100000:  # 100KB以上の場合
                    self.logger.warning(f'リクエストボディが大きすぎます ({request_size}バイト)')
                
                self.docs_service.documents().batchUpdate(
                    documentId=document_id,
                    body=request_body
                ).execute()
                
                self.logger.debug(f'挿入成功: index={index}, サイズ={len(text)}文字')
                return
                
            except HttpError as e:
                error_info = {
                    'status': e.resp.status,
                    'reason': e.resp.reason if hasattr(e.resp, 'reason') else 'Unknown',
                    'url': e.uri if hasattr(e, 'uri') else 'Unknown'
                }
                
                # エラー詳細を取得
                error_details = ''
                if hasattr(e, 'content'):
                    try:
                        error_content = json.loads(e.content.decode('utf-8'))
                        error_details = json.dumps(error_content, ensure_ascii=False, indent=2)
                    except:
                        error_details = str(e.content)
                
                self.logger.error(f'Google Docs APIエラー (試行 {attempt + 1}/{max_retries}):')
                self.logger.error(f'  ステータス: {error_info["status"]}')
                self.logger.error(f'  理由: {error_info["reason"]}')
                self.logger.error(f'  テキストサイズ: {len(text)}文字')
                self.logger.error(f'  挿入位置: {index}')
                self.logger.error(f'  テキスト内容: {text_repr}')
                if error_details:
                    self.logger.error(f'  エラー詳細: {error_details}')
                
                if e.resp.status == 500:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # 2秒、4秒、6秒
                        self.logger.warning(f'500エラーが発生しました。{wait_time}秒後にリトライします')
                        
                        # ドキュメントの状態を再確認
                        try:
                            current_length = self._get_document_length(document_id)
                            self.logger.info(f'ドキュメントの現在の長さ: {current_length}')
                            if current_length != index:
                                self.logger.warning(f'挿入位置が一致しません。期待: {index}, 実際: {current_length}')
                                index = current_length  # 位置を修正
                        except Exception as check_error:
                            self.logger.warning(f'ドキュメントの状態確認に失敗: {str(check_error)}')
                        
                        time.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f'500エラーが{max_retries}回続きました。')
                        self.logger.error(f'テキスト: {text[:100]}...')
                        self.logger.error(f'挿入位置: {index}')
                        raise
                else:
                    # 500以外のエラーは即座に再スロー
                    raise
                    
            except Exception as e:
                self.logger.error(f'予期しないエラー (試行 {attempt + 1}/{max_retries}): {str(e)}')
                self.logger.error(f'テキスト: {text_repr}')
                self.logger.error(f'挿入位置: {index}')
                
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    self.logger.warning(f'{wait_time}秒後にリトライします')
                    time.sleep(wait_time)
                    continue
                else:
                    raise
    
    def _insert_text_in_paragraphs(self, document_id: str, text: str, max_chunk_size: int):
        """テキストを段落単位で挿入（より安全な方法）"""
        import time
        
        # テキストを行ごとに分割
        lines = text.split('\n')
        current_index = 1  # 最初の挿入位置
        
        # 空行で区切られた段落を検出
        paragraphs = []
        current_paragraph = []
        
        for line in lines:
            if line.strip() == '':
                # 空行が見つかったら、現在の段落を保存
                if current_paragraph:
                    paragraphs.append('\n'.join(current_paragraph))
                    current_paragraph = []
                # 空行も段落として追加
                paragraphs.append('')
            else:
                current_paragraph.append(line)
        
        # 最後の段落を追加
        if current_paragraph:
            paragraphs.append('\n'.join(current_paragraph))
        
        self.logger.info(f'テキストを{len(paragraphs)}個の段落に分割しました')
        
        # 各段落を挿入
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip() and i > 0:
                # 空行の場合は改行のみを挿入
                try:
                    current_index = self._get_document_length(document_id)
                    self._insert_text_chunk(document_id, '\n', current_index, max_retries=1)
                    time.sleep(0.2)  # 短い待機時間
                except Exception as e:
                    self.logger.warning(f'空行の挿入に失敗しました: {str(e)}')
                    # 空行の挿入失敗は無視して続行
            else:
                # 段落が大きすぎる場合は分割
                if len(paragraph) > max_chunk_size:
                    # 段落を行単位で分割
                    para_lines = paragraph.split('\n')
                    current_chunk = []
                    current_chunk_size = 0
                    
                    for line in para_lines:
                        line_with_newline = line + '\n'
                        line_size = len(line_with_newline)
                        
                        if current_chunk_size + line_size > max_chunk_size and current_chunk:
                            chunk_text = '\n'.join(current_chunk)
                            try:
                                current_index = self._get_document_length(document_id)
                                self._insert_text_chunk(document_id, chunk_text, current_index, max_retries=2)
                                time.sleep(0.3)
                            except Exception as e:
                                self.logger.error(f'チャンクの挿入に失敗しました: {str(e)}')
                                raise
                            
                            current_chunk = []
                            current_chunk_size = 0
                        
                        current_chunk.append(line)
                        current_chunk_size += line_size
                    
                    # 残りのチャンクを挿入
                    if current_chunk:
                        chunk_text = '\n'.join(current_chunk)
                        try:
                            current_index = self._get_document_length(document_id)
                            self._insert_text_chunk(document_id, chunk_text, current_index, max_retries=2)
                            time.sleep(0.3)
                        except Exception as e:
                            self.logger.error(f'チャンクの挿入に失敗しました: {str(e)}')
                            raise
                else:
                    # 段落が小さい場合はそのまま挿入
                    paragraph_with_newline = paragraph + '\n' if paragraph else '\n'
                    try:
                        current_index = self._get_document_length(document_id)
                        self._insert_text_chunk(document_id, paragraph_with_newline, current_index, max_retries=2)
                        time.sleep(0.3)  # 各段落の間に待機時間を設ける
                    except Exception as e:
                        self.logger.error(f'段落の挿入に失敗しました: {str(e)}')
                        raise
        
        self.logger.info('すべての段落を挿入しました')
    
    def _insert_text_in_chunks(self, document_id: str, text: str, chunk_size: int):
        """テキストをチャンクに分割して挿入"""
        import time
        
        # テキストを行単位で分割（改行を保持するため）
        lines = text.split('\n')
        current_chunk_lines = []
        current_chunk_size = 0
        
        for i, line in enumerate(lines):
            # 最後の行かどうかを判定
            is_last_line = (i == len(lines) - 1)
            # 改行を追加するかどうか（最後の行で、かつ元のテキストが改行で終わっていない場合は追加しない）
            add_newline = not is_last_line or text.endswith('\n')
            
            line_with_newline = line + '\n' if add_newline else line
            line_size = len(line_with_newline)
            
            # チャンクサイズを超える場合は、現在のチャンクを挿入
            if current_chunk_size + line_size > chunk_size and current_chunk_lines:
                chunk_text = ''.join(current_chunk_lines)
                if chunk_text:
                    # 現在のドキュメントの長さを取得して挿入位置を決定
                    current_index = self._get_document_length(document_id)
                    self.logger.info(f'チャンクを挿入します (サイズ: {len(chunk_text)}文字, 行数: {len(current_chunk_lines)})')
                    self._insert_text_chunk(document_id, chunk_text, current_index)
                    # 挿入後に少し待機（APIの負荷を軽減）
                    time.sleep(0.5)
                
                current_chunk_lines = []
                current_chunk_size = 0
            
            # 行がチャンクサイズより大きい場合は、行自体を分割
            if line_size > chunk_size:
                self.logger.warning(f'非常に長い行を検出しました ({line_size}文字)。分割します。')
                # 行を文字単位で分割（安全のため、chunk_sizeの80%に制限）
                safe_chunk_size = int(chunk_size * 0.8)
                char_chunks = [line[j:j+safe_chunk_size] for j in range(0, len(line), safe_chunk_size)]
                
                for j, char_chunk in enumerate(char_chunks):
                    # 最後のチャンクでない場合、または元の行の最後の場合は改行を追加
                    is_last_char_chunk = (j == len(char_chunks) - 1)
                    char_chunk_with_newline = char_chunk + '\n' if (is_last_char_chunk and add_newline) else char_chunk
                    char_chunk_size = len(char_chunk_with_newline)
                    
                    if current_chunk_size + char_chunk_size > chunk_size and current_chunk_lines:
                        chunk_text = ''.join(current_chunk_lines)
                        if chunk_text:
                            current_index = self._get_document_length(document_id)
                            self.logger.info(f'チャンクを挿入します (サイズ: {len(chunk_text)}文字)')
                            self._insert_text_chunk(document_id, chunk_text, current_index)
                            time.sleep(0.5)
                        
                        current_chunk_lines = []
                        current_chunk_size = 0
                    
                    current_chunk_lines.append(char_chunk_with_newline)
                    current_chunk_size += char_chunk_size
            else:
                current_chunk_lines.append(line_with_newline)
                current_chunk_size += line_size
        
        # 残りのチャンクを挿入
        if current_chunk_lines:
            chunk_text = ''.join(current_chunk_lines)
            if chunk_text:
                current_index = self._get_document_length(document_id)
                self.logger.info(f'最後のチャンクを挿入します (サイズ: {len(chunk_text)}文字, 行数: {len(current_chunk_lines)})')
                self._insert_text_chunk(document_id, chunk_text, current_index)
    
    def _apply_checklist_format(self, document_id: str, checkbox_line_indices: list):
        """チェックリスト形式を適用"""
        try:
            # ドキュメントを再取得して段落位置を確認
            doc = self.docs_service.documents().get(documentId=document_id).execute()
            
            checkbox_requests = []
            paragraph_index = 0
            
            for element in doc.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    paragraph = element['paragraph']
                    elements = paragraph.get('elements', [])
                    
                    if elements and paragraph_index in checkbox_line_indices:
                        # この段落をチェックリスト形式にする
                        start_index = elements[0].get('startIndex', 1)
                        end_index = elements[-1].get('endIndex', start_index + 1)
                        
                        checkbox_requests.append({
                            'createParagraphBullets': {
                                'range': {
                                    'startIndex': start_index,
                                    'endIndex': end_index
                                },
                                'bulletPreset': 'BULLET_CHECKBOX'
                            }
                        })
                    
                    paragraph_index += 1
            
            if checkbox_requests:
                try:
                    self.docs_service.documents().batchUpdate(
                        documentId=document_id,
                        body={'requests': checkbox_requests}
                    ).execute()
                    self.logger.debug(f'{len(checkbox_requests)}件のチェックリスト項目を追加しました')
                except Exception as e:
                    self.logger.warning(f'チェックリスト形式の適用に失敗しました（テキストは挿入されています）: {str(e)}')
        except Exception as e:
            self.logger.warning(f'チェックリスト形式の適用中にエラーが発生しました: {str(e)}')
            # チェックリスト形式の適用に失敗しても、テキストは挿入されているので続行
    
    def _move_to_folder(self, document_id: str, folder_id: str):
        """ドキュメントをフォルダに移動"""
        try:
            # まずフォルダが存在するか確認
            try:
                folder = self.drive_service.files().get(
                    fileId=folder_id,
                    fields='id, name, mimeType'
                ).execute()
                
                # フォルダであることを確認
                if folder.get('mimeType') != 'application/vnd.google-apps.folder':
                    self.logger.error(f'指定されたIDはフォルダではありません: {folder_id}')
                    return
                
                self.logger.info(f'フォルダを確認しました: {folder.get("name")} (ID: {folder_id})')
                
            except HttpError as e:
                if e.resp.status == 404:
                    self.logger.error(f'フォルダが見つかりません: {folder_id}')
                    self.logger.error('以下を確認してください:')
                    self.logger.error('1. フォルダIDが正しいか')
                    self.logger.error('2. OAuth認証アカウントがフォルダにアクセス権限を持っているか')
                    self.logger.error('3. フォルダが存在するか')
                    return
                else:
                    raise
            
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
            
            self.logger.info(f'ドキュメントをフォルダに移動しました: {folder.get("name")} (ID: {folder_id})')
            
        except HttpError as e:
            error_details = e.error_details if hasattr(e, 'error_details') else str(e)
            self.logger.error(f'フォルダへの移動に失敗しました: {str(e)}')
            self.logger.error(f'詳細: {error_details}')
            self.logger.warning('ドキュメントは作成されていますが、フォルダへの移動に失敗しました')
            # フォルダへの移動に失敗してもドキュメントは作成されているので、エラーは出さない
        except Exception as e:
            self.logger.error(f'フォルダへの移動中に予期しないエラーが発生しました: {str(e)}', exc_info=True)
            self.logger.warning('ドキュメントは作成されていますが、フォルダへの移動に失敗しました')

