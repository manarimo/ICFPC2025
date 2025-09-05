#!/usr/bin/env python3
"""
server.pyのテストスクリプト
サーバーを起動し、/select, /explore, /guessの一連のAPIテストを実行する
"""

import json
import time
import subprocess
import threading
from api import APIClient
from aedificium import Aedificium


def start_server():
    """サーバーをバックグラウンドで起動する"""
    print("=== サーバーを起動中... ===")
    process = subprocess.Popen(
        ["python3", "server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # サーバーが起動するまで少し待つ
    time.sleep(2)
    
    return process


def print_request_response(endpoint, request_data, response_data):
    """リクエストとレスポンスを整形して出力する"""
    print(f"\n--- {endpoint} ---")
    print(f"Request: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
    print(f"Response: {json.dumps(response_data, indent=2, ensure_ascii=False)}")


def test_api_sequence():
    """API呼び出しのテストシーケンスを実行する"""
    try:
        # APIクライアントを作成（ローカルサーバー用）
        client = APIClient(
            api_base="http://localhost:8000",
            api_id="test_id_12345"  # テスト用のID
        )
        
        print("=== APIテストシーケンス開始 ===")
        
        # 1. /select を呼び出す
        print("\n1. /select を呼び出します...")
        select_request = {
            "id": "test_id_12345",
            "problemName": "probatio"
        }
        
        try:
            select_response = client.select("probatio")
            print_request_response("/select", select_request, select_response)
        except Exception as e:
            print(f"Error in /select: {e}")
            return
        
        # 2. /explore を複数回呼び出す
        print("\n2. /explore を複数回呼び出します...")
        
        # 最初の探索: 単純なプラン
        explore_plans_1 = ["", "0", "1", "2"]
        explore_request_1 = {
            "id": "test_id_12345",
            "plans": explore_plans_1
        }
        
        try:
            explore_response_1 = client.explore(explore_plans_1)
            print_request_response("/explore (1回目)", explore_request_1, explore_response_1)
        except Exception as e:
            print(f"Error in /explore (1回目): {e}")
            return
        
        # 2回目の探索: より複雑なプラン
        explore_plans_2 = ["01", "12", "20", "012"]
        explore_request_2 = {
            "id": "test_id_12345",
            "plans": explore_plans_2
        }
        
        try:
            explore_response_2 = client.explore(explore_plans_2)
            print_request_response("/explore (2回目)", explore_request_2, explore_response_2)
        except Exception as e:
            print(f"Error in /explore (2回目): {e}")
            return
        
        # 3回目の探索: 長いプラン
        explore_plans_3 = ["0123", "4501"]
        explore_request_3 = {
            "id": "test_id_12345",
            "plans": explore_plans_3
        }
        
        try:
            explore_response_3 = client.explore(explore_plans_3)
            print_request_response("/explore (3回目)", explore_request_3, explore_response_3)
        except Exception as e:
            print(f"Error in /explore (3回目): {e}")
            return
        
        # 3. 探索結果から推測されるマップを作成
        print("\n3. 探索結果を分析してマップを推測します...")
        
        # 簡単な推測マップを作成（実際には探索結果を分析する必要がある）
        # ここでは "probatio" 問題用の3部屋マップを推測として作成
        guess_map = {
            "rooms": [0, 1, 2],  # 探索結果から推測した部屋ラベル
            "startingRoom": 0,   # 通常は0から開始
            "connections": [
                {"from": {"room": 0, "door": 0}, "to": {"room": 1, "door": 0}},
                {"from": {"room": 1, "door": 1}, "to": {"room": 2, "door": 0}},
                {"from": {"room": 2, "door": 1}, "to": {"room": 0, "door": 1}}
            ]
        }
        
        # 実際の探索結果を使ってより良い推測を作成
        print("探索結果を基に推測マップを作成中...")
        
        # 最初の探索結果から部屋数と開始部屋を推測
        first_results = explore_response_1["results"]
        if first_results:
            # 空のプランの結果から開始部屋のラベルを取得
            starting_room_label = first_results[0][0] if first_results[0] else 0
            
            # 他の結果から部屋ラベルを収集
            all_labels = set()
            for result in first_results:
                all_labels.update(result)
            
            # 推測マップを更新
            unique_labels = sorted(list(all_labels))
            guess_map["rooms"] = unique_labels
            
            print(f"推測された部屋ラベル: {unique_labels}")
            print(f"開始部屋ラベル: {starting_room_label}")
        
        # 4. /guess を呼び出す
        print("\n4. /guess を呼び出します...")
        guess_request = {
            "id": "test_id_12345",
            "map": guess_map
        }
        
        try:
            guess_response = client.guess(guess_map)
            print_request_response("/guess", guess_request, guess_response)
            
            if guess_response.get("correct", False):
                print("\n🎉 正解です！マップの推測が成功しました！")
            else:
                print("\n❌ 不正解でした。マップの推測に失敗しました。")
                
        except Exception as e:
            print(f"Error in /guess: {e}")
            return
        
        print("\n=== APIテストシーケンス完了 ===")
        
    except Exception as e:
        print(f"テスト中にエラーが発生しました: {e}")


def main():
    """メイン関数"""
    server_process = None
    
    try:
        # サーバーを起動
        server_process = start_server()
        
        # APIテストを実行
        test_api_sequence()
        
    except KeyboardInterrupt:
        print("\n\nテストが中断されました")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        
    finally:
        # サーバーを停止
        if server_process:
            print("\n=== サーバーを停止中... ===")
            server_process.terminate()
            
            # プロセスが終了するまで少し待つ
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("サーバーが正常に停止しませんでした。強制終了します...")
                server_process.kill()
            
            print("サーバーが停止しました")


if __name__ == "__main__":
    main()
