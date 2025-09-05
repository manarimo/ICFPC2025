#!/usr/bin/env python3
"""
ICFP Contest 2025 Mock API Server
/register は実装しない（リクエストに従って）
"""

import json
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


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
        問題を選択する
        """
        # リクエストの検証
        if 'id' not in request_data or 'problemName' not in request_data:
            self._send_error(400, "Missing required fields: id, problemName")
            return
        
        problem_name = request_data['problemName']
        
        # モックレスポンス
        response = {
            "problemName": problem_name
        }
        
        self._send_json_response(200, response)
    
    def _handle_explore(self, request_data):
        """
        /explore エンドポイントの処理
        Ædificiumを探索する
        """
        # リクエストの検証
        if 'id' not in request_data or 'plans' not in request_data:
            self._send_error(400, "Missing required fields: id, plans")
            return
        
        plans = request_data['plans']
        
        if not isinstance(plans, list):
            self._send_error(400, "plans must be a list")
            return
        
        # 各プランに対してモックの結果を生成
        results = []
        for plan in plans:
            if not isinstance(plan, str):
                self._send_error(400, "Each plan must be a string")
                return
            
            # プランの長さ + 1の結果を生成（開始部屋 + 移動先部屋の数）
            plan_length = len(plan)
            result = []
            
            # 各部屋で0-3の2ビット整数をランダム生成
            for _ in range(plan_length + 1):
                result.append(random.randint(0, 3))
            
            results.append(result)
        
        # モックレスポンス
        response = {
            "results": results,
            "queryCount": random.randint(1, 100)  # モック用のクエリカウント
        }
        
        self._send_json_response(200, response)
    
    def _handle_guess(self, request_data):
        """
        /guess エンドポイントの処理
        候補マップを提出する
        """
        # リクエストの検証
        if 'id' not in request_data or 'map' not in request_data:
            self._send_error(400, "Missing required fields: id, map")
            return
        
        map_data = request_data['map']
        
        # マップデータの基本的な構造チェック
        required_map_fields = ['rooms', 'startingRoom', 'connections']
        for field in required_map_fields:
            if field not in map_data:
                self._send_error(400, f"Missing required map field: {field}")
                return
        
        # モックレスポンス（ランダムに正解/不正解を決定）
        response = {
            "correct": random.choice([True, False])
        }
        
        self._send_json_response(200, response)
    
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


def run_server(port=8000):
    """サーバーを起動"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, ICFPMockServer)
    
    print(f"ICFP Contest 2025 Mock API Server starting on port {port}...")
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
    run_server()
