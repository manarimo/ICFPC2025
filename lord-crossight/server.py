#!/usr/bin/env python3
"""
ICFP Contest 2025 Mock API Server
/register は実装しない（リクエストに従って）
"""

import json
import re
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from aedificium import Aedificium, create_random_aedificium

class IdStates:
    """各idの状態を管理するクラス"""
    
    def __init__(self):
        self.aedificium: Aedificium = None
        self.query_count: int = 0
    
    def set_aedificium(self, aedificium: Aedificium):
        """Aedificiumを設定し、query_countをリセットする"""
        self.aedificium = aedificium
        self.query_count = 0
    
    def get_aedificium(self) -> Aedificium:
        """Aedificiumを取得する"""
        return self.aedificium
    
    def get_query_count(self) -> int:
        """query_countを取得する"""
        return self.query_count
    
    def increment_query_count(self, increment: int) -> int:
        """query_countを増加させる"""
        self.query_count += increment
        return self.query_count
    
    def clear(self):
        """状態をクリアする"""
        self.aedificium = None
        self.query_count = 0


# id事に状態を管理するdefaultdict
# 各idに対してIdStatesオブジェクトを自動生成して保持
id_states = defaultdict(IdStates)


class ICFPMockServer(BaseHTTPRequestHandler):
    """ICFP Contest 2025のモックAPIサーバー"""
    
    def do_POST(self):
        """POSTリクエストの処理"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # リクエストボディを読み取り
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            try:
                request_data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self._send_error(400, "Invalid JSON")
                return
        else:
            request_data = {}
        
        # エンドポイントに応じて処理を分岐
        if path == '/select':
            self._handle_select(request_data)
        elif path == '/explore':
            self._handle_explore(request_data)
        elif path == '/guess':
            self._handle_guess(request_data)
        else:
            self._send_error(404, f"Endpoint not found: {path}")
    
    def _handle_select(self, request_data):
        """
        /select エンドポイントの処理
        問題を選択し、新しいランダムAedificiumを生成する
        """
        # リクエストの検証
        if 'id' not in request_data or 'problemName' not in request_data:
            self._send_error(400, "Missing required fields: id, problemName")
            return
        
        user_id = request_data['id']
        problem_name = request_data['problemName']
        
        # 新しいランダムAedificiumを生成

        new_aedificium = initialize_aedificium(problem_name=problem_name)
        id_states[user_id].set_aedificium(new_aedificium)
        
        print(f"Generated new Aedificium for user '{user_id}', problem '{problem_name}': {new_aedificium}")
        
        response = {
            "problemName": problem_name
        }
        
        self._send_json_response(200, response)
    
    def _handle_explore(self, request_data):
        """
        /explore エンドポイントの処理
        指定されたidのAedificiumを探索する
        """
        # リクエストの検証
        if 'id' not in request_data or 'plans' not in request_data:
            self._send_error(400, "Missing required fields: id, plans")
            return
        
        user_id = request_data['id']
        current_aedificium = id_states[user_id].get_aedificium()
        
        # Aedificiumが選択されているかチェック
        if current_aedificium is None:
            self._send_error(400, "No problem selected. Please call /select first.")
            return
        
        plans = request_data['plans']
        
        if not isinstance(plans, list):
            self._send_error(400, "plans must be a list")
            return
        
        # プラン数の制限チェック（18n doorways per night）
        total_plan_length = sum(len(plan) for plan in plans)
        max_length = 18 * len(current_aedificium.rooms)
        
        if total_plan_length > max_length:
            self._send_error(400, f"Total plan length ({total_plan_length}) exceeds limit ({max_length})")
            return
        
        # 各プランの検証
        for plan in plans:
            if not isinstance(plan, str):
                self._send_error(400, "Each plan must be a string")
                return
            
            # プラン文字列の検証（0-5の数字のみ）
            if not all(c in '012345' for c in plan):
                self._send_error(400, "Plan must contain only digits 0-5")
                return
        
        # 実際のAedificiumを使用して探索を実行
        exploration_result = current_aedificium.explore(plans)
        
        # クエリカウントを更新（プラン数 + リクエストペナルティ1）
        new_query_count = id_states[user_id].increment_query_count(len(plans) + 1)
        
        print(f"User '{user_id}': Explored with {len(plans)} plans, total query count: {new_query_count}")
        
        response = {
            "results": exploration_result["results"],
            "queryCount": new_query_count
        }
        
        self._send_json_response(200, response)
    
    def _handle_guess(self, request_data):
        """
        /guess エンドポイントの処理
        候補マップを提出し、指定されたidのAedificiumと比較する
        """
        # リクエストの検証
        if 'id' not in request_data or 'map' not in request_data:
            self._send_error(400, "Missing required fields: id, map")
            return
        
        user_id = request_data['id']
        current_aedificium = id_states[user_id].get_aedificium()
        
        # Aedificiumが選択されているかチェック
        if current_aedificium is None:
            self._send_error(400, "No problem selected. Please call /select first.")
            return
        
        map_data = request_data['map']
        
        # マップデータの基本的な構造チェック
        required_map_fields = ['rooms', 'startingRoom', 'connections']
        for field in required_map_fields:
            if field not in map_data:
                self._send_error(400, f"Missing required map field: {field}")
                return
        
        try:
            # 提出されたマップからAedificiumオブジェクトを作成
            submitted_aedificium = Aedificium.from_dict(map_data)
            
            # 現在のAedificiumと等価性を詳細にテスト
            failure_reason = current_aedificium.equivalence_test(submitted_aedificium)
            is_correct = failure_reason is None
            
            print(f"User '{user_id}': Map guess submitted. Correct: {is_correct}")
            if not is_correct:
                print(f"Failure reason: {failure_reason}")
            print(f"Current Aedificium: {current_aedificium}")
            print(f"Submitted Aedificium: {submitted_aedificium}")
            
            response = {
                "correct": is_correct
            }
            
            # 失敗した場合は理由を追加
            if not is_correct:
                response["reason"] = failure_reason
            
            # 仕様に従い、guess後は問題を非選択状態にする
            id_states[user_id].clear()
            
            self._send_json_response(200, response)
            
        except Exception as e:
            print(f"Error processing guess: {e}")
            self._send_error(400, f"Invalid map data: {str(e)}")
            return
    
    def _send_json_response(self, status_code, data):
        """JSON形式のレスポンスを送信"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        json_data = json.dumps(data, ensure_ascii=False)
        self.wfile.write(json_data.encode('utf-8'))
    
    def _send_error(self, status_code, message):
        """エラーレスポンスを送信"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        error_data = {"error": message}
        json_data = json.dumps(error_data, ensure_ascii=False)
        self.wfile.write(json_data.encode('utf-8'))
    
    def log_message(self, format, *args):
        """ログメッセージをカスタマイズ"""
        print(f"[{self.address_string()}] {format % args}")


def initialize_aedificium(problem_name: str) -> Aedificium:
    """
    問題名に応じてAedificiumを生成する
    """
    public_names = {
        "probatio": 3,
        "primus": 6,
        "secundus": 12,
        "tertius": 18,
        "quartus": 24,
        "quintus": 30,
    }
    if problem_name in public_names:
        return create_random_aedificium(num_rooms=public_names[problem_name])

    # if problem_name matches "random_room_size_{int}", return a random Aedificium with the given number of rooms
    if re.match(r"random_room_size_\d+", problem_name):
        num_rooms = int(problem_name.replace("random_room_size_", ""))
        return create_random_aedificium(num_rooms=num_rooms)

    raise ValueError(f"Invalid problem name: {problem_name}")


def run_server(port=8000):
    """サーバーを起動"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, ICFPMockServer)
    
    print(f"Lord=Crossight: ICFP Contest 2025 Mock API Server starting on port {port}...")
    print(f"Available endpoints:")
    print(f"  POST http://localhost:{port}/select")
    print(f"  POST http://localhost:{port}/explore") 
    print(f"  POST http://localhost:{port}/guess")
    print("Press Ctrl+C to stop the server")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        httpd.server_close()


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8000))
    run_server(port)
