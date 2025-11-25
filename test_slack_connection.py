#!/usr/bin/env python3
"""
Slack接続テストスクリプト
Bot Tokenとチャンネルの接続を確認
"""

import requests
import json
import sys
from pathlib import Path

def test_slack_connection():
    """Slack接続をテスト"""
    
    # 設定ファイルを読み込み
    config_path = Path('config/config.json')
    if not config_path.exists():
        print('❌ config/config.json が見つかりません')
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    bot_token = config.get('slack', {}).get('bot_token')
    channel = config.get('slack', {}).get('channel')
    
    if not bot_token:
        print('❌ Bot Tokenが設定されていません')
        return False
    
    if not channel:
        print('❌ チャンネルが設定されていません')
        return False
    
    print(f'📋 設定確認')
    print(f'  Bot Token: {bot_token[:20]}...')
    print(f'  チャンネル: {channel}')
    print()
    
    # 1. Bot情報を取得
    print('1️⃣ Bot情報を確認中...')
    url = 'https://slack.com/api/auth.test'
    headers = {
        'Authorization': f'Bearer {bot_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    result = response.json()
    
    if result.get('ok'):
        print(f'  ✅ Bot認証成功')
        print(f'  Bot User ID: {result.get("user_id")}')
        print(f'  ワークスペース: {result.get("team")}')
        print(f'  ユーザー名: {result.get("user")}')
    else:
        print(f'  ❌ Bot認証失敗: {result.get("error")}')
        return False
    
    print()
    
    # 2. チャンネル情報を取得（スコープが不足している場合はスキップ）
    print('2️⃣ チャンネル情報を確認中...')
    url = 'https://slack.com/api/conversations.info'
    params = {'channel': channel}
    
    response = requests.get(url, headers=headers, params=params)
    result = response.json()
    
    if result.get('ok'):
        channel_info = result.get('channel', {})
        print(f'  ✅ チャンネルが見つかりました')
        print(f'  チャンネル名: #{channel_info.get("name")}')
        print(f'  チャンネルID: {channel_info.get("id")}')
        print(f'  プライベート: {channel_info.get("is_private", False)}')
        print(f'  アーカイブ: {channel_info.get("is_archived", False)}')
        
        # Botがメンバーか確認
        members = channel_info.get('members', [])
        bot_user_id = result.get('user_id')
        if bot_user_id in members:
            print(f'  ✅ Botがチャンネルのメンバーです')
        else:
            print(f'  ❌ Botがチャンネルのメンバーではありません')
            print(f'  メンバー数: {len(members)}')
            print(f'  Bot User ID: {bot_user_id}')
            print(f'  メンバーリスト（最初の10人）: {members[:10]}')
            return False
    else:
        error = result.get('error')
        if error == 'missing_scope':
            print(f'  ⚠️  チャンネル情報の取得に必要なスコープが不足しています')
            print(f'  💡 これは問題ありません。投稿テストを続行します...')
        else:
            print(f'  ❌ チャンネル情報の取得に失敗: {error}')
            if error == 'channel_not_found':
                print(f'  💡 考えられる原因:')
                print(f'     - チャンネルIDが間違っている')
                print(f'     - チャンネルが削除されている')
                print(f'     - プライベートチャンネルで、Botが追加されていない')
                print(f'     - ワークスペースが違う')
    
    print()
    
    # 3. メッセージ投稿テスト（シンプルなtext）
    print('3️⃣ メッセージ投稿テスト（シンプルなtext）...')
    url = 'https://slack.com/api/chat.postMessage'
    payload = {
        'channel': channel,
        'text': '🧪 テストメッセージ: 接続テスト成功！'
    }
    
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    
    if result.get('ok'):
        print(f'  ✅ メッセージ投稿成功！')
        print(f'  メッセージTS: {result.get("ts")}')
    else:
        error = result.get('error')
        print(f'  ❌ メッセージ投稿失敗: {error}')
        
        if error == 'channel_not_found':
            print(f'  💡 チャンネルが見つかりません')
        elif error == 'not_in_channel':
            print(f'  💡 Botがチャンネルに参加していません')
        elif error == 'missing_scope':
            needed = result.get('needed')
            print(f'  💡 必要なスコープが不足しています: {needed}')
        
        return False
    
    print()
    
    # 4. メッセージ投稿テスト（blocks形式 - 実際のアプリと同じ形式）
    print('4️⃣ メッセージ投稿テスト（blocks形式）...')
    payload = {
        'channel': channel,
        'text': '📝 議事録が生成されました',
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': '*📝 議事録が生成されました*\n\n*ファイル名:* test.txt\n*日付:* 2025年11月24日\n*Document:* <https://docs.google.com/document/d/test|議事録を開く>'
                }
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    
    if result.get('ok'):
        print(f'  ✅ blocks形式のメッセージ投稿成功！')
        print(f'  メッセージTS: {result.get("ts")}')
        return True
    else:
        error = result.get('error')
        print(f'  ❌ blocks形式のメッセージ投稿失敗: {error}')
        print(f'  詳細: {json.dumps(result, indent=2, ensure_ascii=False)}')
        
        if error == 'channel_not_found':
            print(f'  💡 チャンネルが見つかりません（blocks形式で）')
        elif error == 'not_in_channel':
            print(f'  💡 Botがチャンネルに参加していません')
        elif error == 'missing_scope':
            needed = result.get('needed')
            print(f'  💡 必要なスコープが不足しています: {needed}')
        
        return False


if __name__ == '__main__':
    print('=' * 60)
    print('Slack接続テスト')
    print('=' * 60)
    print()
    
    success = test_slack_connection()
    
    print()
    print('=' * 60)
    if success:
        print('✅ すべてのテストが成功しました！')
        sys.exit(0)
    else:
        print('❌ テストに失敗しました。上記のエラーを確認してください。')
        sys.exit(1)

