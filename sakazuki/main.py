from aedificium import Aedificium, problem_names, parse_plan, Action
import api
import random
from typing import List
import kissat
import tempfile
import os
import itertools

import cnfc


def solve(single_rooms: int, duplication_factor: int, plans: List[str], results: List[str]):
    num_rooms = single_rooms * duplication_factor
    f = cnfc.Formula()
    
    m = len(plans)
    write_plans, move_plans = [], []
    for plan in plans:
        parsed_plan = parse_plan(plan)
        last_write = None
        write_plan, move_plan = [], []
        for action, payload in parsed_plan:
            if action == Action.USE_CHARCOAL:
                last_write = payload
            else:
                write_plan.append(last_write)  # Noneでも許可
                move_plan.append(payload)
                last_write = None
        write_plans.append(write_plan)
        move_plans.append(move_plan)
    move_results = []
    for result, plan in zip(results, plans):
        move_result = [result[0]]
        parsed_plan = parse_plan(plan)
        for r, p in zip(result[1:], parsed_plan):
            if p[0] == Action.MOVE:
                move_result.append(r)
        move_results.append(move_result)
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
        for i in range(len(move_plans[plan_index]) + 1):
            room_var = create_intvar(f"room_history_{plan_index}_{i}", num_rooms)
            plan_xs.append(room_var)
        xs.append(plan_xs)

    # label history - 各プラン・各時点での各部屋のラベル
    label_histories = []
    for plan_index, move_plan in enumerate(move_plans):
        plan_label_histories = []
        for room_index in range(num_rooms):
            plan_label_history = []
            for tick in range(len(move_plan) + 1):
                plan_label_history.append(create_intvar(f"label_history_{plan_index}_{room_index}_{tick}", 4))
            plan_label_histories.append(plan_label_history)
        label_histories.append(plan_label_histories)

    # 部屋が重複無しで本来どの部屋だったか変数
    original_room_vars = []
    for room_id in range(num_rooms):
        original_room_vars.append(create_intvar(f"original_room_{room_id}", single_rooms))

    # 各部屋の重複数の制約
    for original_room_id in range(single_rooms):
        props = []
        for room_id in range(num_rooms):
            props.append(original_room_vars[room_id] == original_room_id)
        f.Add(cnfc.NumTrue(*props) == duplication_factor)

    # 初期時点での部屋のラベルの制約 (modのやつ / 最初は同じ)
    for plan_index in range(m):
        for room_id in range(num_rooms):
            f.Add(label_histories[plan_index][room_id][0] == original_room_vars[room_id] % 4)
            f.Add(label_histories[plan_index][room_id][0] == label_histories[0][room_id][0])

    # 開始部屋
    # starting_room = 0
    for plan_index in range(m):
        f.Add(xs[plan_index][0] == xs[0][0])

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
        single_write_plan = write_plans[plan_index]
        single_move_plan = move_plans[plan_index]
        single_move_result = move_results[plan_index]
        for tick, current_label in enumerate(single_move_result):
            # ラベルの出力制約
            current_room = single_xs[tick]
            for room_id in range(num_rooms):
                condition = current_room == room_id
                consequence = label_histories[plan_index][room_id][tick] == int(current_label)
                f.Add(cnfc.Implies(condition, consequence))

            if tick == len(single_move_plan):
                continue

            write_plan = single_write_plan[tick]
            # action 1: write <write_plan> on xs[plan_index][tick]
            for room_id in range(num_rooms):
                condition = current_room == room_id
                if write_plan is not None:
                    true_consequence = label_histories[plan_index][room_id][tick + 1] == write_plan
                    false_consequence = label_histories[plan_index][room_id][tick + 1] == label_histories[plan_index][room_id][tick]
                    f.Add(cnfc.If(condition, true_consequence, false_consequence))
                else:
                    # write_planがNoneの場合、ラベルは変化しない
                    f.Add(cnfc.Implies(condition, label_histories[plan_index][room_id][tick + 1] == label_histories[plan_index][room_id][tick]))

            move_plan = single_move_plan[tick]
            # action 2: move xs[plan_index][tick] to xs[plan_index][tick + 1]
            door_id = move_plan
            from_room_intvar = single_xs[tick]
            to_room_intvar = single_xs[tick + 1]
            
            # 各部屋からの遷移制約
            for room_id in range(num_rooms):
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

    # 部屋が区別できないことの制約
    for room1, room2 in itertools.combinations(range(num_rooms), 2):
        source_condition = (original_room_vars[room1] == original_room_vars[room2])
        for door_id in range(6):
            dest1_var = door_destinations[(room1, door_id)]
            dest2_var = door_destinations[(room2, door_id)]
            
            # dest1_var == dest_room1 かつ dest2_var == dest_room2 なら
            # original_room_vars[dest_room1] == original_room_vars[dest_room2]
            for dest_room1 in range(num_rooms):
                for dest_room2 in range(num_rooms):
                    dest_condition = cnfc.And(dest1_var == dest_room1, dest2_var == dest_room2)
                    condition = cnfc.And(source_condition, dest_condition)
                    consequence = original_room_vars[dest_room1] == original_room_vars[dest_room2]
                    f.Add(cnfc.Implies(condition, consequence))
        

    # SATとして解く
    with tempfile.TemporaryDirectory() as tmpdir:
        cnf_path = os.path.join(tmpdir, "output.cnf")
        with open(cnf_path, "w") as fd:
            f.WriteCNF(fd)
        with open(cnf_path, "r") as fd:
            dimacs = fd.read()
    assignments = kissat.solve(dimacs)
    if assignments is None:
        print("failed to solve")
        return
    
    # 解の復元
    def eval_binary(binary_vars: List):
        result = 0
        for i, var in enumerate(binary_vars.exprs):
            result *= 2
            result += int(assignments[var.name])
        return result
    
    rooms = [i % 4 for i in range(num_rooms)]
    starting_room_val = eval_binary(xs[0][0])  # 既に0に固定されている
    
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

    # problem_name = "secundus"
    problem_name = "random_full_2_3_42"
    if problem_name in problem_names():
        single_rooms, duplication_factor = problem_names()[problem_name]
    else:
        single_rooms = 2
        duplication_factor = 3
    num_rooms = single_rooms * duplication_factor

    while True:
        client.select(problem_name)

        plan_count = 24
        def generate_plan():
            plan = []
            for _ in range(num_rooms * 6):
                # plan.append(random.choice([f"[{x}]" for x in range(4)]))
                plan.append(random.choice([str(x) for x in range(6)]))
            return ''.join(plan)
        plans = [generate_plan() for _ in range(plan_count)]

        results_ints = client.explore(plans)["results"]
        results = [''.join(map(str, result_ints)) for result_ints in results_ints]

        estimated_aedificium = solve(single_rooms, duplication_factor, plans, results)
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

