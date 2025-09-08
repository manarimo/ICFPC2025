from aedificium import Aedificium, problem_names
import api
import random
from typing import List
import kissat
import tempfile
import os

import cnfc


def solve(num_rooms: int, plans: List[str], results: List[str], seed: int = 25252):
    f = cnfc.Formula()
    
    m = len(plans)

    # 整数値をバイナリエンコーディングするためのヘルパー関数
    def create_intvar(name: str, max_val: int) -> cnfc.Integer:
        """max_val未満の値を表現するバイナリ変数を作成"""
        bits_needed = (max_val - 1).bit_length()
        intvar = cnfc.Integer(*[f.AddVar(f"{name}_{i}") for i in range(bits_needed)])
        f.Add(intvar < max_val)
        f.Add(intvar >= 0)
        return intvar

    # room history - 各プランでの部屋の訪問履歴（バイナリエンコーディング）
    xs = []
    for plan_index in range(m):
        plan_xs = []
        for i in range(len(results[plan_index])):
            room_var = create_intvar(f"room_history_{plan_index}_{i}", num_rooms)
            plan_xs.append(room_var)
        xs.append(plan_xs)
    
    # 部屋の制約（範囲とラベル）を追加
    for plan_index, (single_xs, result) in enumerate(zip(xs, results)):
        for i, (x_intvar, r) in enumerate(zip(single_xs, result)):
            # ラベル制約: x % 4 == int(r)
            f.Add(x_intvar % 4 == int(r))

    # 開始部屋を0に固定（対称性を破る）
    starting_room = 0
    for plan_index in range(m):
        f.Add(xs[plan_index][0] == starting_room)

    # 実際に使用される(room, door)ペアを列挙
    used_room_door_pairs = {(room, door) for room in range(num_rooms) for door in range(6)}

    # ドア遷移変数を必要な分だけ作成（バイナリエンコーディング）
    door_destinations = {}
    door_connections = {}
    
    for room_id, door_id in used_room_door_pairs:
        key = (room_id, door_id)
        door_destinations[key] = create_intvar(f"door_destinations_{room_id}_{door_id}", num_rooms)
        door_connections[key] = create_intvar(f"door_connections_{room_id}_{door_id}", 6)

    # 遷移制約
    for plan_index in range(m):
        single_xs = xs[plan_index]
        single_plan = plans[plan_index]
        for step, door_char in enumerate(single_plan):
            door_id = int(door_char)
            from_room_intvar = single_xs[step]
            to_room_intvar = single_xs[step + 1]
            
            # 各部屋からの遷移制約
            for room_id in range(num_rooms):
                if (room_id, door_id) in door_destinations:
                    # from_room == room_id なら door_destinations[(room_id, door_id)] == to_room
                    f.Add(cnfc.Implies(from_room_intvar == room_id, door_destinations[(room_id, door_id)] == to_room_intvar))

    # 双方向性制約
    bidirectional_added = set()
    for (room_id, door_id) in door_destinations:
        if (room_id, door_id) not in bidirectional_added:
            dest_room_intvar = door_destinations[(room_id, door_id)]
            dest_door_intvar = door_connections[(room_id, door_id)]
            
            # 逆方向の制約を追加
            for dest_room in range(num_rooms):
                for dest_door in range(6):
                    if (dest_room, dest_door) in door_destinations:
                        # dest_room_binary == dest_room かつ dest_door_binary == dest_door なら
                        # door_destinations[(dest_room, dest_door)] == room_id かつ 
                        # door_connections[(dest_room, dest_door)] == door_id
                        condition = cnfc.And(
                            dest_room_intvar == dest_room,
                            dest_door_intvar == dest_door
                        )
                        consequence = cnfc.And(
                            door_destinations[(dest_room, dest_door)] == room_id,
                            door_connections[(dest_room, dest_door)] == door_id
                        )
                        f.Add(cnfc.Implies(condition, consequence))
            
            bidirectional_added.add((room_id, door_id))

    with tempfile.TemporaryDirectory() as tmpdir:
        cnf_path = os.path.join(tmpdir, "output.cnf")
        with open(cnf_path, "w") as fd:
            f.WriteCNF(fd)
        with open(cnf_path, "r") as fd:
            dimacs = fd.read()
    assignments = kissat.solve(dimacs)
    if result is None:
        print("failed to solve")
        return
    
    def eval_binary(binary_vars: List):
        result = 0
        for i, var in enumerate(binary_vars.exprs):
            result *= 2
            result += int(assignments[var.name])
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

    problem_name = "quintus"
    # problem_name = "random_full_8_1_42"
    if problem_name in problem_names():
        single_rooms, duplication_factor = problem_names()[problem_name]
    else:
        single_rooms = 8
        duplication_factor = 1
    num_rooms = single_rooms * duplication_factor

    while True:
        client.select(problem_name)

        plan_count = 1
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
            break



if __name__ == "__main__":
    main()

