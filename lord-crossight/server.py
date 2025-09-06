#!/usr/bin/env python3
"""
ICFP Contest 2025 Mock API Server
/register は実装しない（リクエストに従って）
"""

import json
import re
import os
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from aedificium import Aedificium, create_random_aedificium, parse_plan, Action

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
    
    def to_dict(self) -> dict:
        """状態を辞書形式にシリアライズする"""
        return {
            "aedificium": self.aedificium.to_dict() if self.aedificium else None,
            "query_count": self.query_count
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'IdStates':
        """辞書形式から状態を復元する"""
        instance = cls()
        instance.aedificium = Aedificium.from_dict(data["aedificium"]) if data["aedificium"] else None
        instance.query_count = data.get("query_count", 0)
        return instance


class PersistentStateManager:
    """永続化された状態を管理するクラス"""
    
    def __init__(self, persistence_dir: str = None):
        self.persistence_dir = persistence_dir
        self._states = defaultdict(IdStates)
        
        # 初期化時にディレクトリから既存の状態ファイルを読み込む
        if self.persistence_dir:
            self._load_existing_states()
    
    def __getitem__(self, user_id: str) -> IdStates:
        """指定されたユーザーIDの状態を取得する"""
        # まだメモリに読み込まれていない場合はファイルから読み込む
        if user_id not in self._states and self.persistence_dir:
            self._load_user_state(user_id)
        return self._states[user_id]
    
    def _get_user_file_path(self, user_id: str) -> str:
        """ユーザーIDに対応するファイルパスを取得する"""
        # ファイル名に使えない文字をエスケープ
        safe_user_id = user_id.replace('/', '_').replace('\\', '_').replace(':', '_')
        return os.path.join(self.persistence_dir, f"{safe_user_id}.json")
    
    def _load_existing_states(self):
        """ディレクトリから既存のユーザー状態ファイルを探して読み込む"""
        if not os.path.exists(self.persistence_dir):
            print(f"Persistence directory not found: {self.persistence_dir}. Starting with empty state.")
            return
        
        try:
            # ディレクトリ内のJSONファイルを検索
            json_files = [f for f in os.listdir(self.persistence_dir) if f.endswith('.json')]
            loaded_count = 0
            
            for filename in json_files:
                user_id = filename[:-5]  # .jsonを除去
                try:
                    self._load_user_state(user_id)
                    loaded_count += 1
                except Exception as e:
                    print(f"Error loading state for user {user_id}: {e}")
            
            print(f"Loaded {loaded_count} user states from {self.persistence_dir}")
        except Exception as e:
            print(f"Error scanning persistence directory {self.persistence_dir}: {e}")
            print("Starting with empty state.")
    
    def _load_user_state(self, user_id: str):
        """指定されたユーザーの状態をファイルから読み込む"""
        if not self.persistence_dir:
            return
        
        file_path = self._get_user_file_path(user_id)
        if not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            self._states[user_id] = IdStates.from_dict(state_data)
        except Exception as e:
            print(f"Error loading state for user {user_id} from {file_path}: {e}")
    
    def _save_user_state(self, user_id: str):
        """指定されたユーザーの状態をファイルに保存する"""
        if not self.persistence_dir:
            return
        
        try:
            # ディレクトリが存在しない場合は作成
            os.makedirs(self.persistence_dir, exist_ok=True)
            
            # ユーザーの状態をシリアライズ
            state_data = self._states[user_id].to_dict()
            
            # ユーザー専用ファイルに書き込み
            file_path = self._get_user_file_path(user_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"Error saving state for user {user_id}: {e}")
    
    def update_user_state(self, user_id: str):
        """ユーザー状態が更新された際に呼び出され、そのユーザーのファイルに保存する"""
        self._save_user_state(user_id)


# 永続化ディレクトリを環境変数から取得
PERSISTENCE_DIR = os.environ.get('ID_STATES_PERSISTENCE_PATH')

# id事に状態を管理するPersistentStateManager
# 各idに対してIdStatesオブジェクトを自動生成して保持し、更新時に個別ファイルに保存
id_states = PersistentStateManager(PERSISTENCE_DIR)


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
        elif path == '/spoiler':
            self._handle_spoiler(request_data)
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
        
        # 状態更新を永続化
        id_states.update_user_state(user_id)
        
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
        
        # プラン数の制限チェック（6n doorways per night）
        parsed_plans = [parse_plan(plan) for plan in plans]
        plan_lengths = [len([(move, arg) for move, arg in plan if move == Action.MOVE]) for plan in parsed_plans]
        max_length = 6 * len(current_aedificium.rooms)
        
        if max(plan_lengths) > max_length:
            self._send_error(400, f"max plan length ({max(plan_lengths)}) exceeds limit ({max_length})")
            return
        
        # 各プランの検証
        for plan in plans:
            if not isinstance(plan, str):
                self._send_error(400, "Each plan must be a string")
                return
            
            # プラン文字列の検証（0-5の数字のみ）
            if not all(c in '012345[]' for c in plan):
                self._send_error(400, "Plan must contain only digits 0-5 and []")
                return
        
        # 実際のAedificiumを使用して探索を実行
        exploration_result = current_aedificium.explore(plans)
        
        # クエリカウントを更新（プラン数 + リクエストペナルティ1）
        new_query_count = id_states[user_id].increment_query_count(len(plans) + 1)
        
        # 状態更新を永続化
        id_states.update_user_state(user_id)
        
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
            
            # 状態更新を永続化
            id_states.update_user_state(user_id)
            
            self._send_json_response(200, response)
            
        except Exception as e:
            print(f"Error processing guess: {e}")
            self._send_error(400, f"Invalid map data: {str(e)}")
            return

    def _handle_spoiler(self, request_data):
        """
        /spoiler エンドポイントの処理
        指定されたidの現在の正解（Aedificium）を返す
        """
        # リクエストの検証
        if 'id' not in request_data:
            self._send_error(400, "Missing required field: id")
            return

        user_id = request_data['id']
        current_aedificium = id_states[user_id].get_aedificium()

        # Aedificiumが選択されているかチェック
        if current_aedificium is None:
            self._send_error(400, "No problem selected. Please call /select first.")
            return

        response = {
            "map": current_aedificium.to_dict()
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

        "aleph": 12,
        "beth": 24,
        "gimel": 36,
        "daleth": 48,
        "he": 60,

        "vau": 18,
        "zain": 36,
        "hhet": 54,
        "teth": 72,
        "iod": 90,
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
    print(f"  POST http://localhost:{port}/spoiler")
    if PERSISTENCE_DIR:
        print(f"State persistence enabled: {PERSISTENCE_DIR} (separate file per user)")
    else:
        print("State persistence disabled (set ID_STATES_PERSISTENCE_PATH to enable)")
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
