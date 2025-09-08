from aedificium import Aedificium, problem_names
import api
import random
from typing import List

import z3


def solve(num_rooms: int, plans: List[str], results: List[str], seed: int = 25252):
    s = z3.Solver()
    
    # Z3の最適化設定
    s.set("timeout", 30000)  # 30秒のタイムアウト
    s.set("random_seed", seed)
    s.set("arith.solver", 2)  # より効/率的な算術ソルバー
    
    m = len(plans)

    # 整数値をバイナリエンコーディングするためのヘルパー関数
    def create_binary_vars(name: str, max_val: int):
        """max_val未満の値を表現するバイナリ変数を作成"""
        if max_val <= 1:
            return [z3.Bool(f"{name}_0")]
        
        bits_needed = (max_val - 1).bit_length()
        return [z3.Bool(f"{name}_{i}") for i in range(bits_needed)]
    
    def binary_to_constraints(binary_vars: List, target_val: int):
        """バイナリ変数が特定の値を表すための制約を返す"""
        constraints = []
        for i, bit_var in enumerate(binary_vars):
            if target_val & (1 << i):
                constraints.append(bit_var)
            else:
                constraints.append(z3.Not(bit_var))
        return z3.And(constraints)
    
    def binary_equals(binary_vars1: List, binary_vars2: List):
        """2つのバイナリ変数が同じ値を表すための制約"""
        if len(binary_vars1) != len(binary_vars2):
            # パディングして長さを合わせる
            max_len = max(len(binary_vars1), len(binary_vars2))
            while len(binary_vars1) < max_len:
                binary_vars1.append(z3.BoolVal(False))
            while len(binary_vars2) < max_len:
                binary_vars2.append(z3.BoolVal(False))
        
        return z3.And([b1 == b2 for b1, b2 in zip(binary_vars1, binary_vars2)])
    
    def binary_less_than(binary_vars: List, max_val: int):
        """バイナリ変数がmax_val未満であることを保証する制約"""
        if max_val >= (1 << len(binary_vars)):
            return z3.BoolVal(True)  # 常に真
        
        # max_val以上の値を禁止する制約を生成
        forbidden_constraints = []
        for val in range(max_val, 1 << len(binary_vars)):
            forbidden_constraints.append(z3.Not(binary_to_constraints(binary_vars, val)))
        return z3.And(forbidden_constraints)
    
    def binary_mod4_equals(binary_vars: List, target_mod: int):
        """バイナリ変数 % 4 == target_modの制約"""
        if len(binary_vars) < 2:
            # 1ビットの場合、値は0か1なので、target_modは0か1のみ有効
            if target_mod in [0, 1]:
                return binary_to_constraints(binary_vars, target_mod)
            else:
                return z3.BoolVal(False)
        
        # 下位2ビットがtarget_modと一致する制約
        return z3.And([
            binary_vars[0] if (target_mod & 1) else z3.Not(binary_vars[0]),
            binary_vars[1] if (target_mod & 2) else z3.Not(binary_vars[1])
        ])

    # room history - 各プランでの部屋の訪問履歴（バイナリエンコーディング）
    xs = []
    for plan_index in range(m):
        plan_xs = []
        for i in range(len(results[plan_index])):
            room_binary = create_binary_vars(f"x_{plan_index}_{i}", num_rooms)
            plan_xs.append(room_binary)
        xs.append(plan_xs)
    
    # 部屋の制約（範囲とラベル）を追加
    for plan_index, (single_xs, result) in enumerate(zip(xs, results)):
        for i, (x_binary, r) in enumerate(zip(single_xs, result)):
            # 範囲制約: x < num_rooms
            s.add(binary_less_than(x_binary, num_rooms))
            # ラベル制約: x % 4 == int(r)
            s.add(binary_mod4_equals(x_binary, int(r)))

    # 開始部屋を0に固定（対称性を破る）
    starting_room = 0
    for plan_index in range(m):
        s.add(binary_to_constraints(xs[plan_index][0], starting_room))

    # 実際に使用される(room, door)ペアを列挙
    used_room_door_pairs = {(room, door) for room in range(num_rooms) for door in range(6)}

    # ドア遷移変数を必要な分だけ作成（バイナリエンコーディング）
    door_destinations = {}
    door_connections = {}
    
    for room_id, door_id in used_room_door_pairs:
        key = (room_id, door_id)
        door_destinations[key] = create_binary_vars(f"dd_{room_id}_{door_id}", num_rooms)
        door_connections[key] = create_binary_vars(f"dc_{room_id}_{door_id}", 6)
        
        # 範囲制約を追加
        s.add(binary_less_than(door_destinations[key], num_rooms))
        s.add(binary_less_than(door_connections[key], 6))

    # 遷移制約
    for plan_index in range(m):
        single_xs = xs[plan_index]
        single_plan = plans[plan_index]
        for step, door_char in enumerate(single_plan):
            door_id = int(door_char)
            from_room_binary = single_xs[step]
            to_room_binary = single_xs[step + 1]
            
            # 各部屋からの遷移制約
            for room_id in range(num_rooms):
                if (room_id, door_id) in door_destinations:
                    # from_room == room_id なら door_destinations[(room_id, door_id)] == to_room
                    room_match = binary_to_constraints(from_room_binary, room_id)
                    dest_match = binary_equals(door_destinations[(room_id, door_id)], to_room_binary)
                    s.add(z3.Implies(room_match, dest_match))

    # 双方向性制約
    bidirectional_added = set()
    for (room_id, door_id) in door_destinations:
        if (room_id, door_id) not in bidirectional_added:
            dest_room_binary = door_destinations[(room_id, door_id)]
            dest_door_binary = door_connections[(room_id, door_id)]
            
            # 逆方向の制約を追加
            for dest_room in range(num_rooms):
                for dest_door in range(6):
                    if (dest_room, dest_door) in door_destinations:
                        # dest_room_binary == dest_room かつ dest_door_binary == dest_door なら
                        # door_destinations[(dest_room, dest_door)] == room_id かつ 
                        # door_connections[(dest_room, dest_door)] == door_id
                        condition = z3.And(
                            binary_to_constraints(dest_room_binary, dest_room),
                            binary_to_constraints(dest_door_binary, dest_door)
                        )
                        consequence = z3.And(
                            binary_to_constraints(door_destinations[(dest_room, dest_door)], room_id),
                            binary_to_constraints(door_connections[(dest_room, dest_door)], door_id)
                        )
                        s.add(z3.Implies(condition, consequence))
            
            bidirectional_added.add((room_id, door_id))

    if s.check() != z3.sat:
        print("failed to solve")
        return

    model = s.model()
    
    def eval_binary(binary_vars: List):
        """バイナリ変数の値を整数に変換"""
        result = 0
        for i, bit_var in enumerate(binary_vars):
            if model.eval(bit_var, model_completion=True):
                result |= (1 << i)
        return result
    
    rooms = [i % 4 for i in range(num_rooms)]
    starting_room_val = starting_room  # 既に0に固定されている
    
    used_door_pairs = set()
    connections = []
    
    for (room_id, door_id) in door_destinations:
        door_pair = (room_id, door_id)
        if door_pair in used_door_pairs:
            continue
            
        room_to = eval_binary(door_destinations[(room_id, door_id)])
        door_to = eval_binary(door_connections[(room_id, door_id)])
        reverse_pair = (room_to, door_to)
        
        if reverse_pair in used_door_pairs:
            continue  # 既に処理済み
            
        used_door_pairs.add(door_pair)
        used_door_pairs.add(reverse_pair)
        
        connections.append({
            "from": {"room": room_id, "door": door_id},
            "to": {"room": room_to, "door": door_to}
        })
    
    return Aedificium(rooms, starting_room_val, connections)


def main():
    client = api.APIClient(
        api_base="http://localhost:8000",
        api_id="sakazuki",
    )
    # client = api.APIClient(
    #     api_base="https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com",
    #     api_id="amylase.inquiry@gmail.com X6G0RVKUlX20I8XSUsnkIQ",
    # )

    problem_name = "tertius"
    # problem_name = "random_full_8_1_42"
    if problem_name in problem_names():
        single_rooms, duplication_factor = problem_names()[problem_name]
    else:
        single_rooms = 8
        duplication_factor = 1
    num_rooms = single_rooms * duplication_factor

    while True:
        client.select(problem_name)

        plan_count = 3
        plans = [''.join(random.choices("012345", k=num_rooms * 6)) for _ in range(plan_count)]

        results_ints = client.explore(plans)["results"]
        results = [''.join(map(str, result_ints)) for result_ints in results_ints]

        print(f"plan: {plans}")
        print(f"result: {results}")

        estimated_aedificium = solve(num_rooms, plans, results)
        if estimated_aedificium is None:
            print("z3が解を見つけられませんでした")
            continue

        # print(f"estimated_aedificium: {estimated_aedificium.to_dict()}")
        guess_response = client.guess(estimated_aedificium.to_dict())
        print(f"guess_response: {guess_response}")
        if guess_response["correct"]:
            break
        else:
            print("failed to guess")
            # continue
            break



if __name__ == "__main__":
    main()

