from typing import List, Dict, Any, Tuple
import json
import random


class Aedificium:
    """
    Ædificiumを表現するクラス
    六角形の部屋とドア（0-5番）で構成される迷宮を管理する
    """
    
    def __init__(self, rooms: List[int], starting_room: int, connections: List[Dict[str, Any]]):
        """
        Aedificiumを初期化する
        
        Args:
            rooms: 各部屋のラベル（2bitの整数）のリスト
            starting_room: 開始部屋のインデックス
            connections: 部屋間の接続情報のリスト
        """
        self.rooms = rooms
        self.starting_room = starting_room
        self.connections = connections
        
        # 効率的なルックアップのための接続マップを構築
        self._connection_map = self._build_connection_map()
    
    def _build_connection_map(self) -> Dict[Tuple[int, int], Tuple[int, int]]:
        """
        接続情報から効率的なルックアップマップを構築する
        
        Returns:
            (room_index, door_number) -> (destination_room, destination_door) のマッピング
        """
        connection_map = {}
        
        for conn in self.connections:
            from_room = conn['from']['room']
            from_door = conn['from']['door']
            to_room = conn['to']['room']
            to_door = conn['to']['door']
            
            # 双方向の接続を設定（undirected graph）
            connection_map[(from_room, from_door)] = (to_room, to_door)
            connection_map[(to_room, to_door)] = (from_room, from_door)
        
        return connection_map
    
    def explore(self, plans: List[str]) -> Dict[str, Any]:
        """
        /explore APIと同じ動作をするメソッド
        指定されたroute planに従って迷宮を探索し、各部屋のラベルを記録する
        
        Args:
            plans: route planのリスト（各planは"0123"のような文字列）
        
        Returns:
            results: 各planに対する探索結果（部屋のラベルのリスト）
            queryCount: 探索回数（planの数）
        """
        results = []
        
        for plan in plans:
            # 各planに対して探索を実行
            path_labels = self._execute_plan(plan)
            results.append(path_labels)
        
        return {
            "results": results,
            "queryCount": len(plans)
        }
    
    def _execute_plan(self, plan: str) -> List[int]:
        """
        単一のroute planを実行する
        
        Args:
            plan: route plan（"0123"のような文字列）
        
        Returns:
            訪問した部屋のラベルのリスト
        """
        current_room = self.starting_room
        labels = [self.rooms[current_room]]  # 開始部屋のラベルを記録
        
        for door_char in plan:
            door = int(door_char)
            
            # 現在の部屋から指定されたドアを通って次の部屋へ移動
            if (current_room, door) in self._connection_map:
                next_room, _ = self._connection_map[(current_room, door)]
                current_room = next_room
                labels.append(self.rooms[current_room])
            else:
                # 接続が存在しない場合は現在の部屋に留まる
                # （仕様によってはエラーを投げる場合もあるが、ここでは安全側に倒す）
                labels.append(self.rooms[current_room])
        
        return labels
    
    def to_dict(self) -> Dict[str, Any]:
        """
        /guess APIで使用される形式のJSONに変換する
        
        Returns:
            /guess APIで期待される形式の辞書
        """
        return {
            "rooms": self.rooms,
            "startingRoom": self.starting_room,
            "connections": self.connections
        }
    
    def to_json(self) -> str:
        """
        JSONストリングにシリアライズする
        
        Returns:
            JSON形式の文字列
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Aedificium':
        """
        /guess API形式の辞書からAedificiumオブジェクトを作成する
        
        Args:
            data: /guess API形式の辞書
        
        Returns:
            Aedificiumオブジェクト
        """
        return cls(
            rooms=data['rooms'],
            starting_room=data['startingRoom'],
            connections=data['connections']
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Aedificium':
        """
        JSON文字列からAedificiumオブジェクトを作成する
        
        Args:
            json_str: JSON形式の文字列
        
        Returns:
            Aedificiumオブジェクト
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def equivalence_test(self, other: 'Aedificium') -> str:
        """
        他のAedificiumと等価かどうかを詳細にテストする
        
        Args:
            other: 比較対象のAedificium
        
        Returns:
            str: 失敗したplan文字列、またはすべて成功した場合はNone
        """
        # 部屋数が異なる場合は等価でない
        if len(self.rooms) != len(other.rooms):
            return "DIFFERENT_ROOM_COUNT"
        
        num_rooms = len(self.rooms)
        plan_length = num_rooms * 18
        
        # 100ケースのランダムなplanでテスト
        for _ in range(100):
            # ランダムなplanを生成（0-5のドア番号）
            plan = ''.join([str(random.randint(0, 5)) for _ in range(plan_length)])
            
            # 両方のAedificiumで同じplanを実行
            self_result = self._execute_plan(plan)
            other_result = other._execute_plan(plan)
            
            # 結果が異なる場合、そのplanを返す
            if self_result != other_result:
                return f"PLAN_FAILED: {plan}"
        
        # すべてのテストケースで成功した場合
        return None

    def is_equivalent_to(self, other: 'Aedificium') -> bool:
        """
        他のAedificiumと等価かどうかを判定する（後方互換性のあるメソッド）
        
        Args:
            other: 比較対象のAedificium
        
        Returns:
            bool: 等価な場合True
        """
        # equivalence_testメソッドを使用して判定
        result = self.equivalence_test(other)
        return result is None
    
    def __repr__(self) -> str:
        """
        オブジェクトの文字列表現
        """
        return f"Aedificium(rooms={len(self.rooms)}, starting_room={self.starting_room}, connections={len(self.connections)})"


# 使用例とテスト用の関数
def create_simple_aedificium() -> Aedificium:
    """
    簡単なテスト用のAedificiumを作成する
    """
    # 3部屋の簡単な例
    rooms = [0, 1, 2]  # 各部屋のラベル
    starting_room = 0
    connections = [
        {"from": {"room": 0, "door": 0}, "to": {"room": 1, "door": 0}},
        {"from": {"room": 1, "door": 1}, "to": {"room": 2, "door": 0}},
        {"from": {"room": 2, "door": 1}, "to": {"room": 0, "door": 1}}
    ]
    
    return Aedificium(rooms, starting_room, connections)


def _is_connected(connections: List[Dict[str, Any]], num_rooms: int) -> bool:
    """
    グラフが連結かどうかをチェックする
    
    Args:
        connections: 接続情報のリスト
        num_rooms: 部屋数
    
    Returns:
        bool: 連結の場合True
    """
    if num_rooms == 0:
        return True
    if num_rooms == 1:
        return True
    
    # 隣接リストを構築
    adj = [[] for _ in range(num_rooms)]
    for conn in connections:
        from_room = conn['from']['room']
        to_room = conn['to']['room']
        adj[from_room].append(to_room)
        adj[to_room].append(from_room)
    
    # DFSで連結性をチェック
    visited = [False] * num_rooms
    stack = [0]  # 部屋0から開始
    visited[0] = True
    
    while stack:
        current = stack.pop()
        for neighbor in adj[current]:
            if not visited[neighbor]:
                visited[neighbor] = True
                stack.append(neighbor)
    
    return all(visited)


def _all_doors_used(connections: List[Dict[str, Any]], num_rooms: int) -> bool:
    """
    全ての部屋の全てのドア（0-5）が使われているかチェックする
    
    Args:
        connections: 接続情報のリスト  
        num_rooms: 部屋数
    
    Returns:
        bool: 全てのドアが使われている場合True
    """
    used_doors = set()
    for conn in connections:
        from_room = conn['from']['room']
        from_door = conn['from']['door']
        to_room = conn['to']['room']
        to_door = conn['to']['door']
        
        used_doors.add((from_room, from_door))
        used_doors.add((to_room, to_door))
    
    # 各部屋の各ドア（0-5）が使われているかチェック
    for room in range(num_rooms):
        for door in range(6):
            if (room, door) not in used_doors:
                return False
    
    return True


def create_random_aedificium(num_rooms: int) -> Aedificium:
    """
    ランダムなAedificiumを生成する
    連結かつ全てのドアが使われているような部屋になるまで生成を繰り返す
    
    Args:
        num_rooms: 部屋数
    
    Returns:
        ランダムに生成されたAedificiumオブジェクト
    """
    # 各部屋のラベルをランダム生成（2ビット整数: 0-3）
    rooms = [random.randint(0, 3) for _ in range(num_rooms)]
    
    # 開始部屋をランダム選択
    starting_room = random.randint(0, num_rooms - 1)
    
    # 条件を満たすまで生成を繰り返す
    max_attempts = 1000  # 無限ループを防ぐための上限
    for attempt in range(max_attempts):
        connections = []
        used_doors = set()
        
        # 全てのドアのリストを作成
        all_doors = []
        for room in range(num_rooms):
            for door in range(6):
                all_doors.append((room, door))
        
        # 全てのドアが使われるまで接続を追加
        while len(used_doors) < len(all_doors):
            # 未使用のドアから復元抽出で2つ選ぶ
            unused_doors = [door for door in all_doors if door not in used_doors]
            
            # 復元抽出で2つのドアを選択
            door1 = random.choice(unused_doors)
            door2 = random.choice(unused_doors)
            
            # 接続を追加
            room1, door_num1 = door1
            room2, door_num2 = door2
            
            connections.append({
                "from": {"room": room1, "door": door_num1},
                "to": {"room": room2, "door": door_num2}
            })
            
            # 使用済みドアに追加
            used_doors.add(door1)
            used_doors.add(door2)
        
        # 連結性と全ドア使用をチェック
        if _is_connected(connections, num_rooms) and _all_doors_used(connections, num_rooms):
            return Aedificium(rooms, starting_room, connections)
    
    # 最大試行回数に達した場合、警告を出してベストエフォートで返す
    print(f"Warning: Could not generate fully connected aedificium with all doors used after {max_attempts} attempts")
    return Aedificium(rooms, starting_room, connections)


if __name__ == "__main__":
    # テスト実行
    aed = create_simple_aedificium()
    print(f"Created: {aed}")
    
    # 探索テスト
    result = aed.explore(["0", "01", "011"])
    print(f"Exploration result: {result}")
    
    # JSON変換テスト
    json_data = aed.to_json()
    print(f"JSON: {json_data}")
    
    # JSON復元テスト
    restored = Aedificium.from_json(json_data)
    print(f"Restored: {restored}")
