from aedificium import Aedificium, problem_names
import api
import random
from typing import List

import z3


def solve(num_rooms: int, plans: List[str], results: List[str]):
    s = z3.Solver()
    
    # Z3の最適化設定
    s.set("timeout", 30000)  # 30秒のタイムアウト
    s.set("random_seed", 42)
    s.set("arith.solver", 2)  # より効/率的な算術ソルバー
    
    m = len(plans)

    # room history - 各プランでの部屋の訪問履歴
    xs = [[z3.Int(f"x_{plan_index}_{i}") for i in range(len(results[plan_index]))] for plan_index in range(m)]
    
    # 部屋の制約（範囲とラベル）を効率的に追加
    for plan_index, (single_xs, result) in enumerate(zip(xs, results)):
        for i, (x, r) in enumerate(zip(single_xs, result)):
            s.add(x >= 0, x < num_rooms, x % 4 == int(r))

    # 開始部屋を0に固定（対称性を破る）
    starting_room = 0
    for plan_index in range(m):
        s.add(xs[plan_index][0] == starting_room)

    # 実際に使用される(room, door)ペアを列挙
    used_room_door_pairs = {(room, door) for room in range(num_rooms) for door in range(6)}

    # ドア遷移変数を必要な分だけ作成
    door_destinations = {}
    door_connections = {}
    
    for room_id, door_id in used_room_door_pairs:
        key = (room_id, door_id)
        door_destinations[key] = z3.Int(f"dd_{room_id}_{door_id}")
        door_connections[key] = z3.Int(f"dc_{room_id}_{door_id}")
        
        # 範囲制約を効率的に追加
        s.add(
            door_destinations[key] >= 0,
            door_destinations[key] < num_rooms,
            door_connections[key] >= 0,
            door_connections[key] < 6
        )

    # 遷移制約 - より効率的に実装
    for plan_index in range(m):
        single_xs = xs[plan_index]
        single_plan = plans[plan_index]
        for step, door_char in enumerate(single_plan):
            door_id = int(door_char)
            from_room = single_xs[step]
            to_room = single_xs[step + 1]
            
            # 条件付き制約を使用
            conditions = []
            for room_id in range(num_rooms):
                if (room_id, door_id) in door_destinations:
                    conditions.append(
                        z3.If(from_room == room_id,
                             door_destinations[(room_id, door_id)] == to_room,
                             True)
                    )
            if conditions:
                s.add(z3.And(conditions))

    # 双方向性制約 - 大幅に簡略化
    bidirectional_added = set()
    for (room_id, door_id) in door_destinations:
        if (room_id, door_id) not in bidirectional_added:
            dest_room_var = door_destinations[(room_id, door_id)]
            dest_door_var = door_connections[(room_id, door_id)]
            
            # 逆方向の制約を効率的に追加
            reverse_conditions = []
            for dest_room in range(num_rooms):
                for dest_door in range(6):
                    if (dest_room, dest_door) in door_destinations:
                        reverse_conditions.append(
                            z3.If(
                                z3.And(dest_room_var == dest_room, dest_door_var == dest_door),
                                z3.And(
                                    door_destinations[(dest_room, dest_door)] == room_id,
                                    door_connections[(dest_room, dest_door)] == door_id
                                ),
                                True
                            )
                        )
            
            if reverse_conditions:
                s.add(z3.And(reverse_conditions))
            
            bidirectional_added.add((room_id, door_id))

    if s.check() != z3.sat:
        print("failed to solve")
        return

    model = s.model()
    rooms = [i % 4 for i in range(num_rooms)]
    starting_room_val = starting_room  # 既に0に固定されている
    
    used_door_pairs = set()
    connections = []
    
    for (room_id, door_id) in door_destinations:
        door_pair = (room_id, door_id)
        if door_pair in used_door_pairs:
            continue
            
        room_to = model.eval(door_destinations[(room_id, door_id)]).as_long()
        door_to = model.eval(door_connections[(room_id, door_id)]).as_long()
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

    problem_name = "probatio"
    # problem_name = "random_full_8_1_42"
    if problem_name in problem_names():
        single_rooms, duplication_factor = problem_names()[problem_name]
    else:
        single_rooms = 8
        duplication_factor = 1
    num_rooms = single_rooms * duplication_factor
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
        return

    # print(f"estimated_aedificium: {estimated_aedificium.to_dict()}")
    guess_response = client.guess(estimated_aedificium.to_dict())
    print(f"guess_response: {guess_response}")



if __name__ == "__main__":
    main()

