import api
import random
import math
import copy
import multiprocessing
import os
from typing import List, Dict, Any, Tuple
from aedificium import Aedificium, create_random_aedificium, reconstruct_aedificium
from collections import Counter, defaultdict, namedtuple
from statistics import mean

from beam_search import BeamSearch


def list_ngram_hashes(s: List[int], n: int) -> List[int]:
    """
    List[int]をngramのhash値のList[List[int]]に変換する
    """
    # use rolling hash
    hash_value = 0
    hashes = []
    p = 11
    mod = 998244353
    inv_p = pow(p, mod - 2, mod)
    for i, x in enumerate(s):
        hash_value = (hash_value * p + x) % mod
        if i >= n - 1:
            hashes.append(hash_value)
            hash_value = ((hash_value - s[i - n + 1]) % mod * inv_p) % mod
    return hashes


def compare_ngram_sets(seq1: List[int], seq2: List[int], ngram_length: int) -> float:
    """
    ngramのhash値の集合を比較する

    smaller is similar
    """

    hashes1 = list_ngram_hashes(seq1, ngram_length)
    hashes2 = list_ngram_hashes(seq2, ngram_length)

    jaccard_similarity = len(set(hashes1).intersection(set(hashes2))) / len(set(hashes1).union(set(hashes2)))
    return 1 - jaccard_similarity

    
def evaluate_fitness(room_history: List[int], result: List[int], plan: str, num_rooms: int) -> float:
    """
    評価関数
    
    Args:
        room_history: 部屋IDの履歴
        result: 目標となる探索結果
        plan: 使用するプラン
        num_rooms: 部屋数
    Returns:
        float: 類似度のコスト（小さいほど類似）
    """

    plan_ints = [int(p) for p in plan]
    door_destinations = {}
    incoming_doors = [set() for _ in range(num_rooms)]
    doors_by_room_pair = defaultdict(set)
    door_conflicts = 0  # ドア接続の競合数をカウント
    for room_from, plan_int, room_to in zip(room_history[:-1], plan_ints, room_history[1:]):
        door = (room_from, plan_int)
        if door in door_destinations and door_destinations[door] != room_to:
            door_conflicts += 1
            continue
        door_destinations[door] = room_to
        incoming_doors[room_to].add(door)
        doors_by_room_pair[(room_from, room_to)].add(door)

    used_doors = set()
    for room_a in range(num_rooms):
        for room_b in range(room_a + 1, num_rooms):
            atob = list(doors_by_room_pair[(room_a, room_b)])
            btoa = list(doors_by_room_pair[(room_b, room_a)])

            for door_a, door_b in zip(atob, btoa):
                used_doors.add(door_a)
                used_doors.add(door_b)

            if len(atob) > len(btoa):            
                for i in range(len(btoa), len(atob)):
                    for door_id in range(6):
                        incoming_door = atob[i]
                        outgoing_door = (room_b, door_id)
                        if outgoing_door in used_doors:
                            continue
                        incoming_room = room_a
                        other_room = door_destinations.get(outgoing_door, incoming_room)
                        if other_room != incoming_room:
                            continue
                        used_doors.add(incoming_door)
                        used_doors.add(outgoing_door)
                        break  # 1つの incoming_door につき1つの接続のみ
                    door_conflicts += 1
            else:
                for i in range(len(atob), len(btoa)):
                    for door_id in range(6):
                        incoming_door = btoa[i]
                        outgoing_door = (room_a, door_id)
                        if outgoing_door in used_doors:
                            continue
                        incoming_room = room_b
                        other_room = door_destinations.get(outgoing_door, incoming_room)
                        if other_room != incoming_room:
                            continue
                        used_doors.add(incoming_door)
                        used_doors.add(outgoing_door)
                        break  # 1つの incoming_door につき1つの接続のみ
                    door_conflicts += 1


    # for room_id, incoming_door_set in enumerate(incoming_doors):
    #     for incoming_door in incoming_door_set:
    #         if incoming_door in used_doors:
    #             continue
    #         for door_id in range(6):
    #             # TODO: 既にドアがあったらそれを使ってほしい
                

    #             outgoing_door = (room_id, door_id)
    #             if outgoing_door in used_doors:
    #                 continue
    #             incoming_room = incoming_door[0]
    #             other_room = door_destinations.get(outgoing_door, incoming_room)
    #             if other_room != incoming_room:
    #                 continue
    #             used_doors.add(incoming_door)
    #             used_doors.add(outgoing_door)
    #             break  # 1つの incoming_door につき1つの接続のみ
    #         # door_conflicts += 1

    return door_conflicts / len(room_history)

def mutate_one_element(room_history: List[int], plan: str, num_rooms: int) -> List[int]:
    """
    ランダムな要素を変更
    """
    index = random.randrange(0, len(room_history))
    room_id = room_history[index]
    new_room_id = random.randrange(0, num_rooms)
    new_room_id = new_room_id // 4 * 4 + room_id % 4
    if new_room_id >= num_rooms:
        new_room_id -= 4

    updated = room_history[:]
    updated[index] = new_room_id
    return updated

def resolve_conflict(room_history: List[int], plan: str, num_rooms: int) -> List[int]:
    plan_ints = [int(p) for p in plan]
    door_destinations = {}
    incoming_doors = [set() for _ in range(num_rooms)]
    door_conflicts = 0  # ドア接続の競合数をカウント
    index_candidates = []
    for i, (room_from, plan_int, room_to) in enumerate(zip(room_history[:-1], plan_ints, room_history[1:])):
        door = (room_from, plan_int)
        if door in door_destinations and door_destinations[door][3] != room_to:
            index_candidates.append(i)
            index_candidates.append(i + 1)
            index_candidates.append(door_destinations[door][0])
            index_candidates.append(door_destinations[door][0] + 1)
            continue
        door_destinations[door] = (i, room_from, plan_int, room_to)
        incoming_doors[room_to].add(door)
    
    index = index_candidates[random.randrange(0, len(index_candidates))]

    room_id = room_history[index]
    new_room_id = random.randrange(0, num_rooms)
    new_room_id = new_room_id // 4 * 4 + room_id % 4
    if new_room_id >= num_rooms:
        new_room_id -= 4

    updated = room_history[:]
    updated[index] = new_room_id

    return updated

def resolve_overflow(room_history: List[int], plan: str, num_rooms: int) -> List[int]:
    plan_ints = [int(p) for p in plan]
    incoming_doors = [set() for _ in range(num_rooms)]
    door_to_index = defaultdict(list)
    for i, (room_from, plan_int, room_to) in enumerate(zip(room_history[:-1], plan_ints, room_history[1:])):
        door = (room_from, plan_int)
        door_to_index[door].append(i + 1)
        incoming_doors[room_to].add(door)
    
    door_candidates = []
    for incoming_door in incoming_doors:
        if len(incoming_door) > 6:
            door_candidates.extend(incoming_door)
    
    door = door_candidates[random.randrange(0, len(door_candidates))]

    updated = room_history[:]
    for index in door_to_index[door]:
        room_id = room_history[index]
        new_room_id = random.randrange(0, num_rooms)
        new_room_id = new_room_id // 4 * 4 + room_id % 4
        if new_room_id >= num_rooms:
            new_room_id -= 4

        updated[index] = new_room_id

    return updated

def get_random_mutation(room_history: List[int], plan: str, num_rooms: int) -> List[int]:
        """
        ランダムな局所変更を適用（制約を満たす場合のみ）
        
        Args:
            room_history: 変更対象の部屋IDの履歴
            
        Returns:
            List[int]: 変更後の部屋IDの履歴
        """
        mutation_functions = [
            mutate_one_element,
            resolve_conflict,
            resolve_overflow
        ]
        
        mutation_func = random.choices(mutation_functions, weights=[1, 2, 3])[0]
        return mutation_func(room_history, plan, num_rooms)


def solve_with_seed(args):
    """
    並列実行用のsolve関数ラッパー
    各プロセスで異なる乱数状態を初期化する
    
    Args:
        args: (process_id, target_result, plan, num_rooms, max_iterations, initial_temp, terminal_temp)
        
    Returns:
        Tuple[List[int], int]: (推定された部屋IDの履歴, 適合度)
    """
    process_id, target_result, plan, num_rooms, max_iterations, initial_temp, terminal_temp = args
    
    # 各プロセスで異なる乱数シードを設定
    # プロセスIDとプロセス固有の値を組み合わせてシードを作成
    seed = (os.getpid() * 1000 + process_id) % (2**32)
    random.seed(seed)
    
    print(f"プロセス {process_id} (PID: {os.getpid()}): 乱数シード = {seed}")
    
    # solve関数を実行
    solution = solve(target_result, plan, num_rooms, max_iterations, initial_temp, terminal_temp)
    #solution = try_solve_beam(target_result, plan, num_rooms)
    fitness = evaluate_fitness(solution, target_result, plan, num_rooms)
    
    return solution, fitness


def solve(target_result: List[int], plan: str, num_rooms: int, 
          max_iterations: int = 10000, initial_temp: float = 100.0, 
          terminal_temp: float = 0.01) -> List[int]:
        """
        焼きなまし法でAedificiumを推定
        
        Args:
            target_result: 目標となる探索結果
            plan: 使用するプラン
            num_rooms: 部屋数
            max_iterations: 最大反復回数
            initial_temp: 初期温度
            terminal_temp: 終了温度
            
        Returns:
            List[int]: 推定された部屋IDの履歴
        """
        print("焼きなまし法による探索を開始...")
        
        # ラベル列を初期解として採用
        current_solution = target_result[:]
        
        current_fitness = evaluate_fitness(current_solution, target_result, plan, num_rooms)
        
        best_solution = copy.deepcopy(current_solution)
        best_fitness = current_fitness
        
        # 指数関数による温度低減のパラメータを計算
        # T(t) = initial_temp * exp(-α * t / max_iterations)
        # terminal_temp = initial_temp * exp(-α) より α = -ln(terminal_temp / initial_temp)
        alpha = -math.log(terminal_temp / initial_temp)
        
        temperature = initial_temp
        
        print(f"初期解のコスト: {current_fitness}")
        print(f"温度設定: 初期={initial_temp}, 終了={terminal_temp}, α={alpha:.6f}")
        
        for iteration in range(max_iterations):
            # 局所変更を適用
            new_solution = get_random_mutation(current_solution, plan, num_rooms)
            new_fitness = evaluate_fitness(new_solution, target_result, plan, num_rooms)
            
            # 適合度の差を計算（最小化問題）
            delta = new_fitness - current_fitness
            
            # 受容判定
            accept = False
            if delta < 0:
                # 改善した場合（値が小さくなった）は受容
                accept = True
            elif temperature > 0:
                # 悪化した場合は確率的に受容
                probability = math.exp(-delta / temperature)
                accept = random.random() < probability
            
            if accept:
                current_solution = new_solution
                current_fitness = new_fitness
                
                # 最良解の更新（最小化問題）
                if current_fitness < best_fitness:
                    best_solution = copy.deepcopy(current_solution)
                    best_fitness = current_fitness
                    print(f"反復 {iteration}: 新しい最良解 コスト={best_fitness}")
            
            # 温度を指数関数で下げる
            progress = (iteration + 1) / max_iterations
            temperature = initial_temp * math.exp(-alpha * progress)
            
            # 進捗表示
            if iteration % 1000 == 0:
                print(f"反復 {iteration}: 現在のコスト={current_fitness}, 最良コスト={best_fitness}, 温度={temperature:.4f}")
            
            # 完全一致した場合は早期終了（コスト0）
            if best_fitness == 0:
                print(f"完全一致を発見！反復 {iteration}で終了")
                break
        
        print(f"焼きなまし法完了。最終コスト: {best_fitness}")
        return best_solution


def collect_target_data(api_client: api.APIClient, problem_name: str, plan_length: int) -> Tuple[List[int], str]:
    """
    目標となるデータを収集する
    
    Args:
        api_client: APIクライアント
        num_rooms: 部屋数
        plan_length: プランの長さ
        
    Returns:
        Tuple[List[int], str]: (探索結果, プラン)
    """
    api_client.select(problem_name)
    
    # 長さplan_lengthのランダムなプランを生成
    plan = ''.join([str(random.randint(0, 5)) for _ in range(plan_length)])
    print(f"プラン生成: {plan[:20]}... (長さ: {len(plan)})")
    
    # 探索実行
    result = api_client.explore([plan])
    target_result = result["results"][0]
    
    print(f"探索完了。結果の長さ: {len(target_result)}")
    print(f"結果の最初の10要素: {target_result[:10]}")
    
    return target_result, plan


def try_solve():
    """メイン関数"""
    # APIクライアントを作成
    api_base, api_id = "http://localhost:8000", "esports_complex"  # ローカルテスト用
    # api_base, api_id = (
    #     "https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com", 
    #     "amylase.inquiry@gmail.com X6G0RVKUlX20I8XSUsnkIQ"
    # )  # 本番用

    client = api.create_client(api_base=api_base, api_id=api_id)
    
    problem_name = "secundus"
    num_rooms = 12
    problem_name = f"random_room_size_{num_rooms}"
    plan_length = num_rooms * 18
    
    # 目標データを収集
    target_result, plan = collect_target_data(client, problem_name, plan_length)
    
    # 並列実行のパラメータ設定
    num_processes = max(multiprocessing.cpu_count() - 1, 1)  # CPUコア数に基づいて並列度を決定
    
    print(f"並列実行開始: {num_processes}プロセス")
    
    # 各プロセス用の引数を準備
    process_args = []
    for i in range(num_processes):
        args = (
            i,  # process_id
            target_result,
            plan, 
            num_rooms,
            400000,
            1e-2,  # initial_temp
            1e-5,   # terminal_temp
        )
        process_args.append(args)
    
    # 並列実行
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.map(solve_with_seed, process_args)
    
    # 最良の結果を選択（最小化問題）
    best_solution = None
    best_fitness = float('inf')
    
    for i, (solution, fitness) in enumerate(results):
        print(f"プロセス {i}: コスト = {fitness}")
        if fitness < best_fitness:
            best_solution = solution
            best_fitness = fitness
    
    estimated_room_history = best_solution
    
    print(f"\n=== 並列実行結果 ===")
    print(f"最良解: {best_solution}")
    print(f"最良解のコスト: {best_fitness}")
    print(f"使用したプロセス数: {num_processes}")    
    # 最終的なコストを確認（並列実行で得られた最良コストを使用）
    final_fitness = best_fitness
    print(f"最終コスト: {final_fitness}")

    print("\n復元を開始します")
    estimated_aedificium = reconstruct_aedificium(plan, target_result, estimated_room_history, num_rooms)
    if estimated_aedificium is None:
        print("復元に失敗しました")
        return False

    print("\n=== 復元結果 ===")
    print(f"部屋ラベル: {estimated_aedificium.rooms}")
    print(f"開始部屋: {estimated_aedificium.starting_room}")
    print(f"接続数: {len(estimated_aedificium.connections)}")

    # 自己閉路の数をカウント
    self_loops = sum(1 for conn in estimated_aedificium.connections 
                    if (conn["from"]["room"] == conn["to"]["room"] and 
                        conn["from"]["door"] == conn["to"]["door"]))
    print(f"自己閉路数: {self_loops}")
    print(f"通常接続数: {len(estimated_aedificium.connections) - self_loops}")

    print("サーバーに推測を提出します")
    guess_response = client.guess(estimated_aedificium.to_dict())
    print(guess_response)
    return guess_response["correct"]

BeamState = namedtuple("BeamState", ["state", "hash", "score"])

def calc_hash(room_history: List[int]) -> int:
    v = 0
    for r in room_history:
        v *= 1000000009
        v += r
        v %= 1000000009
    return v

def expand_beam(room_history: List[int], plan: str, target_result: List[int], num_rooms: int) -> BeamState:
    mutation_functions = [
        resolve_conflict,
        resolve_overflow,
    ]

    res = []
    for func in mutation_functions:
      new_state = func(room_history, plan, num_rooms)
      new_score = evaluate_fitness(new_state, target_result, plan, num_rooms)
      res.append(BeamState(new_state, calc_hash(new_state), new_score))

    for _ in range(50):
        sample_size = random.randrange(1, 10)
        indices = random.sample(range(len(room_history)), sample_size)
        updated = room_history[:]
        for index in indices:
            room_id = room_history[index]
            new_room_id = random.randrange(0, num_rooms)
            new_room_id = new_room_id // 4 * 4 + room_id % 4
            if new_room_id >= num_rooms:
                new_room_id -= 4
            updated[index] = new_room_id
        score = evaluate_fitness(updated, target_result, plan, num_rooms)
        res.append(BeamState(updated, calc_hash(updated), score))

    return res

def try_solve_beam(target_result: List[int], plan: str, num_rooms: int):
    beam_search = BeamSearch[BeamState](
        beam_size=100,
        max_steps=100000,
        key=lambda x: x.hash
    )

    initial_states = []
    for _ in range(100):
        room_history = []
        for i, label in enumerate(target_result):
            room_id = random.randrange(0, num_rooms // 4) * 4 + label
            if room_id >= num_rooms:
                room_id -= 4
            room_history.append(room_id)
        score = evaluate_fitness(room_history, target_result, plan, num_rooms),
        initial_states.append(BeamState(room_history, calc_hash(room_history), score))

    res = beam_search.run(
        initial_states=initial_states,
        expand=lambda s: expand_beam(s.state, plan, target_result, num_rooms),
        score=lambda s: s.score,
        is_goal=lambda s: s.score == 0
    )
    return res

def main():
    # while True:
    #     if try_solve():
    #         break
    #     else:
    #         print("推測に失敗しました。再度試行します。")
    try_solve()


if __name__ == "__main__":
    # multiprocessingのためのメイン実行ブロック
    multiprocessing.set_start_method('spawn', force=True)  # macOSでの互換性のため
    main()