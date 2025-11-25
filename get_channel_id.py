#!/usr/bin/env python3
"""
SlackチャンネルIDを取得するスクリプト
"""

import requests
import json
import sys

def get_channel_id(bot_token, channel_name):
    """
    チャンネル名からチャンネルIDを取得
    
    Args:
        bot_token: Slack Bot Token
        channel_name: チャンネル名（#を含む、または含まない）
    """
    # # を削除
    if channel_name.startswith('#'):
        channel_name = channel_name[1:]
    
    url = 'https://slack.com/api/conversations.list'
    headers = {
        'Authorization': f'Bearer {bot_token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        'types': 'public_channel,private_channel',
        'limit': 1000
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        result = response.json()
        
        if not result.get('ok'):
            error = result.get('error', 'unknown')
            print(f'エラー: {error}')
            if error == 'missing_scope':
                print('\n必要なスコープが不足しています。')
                print('Slack Appの設定で以下のスコープを追加してください:')
                print('- channels:read (パブリックチャンネル)')
                print('- groups:read (プライベートチャンネル)')
            return None
        
        channels = result.get('channels', [])
        
        # チャンネル名で検索
        for channel in channels:
            if channel.get('name') == channel_name:
                channel_id = channel.get('id')
                print(f'\n✅ チャンネルが見つかりました！')
                print(f'チャンネル名: #{channel_name}')
                print(f'チャンネルID: {channel_id}')
                print(f'\nconfig.json に以下のように設定してください:')
                print(f'  "channel": "{channel_id}"')
                return channel_id
        
        # 見つからない場合
        print(f'\n❌ チャンネル "{channel_name}" が見つかりませんでした。')
        print('\n利用可能なチャンネル一覧:')
        for channel in channels[:20]:  # 最初の20件を表示
            print(f'  - #{channel.get("name")} (ID: {channel.get("id")})')
        
        if len(channels) > 20:
            print(f'  ... 他 {len(channels) - 20} 件')
        
        return None
        
    except Exception as e:
        print(f'エラーが発生しました: {str(e)}')
        return None


if __name__ == '__main__':
    # 設定ファイルから読み込み
    try:
        with open('config/config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        bot_token = config.get('slack', {}).get('bot_token')
        channel_name = config.get('slack', {}).get('channel', '#議事録')
        
        if not bot_token:
            print('エラー: config.json に slack.bot_token が設定されていません')
            sys.exit(1)
        
        print(f'Bot Token: {bot_token[:20]}...')
        print(f'検索するチャンネル: {channel_name}')
        print('\nチャンネルIDを取得中...')
        
        channel_id = get_channel_id(bot_token, channel_name)
        
        if channel_id:
            print('\n✅ 完了！')
        else:
            print('\n❌ チャンネルIDの取得に失敗しました。')
            sys.exit(1)
            
    except FileNotFoundError:
        print('エラー: config/config.json が見つかりません')
        sys.exit(1)
    except json.JSONDecodeError:
        print('エラー: config/config.json の形式が正しくありません')
        sys.exit(1)
    except Exception as e:
        print(f'エラー: {str(e)}')
        sys.exit(1)

