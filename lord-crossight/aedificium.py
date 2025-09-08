from typing import List, Dict, Any, Tuple, Set
import json
from random import Random
import enum
import random


class Action(enum.Enum):
    MOVE = 0
    USE_CHARCOAL = 1


def parse_plan(plan: str) -> List[Tuple[Action, int]]:
    instructions = []
    p = 0
    while p < len(plan):
        if plan[p] == '[':
            instructions.append((Action.USE_CHARCOAL, int(plan[p+1])))
            p += 3
        else:
            instructions.append((Action.MOVE, int(plan[p])))
            p += 1
    return instructions

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
            fr = (from_room, from_door)
            to = (to_room, to_door)
            if fr in connection_map:
                print(f"INCONSISTENT MAP: door {fr} -> {to}, {connection_map[fr]}")
            if to in connection_map:
                print(f"INCONSISTENT MAP: door {to} -> {fr}, {connection_map[to]}")
            connection_map[fr] = to
            connection_map[to] = fr
        
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

    def _parse_plan(self, plan: str) -> List[Tuple[Action, int]]:
        instructions = []
        p = 0
        while p < len(plan):
            if plan[p] == '[':
                instructions.append((Action.USE_CHARCOAL, int(plan[p+1])))
                p += 3
            else:
                instructions.append((Action.MOVE, int(plan[p])))
                p += 1
        return instructions
    
    def _execute_plan(self, plan: str) -> List[int]:
        """
        単一のroute planを実行する
        
        Args:
            plan: route plan（"0123"のような文字列）
        
        Returns:
            訪問した部屋のラベルのリスト
        """
        current_room = self.starting_room
        current_labels = self.rooms[:]
        labels = [current_labels[current_room]]  # 開始部屋のラベルを記録
        
        for action, action_arg in parse_plan(plan):
            if action == Action.MOVE:
                door = action_arg
                # 現在の部屋から指定されたドアを通って次の部屋へ移動
                if (current_room, door) in self._connection_map:
                    next_room, _ = self._connection_map[(current_room, door)]
                    current_room = next_room
            else:
                label = action_arg
                current_labels[current_room] = label
            labels.append(current_labels[current_room])
            
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
    
    def equivalence_test(self, other: 'Aedificium', full_contest_feature: bool = False) -> str:
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
        plan_length = num_rooms * (6 if full_contest_feature else 18)
        random_state = Random()
        
        # 100ケースのランダムなplanでテスト
        for _ in range(100):
            # ランダムなplanを生成（0-5のドア番号）
            plan = ''.join([str(random_state.randint(0, 5)) for _ in range(plan_length)])
            
            # 両方のAedificiumで同じplanを実行
            self_result = self._execute_plan(plan)
            other_result = other._execute_plan(plan)
            
            # 結果が異なる場合、そのplanを返す
            if self_result != other_result:
                return f"PLAN_FAILED: {plan}"

        if not full_contest_feature:
            return None

        # 100ケースのランダムなplanでテスト 木炭付き
        for _ in range(100):
            # ランダムなplanを生成（0-5のドア番号と0-3の木炭番号）
            plan = ''.join([random_state.choice("012345") + "[" + random_state.choice("0123") + "]" for _ in range(plan_length)])
            
            # 両方のAedificiumで同じplanを実行
            self_result = self._execute_plan(plan)
            other_result = other._execute_plan(plan)
            
            # 結果が異なる場合、そのplanを返す
            if self_result != other_result:
                return f"PLAN_WITH_CHARCOAL_FAILED: {plan}"
        
        # すべてのテストケースで成功した場合
        return None

    def is_equivalent_to(self, other: 'Aedificium', full_contest_feature: bool = False) -> bool:
        """
        他のAedificiumと等価かどうかを判定する（後方互換性のあるメソッド）
        
        Args:
            other: 比較対象のAedificium
        
        Returns:
            bool: 等価な場合True
        """
        # equivalence_testメソッドを使用して判定
        result = self.equivalence_test(other, full_contest_feature)
        return result is None
    

    def inject_charcoal_to_walk(self, plan: str) -> str:
        visited = [False] * len(self.rooms)

        # 縮小マップでまだ訪問したことがない頂点にきたらラベルを張り替える
        current_room = self.starting_room
        visited[current_room] = True
        new_plan = f"[{(self.rooms[current_room] + 1) % 4}]"

        for door_str in plan:
            new_plan += door_str
            door_num = int(door_str)
            door = self._connection_map[(current_room, door_num)]
            next_room = door[0]
            if not visited[next_room]:
                # 縮小マップでまだ訪問したことがない頂点にきたらラベルを張り替える
                visited[next_room] = True
                new_plan += f"[{(self.rooms[next_room] + 1) % 4}]"
            current_room = next_room
        return new_plan

    def inject_charcoal_to_walk_triple(self, plan_str: str, layer_b_pos: Dict[int, int]) -> str:
        plan = parse_plan(plan_str)

        current_room = self.starting_room
        new_plan = []
        for (i, move) in enumerate(plan):
            new_plan.append(move)
            if move[0] == Action.USE_CHARCOAL:
                continue
            door = self._connection_map[(current_room, move[1])]
            next_room = door[0]
            if i in layer_b_pos:
                new_plan.append((Action.USE_CHARCOAL, (self.rooms[next_room] + 2) % 4))
            current_room = next_room

        new_plan_str = ""
        for (action, payload) in new_plan:
            if action == Action.MOVE:
                new_plan_str += str(payload)
            elif action == Action.USE_CHARCOAL:
                new_plan_str += f"[{payload}]"
        return new_plan_str

    def build_edge_cover_walk_double(self) -> str:
        max_len = len(self.rooms) * 2 * 6
        seen_doors = set()
        
        final_plan = ""
        cur_room = self.starting_room
        # まだ見たことのないドアを優先的に開けるランダムウォーク
        for _ in range(max_len):
            best_door_num = None
            for door_num in range(6):
                door = (cur_room, door_num)
                if door not in seen_doors:
                    best_door_num = door_num
            if best_door_num == None:
                best_door_num = random.randint(0, 5)
            door = (cur_room, best_door_num)
            final_plan += str(best_door_num)
            seen_doors.add(door)
            cur_room = self._connection_map[door][0]
        return final_plan


    def build_dest_maps_double(self, plan_str: str, result: List[int], ignore_layer_b_transition: bool = False) -> Dict[Tuple[int, int], int] | None:
        # n = 縮小マップの次数 (実際のn / 2)
        n = len(self.rooms)
        dests = {}
        plan = parse_plan(plan_str)
        print(plan)

        # 縮小マップの上で動きをシミュレートし、ラベルが縮小マップと異なる場合はレイヤーをまたいだと判断する
        current_room = self.starting_room
        current_layer = 0
        for ((action, door_num), label, (next_action, _)) in zip(plan, result[1:], (plan[1:] + [(None, None)])):
            print("cur", f"({current_room}, {current_layer}): ({action}, {door_num})")
            if action == Action.USE_CHARCOAL:
                current_layer = 0
                continue
            door = self._connection_map[(current_room, door_num)]
            next_room = door[0]
            if next_action != Action.USE_CHARCOAL and self.rooms[next_room] == label:
                next_layer = 1
            else:
                next_layer = 0
            from_door = (current_room + current_layer * n, door_num)
            to_room = next_room + next_layer * n
            if not (ignore_layer_b_transition and current_layer != 0):
                if from_door in dests and dests[from_door] != to_room:
                    print(f"[ERROR] Conflicting door: {from_door}, {to_room}, {dests[from_door]}")
                    dests[from_door] = min(dests[from_door], to_room)
                    #return None
                else:
                    dests[from_door] = to_room
            current_room, current_layer = next_room, next_layer
        return dests
    
    def build_layer_b_pos(self, plan_str: str, results: List[int]) -> Dict[int, int]:
        layer_a_visited = [False] * len(self.rooms)
        layer_b_visited = [False] * len(self.rooms)
        plan = parse_plan(plan_str)

        layer_b_pos = {}
        current_room = self.starting_room
        for (i, ((action, door_num), label)) in enumerate(zip(plan, results[1:])):
            if action == Action.USE_CHARCOAL:
                layer_a_visited[current_room] = True
                continue
            door = self._connection_map[(current_room, door_num)]
            next_room = door[0]
            if layer_a_visited[next_room] and self.rooms[next_room] == label:
                if not layer_b_visited[next_room]:
                    layer_b_visited[next_room] = True
                    layer_b_pos[i] = next_room
            current_room = next_room
        return layer_b_pos

    def build_dest_maps_triple(self, plan_str: str, result: List[int]) -> Dict[Tuple[int, int], int] | None:
        # n = 縮小マップの次数（実際の1/3）
        n = len(self.rooms)
        dests = {}
        plan = parse_plan(plan_str)

        current_room = self.starting_room
        current_layer = 0
        for ((action, door_num), label, (next_action, next_payload)) in zip(plan, result[1:], (plan[1:] + [(None, None)])):
            print("cur", f"({current_room}, {current_layer}): ({action}, {door_num})")
            if action == Action.USE_CHARCOAL:
                continue
            door = self._connection_map[(current_room, door_num)]
            next_room = door[0]
            if next_action == Action.USE_CHARCOAL:
                label = next_payload
            if label == (self.rooms[next_room] + 1) % 4:
                next_layer = 0
            elif label == (self.rooms[next_room] + 2) % 4:
                next_layer = 1
            elif label == self.rooms[next_room]:
                next_layer = 2
            else:
                print(f"INCONSISTENT: room={next_room}, expected={self.rooms[next_room]}, got={label}")
                return None
            from_door = (current_room + current_layer * n, door_num)
            to_room = next_room + next_layer * n
            if from_door in dests and dests[from_door] != to_room:
                print(f"[ERROR] Conflicting door: {from_door}, {to_room}, {dests[from_door]}")
                dests[from_door] = min(dests[from_door], to_room)
                #return None
            else:
                dests[from_door] = to_room
            current_room, current_layer = next_room, next_layer
        print("---")
        return dests


    def build_covering_path(self, targets: List[int]) -> str:
        n = len(self.rooms)
        done = [False] * n
        cur_room = self.starting_room
        final_plan = ""
        for target in targets:
            if done[target]:
                continue
            visited = [False] * n
            prev = [None] * n
            visited[cur_room] = True
            q = [(cur_room, "")]
            while len(q) > 0:
                (room, plan) = q.pop()
                if room == target:
                    final_plan += plan
                    r = target
                    while r is not None:
                        done[r] = True
                        r = prev[r]
                    cur_room = target
                    break
                for door in range(6):
                    conn = self._connection_map[(room, door)]
                    to_room = conn[0]
                    if visited[to_room]:
                        continue
                    visited[to_room] = True
                    prev[to_room] = room
                    q.append((to_room, plan + str(door)))
        return final_plan


    def __repr__(self) -> str:
        """
        オブジェクトの文字列表現
        """
        return f"Aedificium(rooms={len(self.rooms)}, starting_room={self.starting_room}, connections={len(self.connections)})"


def deduplicate_aedificium(aedificium: Aedificium) -> Aedificium:
    """
    Aedificiumを重複を削除したAedificiumに変換する
    重複については、create_random_aedificiumの実装を仮定する
    
    Args:
        aedificium: 重複を削除するAedificium
    
    Returns:
        Aedificium: 重複を削除したAedificium
    """
    num_rooms = len(aedificium.rooms)
    for duplication_factor in [3, 2]:
        if num_rooms % duplication_factor != 0:
            continue
        single_rooms = num_rooms // duplication_factor

        rooms = aedificium.rooms[:num_rooms // duplication_factor]
        starting_room = aedificium.starting_room
        connections = []
        used_doors = set()
        used_connections = set()

        ok = True
        for connection in aedificium.connections:
            new_from = {
                "room": connection['from']['room'] % single_rooms,
                "door": connection['from']['door']
            }
            new_to = {
                "room": connection['to']['room'] % single_rooms,
                "door": connection['to']['door']
            }
            from_tag = (new_from['room'], new_from['door'])
            to_tag = (new_to['room'], new_to['door'])
            connection_tag = (from_tag, to_tag)
            if connection_tag in used_connections:
                continue
            used_connections.add(connection_tag)
            if from_tag in used_doors or to_tag in used_doors:
                # used in different connection. contradiction
                ok = False
                break
            used_doors.add(from_tag)
            used_doors.add(to_tag)
            connections.append({
                "from": new_from,
                "to": new_to
            })
        if ok and len(used_doors) == single_rooms * 6:
            return Aedificium(rooms, starting_room, connections)

    print(f"DEBUG: failed to deduplicate aedificium. returning original value: {aedificium}")
    return aedificium


def problem_names():
    return {
        "probatio": (3, 1),
        "primus": (6, 1),
        "secundus": (12, 1),
        "tertius": (18, 1),
        "quartus": (24, 1),
        "quintus": (30, 1),

        "aleph": (6, 2),
        "beth": (12, 2),
        "gimel": (18, 2),
        "daleth": (24, 2),
        "he": (30, 2),

        "vau": (6, 3),
        "zain": (12, 3),
        "hhet": (18, 3),
        "teth": (24, 3),
        "iod": (30, 3),
    }


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


def create_random_aedificium(single_rooms: int, duplication_factor: int = 1, random_state: Random | None = None) -> Aedificium:
    """
    ランダムなAedificiumを生成する
    連結かつ全てのドアが使われているような部屋になるまで生成を繰り返す
    
    Args:
        single_rooms: duplication_factorによる重複を考慮しない部屋数
        duplication_factor: 重複度。num_rooms * duplication_factor が部屋数になる。
    
    Returns:
        ランダムに生成されたAedificiumオブジェクト
    """
    random_state = random_state or Random()

    if duplication_factor == 1:
        return _create_random_aedificium_single(single_rooms, random_state)
    assert duplication_factor > 1

    num_rooms = single_rooms * duplication_factor
    max_attempts = 10
    for _ in range(max_attempts):
        single_aedificium = _create_random_aedificium_single(single_rooms, random_state)
        rooms = single_aedificium.rooms * duplication_factor
        starting_room = single_aedificium.starting_room
        connection_dupes = []
        for i in range(duplication_factor):
            renamed_connections = []
            for connection in single_aedificium.connections:
                renamed_connections.append({
                    "from": {"room": connection['from']['room'] + i * single_rooms, "door": connection['from']['door']},
                    "to": {"room": connection['to']['room'] + i * single_rooms, "door": connection['to']['door']}
                })
            connection_dupes.append(renamed_connections)
        for i, duped_connections in enumerate(zip(*connection_dupes)):
            if duped_connections[0]["from"] == duped_connections[0]["to"]:
                # self loop
                i1, i2 = random_state.choices(range(duplication_factor), k=2)
                if i1 == i2:
                    continue
                duped_connections[i1]["to"] = duped_connections[i2]["from"]
                connection_dupes[i2][i] = None
            else:
                # normal case
                for _ in range(random_state.randint(8, 12)):
                    swap_side = random_state.choice(["from", "to"])
                    i1, i2 = random_state.sample(range(duplication_factor), 2)
                    duped_connections[i1][swap_side], duped_connections[i2][swap_side] = duped_connections[i2][swap_side], duped_connections[i1][swap_side]
        connections = sum(connection_dupes, [])
        connections = [conn for conn in connections if conn is not None]
        candidate = Aedificium(rooms, starting_room, connections)
        if _is_connected(connections, num_rooms) and _all_doors_used(connections, num_rooms):
            return candidate
    # 最大試行回数に達した場合、警告を出してベストエフォートで返す
    print(f"Warning: Could not generate fully connected aedificium with all doors used after {max_attempts} attempts")
    return candidate


def _create_random_aedificium_single(num_rooms: int, random_state: Random) -> Aedificium:
    """
    ランダムなAedificiumを生成する
    連結かつ全てのドアが使われているような部屋になるまで生成を繰り返す
    
    Args:
        num_rooms: 部屋数
    
    Returns:
        ランダムに生成されたAedificiumオブジェクト
    """
    # 推測: i mod 4 をランダムシャッフルしているだけ
    rooms = [i % 4 for i in range(num_rooms)]
    random_state.shuffle(rooms)
    
    # 開始部屋をランダム選択
    zero_rooms = [i for i in range(num_rooms) if rooms[i] == 0]
    starting_room = random_state.choice(zero_rooms)
    
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
            door1 = random_state.choice(unused_doors)
            door2 = random_state.choice(unused_doors)
            
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


def reconstruct_aedificium(plan: str, result: List[int], room_history: List[int], num_rooms: int) -> Aedificium | None:
    """
    探索結果と真の部屋IDからÆdificium全体を復元する
    
    Args:
        plan: 探索に使用したplan（例："23"）
        result: planの探索結果（部屋ラベルのリスト、例：[0,1,2]）
        room_history: resultの各要素に対応する真の部屋ID（例：[4,5,6]）
        num_rooms: 部屋数
    Returns:
        復元されたAedificiumオブジェクト、または失敗時はNone
    """

    if len(result) != len(room_history):
        raise ValueError("result and room_history length mismatch")

    rooms = [None for _ in range(num_rooms)]
    for room_id, room_label in zip(room_history, result):
        if rooms[room_id] is not None and rooms[room_id] != room_label:
            print(f"DEBUG: room_id={room_id}, room_label={room_label}, rooms[room_id]={rooms[room_id]}")
            return None
        rooms[room_id] = room_label
    if any(room_label is None for room_label in rooms):
        print(f"DEBUG: rooms={rooms}")
        return None

    plan_ints = [int(p) for p in plan]
    door_destinations = {}
    for room_from, plan_int, room_to in zip(room_history[:-1], plan_ints, room_history[1:]):
        door = (room_from, plan_int)
        if door in door_destinations and door_destinations[door] != room_to:
            print(f"DEBUG: door={door}, door_destinations[door]={door_destinations[door]}, room_to={room_to}")
            return None
        door_destinations[door] = room_to

    connections = build_connections(door_destinations)
    if connections is None:
        return None
    return Aedificium(rooms, starting_room=room_history[0], connections=connections)


def build_connections(door_destinations: Dict[Tuple[int, int], int], num_rooms: int | None = None) -> List[Dict[str, Any]] | None:
    if num_rooms is None:
        num_rooms = len(door_destinations) // 6
    incoming_doors = [set() for _ in range(num_rooms)]
    for door, room_to in door_destinations.items():
        incoming_doors[room_to].add(door)

    connections = []
    used_doors = set()
    for room_id, incoming_door_set in enumerate(incoming_doors):
        if len(incoming_door_set) > 6:
            print(f"DEBUG: room_id={room_id}, incoming_door_set={incoming_door_set}")
            return None
        for incoming_door in incoming_door_set:
            if incoming_door in used_doors:
                continue
            for door_id in range(6):
                outgoing_door = (room_id, door_id)
                if outgoing_door in used_doors:
                    continue
                incoming_room = incoming_door[0]
                other_room = door_destinations.get(outgoing_door, incoming_room)
                if other_room != incoming_room:
                    continue
                connections.append({
                    "from": {"room": incoming_door[0], "door": incoming_door[1]},
                    "to": {"room": outgoing_door[0], "door": outgoing_door[1]}
                })
                used_doors.add(incoming_door)
                used_doors.add(outgoing_door)
                break  # 1つの incoming_door につき1つの接続のみ

    # fill connections with self loops for unused doors
    for room_id in range(num_rooms):
        for door_id in range(6):
            if (room_id, door_id) not in used_doors:
                connections.append({
                    "from": {"room": room_id, "door": door_id},
                    "to": {"room": room_id, "door": door_id}
                })
    return connections


def test_reconstruct_aedificium():
    """
    reconstruct_aedificium関数のテスト
    """
    print("=== reconstruct_aedificium テスト開始 ===")
    
    # テスト1: 基本的な復元テスト
    def test_basic_reconstruction():
        print("\nテスト1: 基本的な復元テスト")
        
        # 元のAedificiumを作成
        original = create_simple_aedificium()
        print(f"元のAedificium: {original}")
        
        # 探索を実行
        plan = "012345"
        explore_result = original.explore([plan])
        result = explore_result["results"][0]
        print(f"探索プラン: {plan}")
        print(f"探索結果: {result}")
        
        # 実際の部屋履歴を生成（探索をシミュレート）
        current_room = original.starting_room
        room_history = [current_room]
        
        for door_char in plan:
            door = int(door_char)
            if (current_room, door) in original._connection_map:
                next_room, _ = original._connection_map[(current_room, door)]
                current_room = next_room
            room_history.append(current_room)
        
        print(f"部屋履歴: {room_history}")
        
        # Aedificiumを復元
        reconstructed = reconstruct_aedificium(plan, result, room_history, len(original.rooms))
        
        if reconstructed is None:
            print("❌ 復元に失敗しました")
            return False
        
        print(f"復元されたAedificium: {reconstructed}")
        
        # 復元されたものが元と同じ動作をするかテスト
        original_test = original.explore([plan])
        reconstructed_test = reconstructed.explore([plan])
        
        if original_test["results"] == reconstructed_test["results"]:
            print("✅ 基本的な復元テストが成功しました")
            return True
        else:
            print("❌ 復元されたAedificiumの動作が元と異なります")
            print(f"元の結果: {original_test['results']}")
            print(f"復元の結果: {reconstructed_test['results']}")
            return False
    
    # テスト2: 長いプランでの復元テスト
    def test_long_plan_reconstruction():
        print("\nテスト2: 長いプランでの復元テスト")
        
        # より複雑なAedificiumを作成
        rooms = [0, 1, 2, 3, 0]  # 5部屋
        starting_room = 0
        connections = [
            {"from": {"room": 0, "door": 0}, "to": {"room": 1, "door": 0}},
            {"from": {"room": 1, "door": 1}, "to": {"room": 2, "door": 0}},
            {"from": {"room": 2, "door": 1}, "to": {"room": 3, "door": 0}},
            {"from": {"room": 3, "door": 1}, "to": {"room": 4, "door": 0}},
            {"from": {"room": 4, "door": 1}, "to": {"room": 0, "door": 1}},
            # 自己ループで残りのドアを埋める
            {"from": {"room": 0, "door": 2}, "to": {"room": 0, "door": 2}},
            {"from": {"room": 0, "door": 3}, "to": {"room": 0, "door": 3}},
            {"from": {"room": 0, "door": 4}, "to": {"room": 0, "door": 4}},
            {"from": {"room": 0, "door": 5}, "to": {"room": 0, "door": 5}},
            {"from": {"room": 1, "door": 2}, "to": {"room": 1, "door": 2}},
            {"from": {"room": 1, "door": 3}, "to": {"room": 1, "door": 3}},
            {"from": {"room": 1, "door": 4}, "to": {"room": 1, "door": 4}},
            {"from": {"room": 1, "door": 5}, "to": {"room": 1, "door": 5}},
            {"from": {"room": 2, "door": 2}, "to": {"room": 2, "door": 2}},
            {"from": {"room": 2, "door": 3}, "to": {"room": 2, "door": 3}},
            {"from": {"room": 2, "door": 4}, "to": {"room": 2, "door": 4}},
            {"from": {"room": 2, "door": 5}, "to": {"room": 2, "door": 5}},
            {"from": {"room": 3, "door": 2}, "to": {"room": 3, "door": 2}},
            {"from": {"room": 3, "door": 3}, "to": {"room": 3, "door": 3}},
            {"from": {"room": 3, "door": 4}, "to": {"room": 3, "door": 4}},
            {"from": {"room": 3, "door": 5}, "to": {"room": 3, "door": 5}},
            {"from": {"room": 4, "door": 2}, "to": {"room": 4, "door": 2}},
            {"from": {"room": 4, "door": 3}, "to": {"room": 4, "door": 3}},
            {"from": {"room": 4, "door": 4}, "to": {"room": 4, "door": 4}},
            {"from": {"room": 4, "door": 5}, "to": {"room": 4, "door": 5}},
        ]
        
        original = Aedificium(rooms, starting_room, connections)
        
        # 長いプランで探索
        plan = "011111111"
        explore_result = original.explore([plan])
        result = explore_result["results"][0]
        
        # 部屋履歴を生成
        current_room = original.starting_room
        room_history = [current_room]
        
        for door_char in plan:
            door = int(door_char)
            if (current_room, door) in original._connection_map:
                next_room, _ = original._connection_map[(current_room, door)]
                current_room = next_room
            room_history.append(current_room)
        
        print(f"長いプラン: {plan}")
        print(f"探索結果: {result}")
        print(f"部屋履歴: {room_history}")
        
        # 復元を試行
        reconstructed = reconstruct_aedificium(plan, result, room_history, len(original.rooms))
        
        if reconstructed is None:
            print("❌ 長いプランでの復元に失敗しました")
            return False
        
        # 動作確認
        original_test = original.explore([plan])
        reconstructed_test = reconstructed.explore([plan])
        
        if original_test["results"] == reconstructed_test["results"]:
            print("✅ 長いプランでの復元テストが成功しました")
            return True
        else:
            print("❌ 長いプランでの復元が失敗しました")
            return False
    
    # テスト3: エラーケースのテスト
    def test_error_cases():
        print("\nテスト3: エラーケースのテスト")
        
        # 長さが一致しないケース
        try:
            result1 = reconstruct_aedificium("01", [0, 1, 2], [0, 1], 3)  # 長さ不一致
            print("❌ 長さ不一致のエラーケースで例外が発生しませんでした")
            return False
        except ValueError:
            print("✅ 長さ不一致のエラーケースが適切に処理されました（例外発生）")
        
        # 矛盾する部屋ラベルのケース
        result2 = reconstruct_aedificium("01", [0, 1, 2], [0, 1, 0], 2)  # 部屋0のラベルが0と2で矛盾
        if result2 is not None:
            print("❌ 矛盾する部屋ラベルのエラーケースが適切に処理されませんでした")
            return False
        else:
            print("✅ 矛盾する部屋ラベルのエラーケースが適切に処理されました（None返却）")
        
        print("✅ エラーケースのテストが成功しました")
        return True
    
    # テスト4: 単一部屋のテスト
    def test_single_room():
        print("\nテスト4: 単一部屋のテスト")
        
        plan = ""  # 空のプラン
        result = [2]  # 部屋ラベル2
        room_history = [0]  # 部屋0のみ
        num_rooms = 1
        
        reconstructed = reconstruct_aedificium(plan, result, room_history, num_rooms)
        
        if reconstructed is None:
            print("❌ 単一部屋の復元に失敗しました")
            return False
        
        # 復元された部屋のラベルが正しいか確認
        if reconstructed.rooms[0] == 2 and reconstructed.starting_room == 0:
            print("✅ 単一部屋のテストが成功しました")
            return True
        else:
            print("❌ 単一部屋の復元結果が正しくありません")
            return False
    
    # 全テストを実行
    test_results = []
    test_results.append(test_basic_reconstruction())
    test_results.append(test_long_plan_reconstruction())
    test_results.append(test_error_cases())
    test_results.append(test_single_room())
    
    # 結果の集計
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n=== テスト結果: {passed}/{total} 成功 ===")
    
    if passed == total:
        print("✅ 全てのテストが成功しました！")
    else:
        print("❌ 一部のテストが失敗しました")
    
    return passed == total


if __name__ == "__main__":
    # 既存のテスト実行
    print("=== 既存のAedificiumテスト ===")
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

    print("\n" + "="*50)
    
    # reconstruct_aedificiumのテスト実行
    test_reconstruct_aedificium()
