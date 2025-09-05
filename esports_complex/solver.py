import api
import random
import math
import copy
import multiprocessing
import os
from typing import List, Dict, Any, Tuple
from aedificium import Aedificium, create_random_aedificium
from collections import Counter
from statistics import mean


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


def validate_constraints(aedificium: Aedificium) -> bool:
    """
    全ドア1回使用の制約をチェックする
    
    Args:
        aedificium: チェック対象のAedificium
        
    Returns:
        bool: 制約を満たしている場合True
    """
    num_rooms = len(aedificium.rooms)
    used_doors = set()
    
    for conn in aedificium.connections:
        from_door = (conn["from"]["room"], conn["from"]["door"])
        to_door = (conn["to"]["room"], conn["to"]["door"])
        
        # 既に使われているドアがないかチェック
        if from_door in used_doors or to_door in used_doors:
            return False
            
        used_doors.add(from_door)
        used_doors.add(to_door)
    
    # 全てのドア（各部屋の0-5）が使われているかチェック
    expected_doors = set()
    for room in range(num_rooms):
        for door in range(6):
            expected_doors.add((room, door))
    
    return used_doors == expected_doors
    
def evaluate_fitness(aedificium: Aedificium, target_result: List[int], plan: str) -> float:
    """
    評価関数
    
    Args:
        aedificium: 評価対象のAedificium
        target_result: 目標となる探索結果
        plan: 使用するプラン
        
    Returns:
        float: 類似度のコスト（小さいほど類似）
    """
    # 同じプランでシミュレーション実行
    try:
        simulated_result = aedificium._execute_plan(plan)

        
        mixed_target_result = []
        mixed_simulated_result = []
        for i in range(len(target_result)):
            mixed_target_result.append(target_result[i])
            mixed_simulated_result.append(simulated_result[i])
            if i < len(plan):
                mixed_target_result.append(int(plan[i]) + 4)
                mixed_simulated_result.append(int(plan[i]) + 4)

        position_mismatch_ratio = len([i for i in range(len(target_result)) if target_result[i] != simulated_result[i]]) / len(target_result)
        scores = [position_mismatch_ratio]
        for ngram_length in [3, 5]:
            hash_set_distance = compare_ngram_sets(mixed_target_result, mixed_simulated_result, ngram_length)
            scores.append(hash_set_distance)
        return mean(scores)
    except Exception:
        # エラーが発生した場合は最悪評価（大きな値）
        return float('inf')
    
def mutate_room_label(aedificium: Aedificium) -> Aedificium:
        """
        局所変更：2つの部屋のラベル（2bit整数）をスワップ
        
        Args:
            aedificium: 変更対象のAedificium
            
        Returns:
            Aedificium: 変更後のAedificium
        """
        new_aed = copy.deepcopy(aedificium)
        
        # 部屋が2つ未満の場合は変更しない
        if len(new_aed.rooms) < 2:
            return new_aed
        
        # 異なる2つの部屋をランダムに選択
        room1_idx = random.randint(0, len(new_aed.rooms) - 1)
        room2_idx = random.randint(0, len(new_aed.rooms) - 1)
        
        # 同じ部屋が選ばれた場合は別の部屋を選択
        while room2_idx == room1_idx:
            room2_idx = random.randint(0, len(new_aed.rooms) - 1)
        
        # 2つの部屋のラベルをスワップ
        new_aed.rooms[room1_idx], new_aed.rooms[room2_idx] = new_aed.rooms[room2_idx], new_aed.rooms[room1_idx]
        
        # 接続マップを再構築
        new_aed._connection_map = new_aed._build_connection_map()
        
        return new_aed
    
def mutate_connection_swap(aedificium: Aedificium) -> Aedificium:
        """
        局所変更：2つの接続を選び、それらのエンドポイントを入れ替える
        全ドア1回使用の制約を維持する
        
        Args:
            aedificium: 変更対象のAedificium
            
        Returns:
            Aedificium: 変更後のAedificium
        """
        new_aed = copy.deepcopy(aedificium)
        
        if len(new_aed.connections) < 2:
            return new_aed
        
        # 2つの接続をランダムに選択
        conn1_idx = random.randint(0, len(new_aed.connections) - 1)
        conn2_idx = random.randint(0, len(new_aed.connections) - 1)
        
        if conn1_idx == conn2_idx:
            return new_aed  # 同じ接続の場合は変更しない
        
        conn1 = new_aed.connections[conn1_idx]
        conn2 = new_aed.connections[conn2_idx]
        
        # 4つのエンドポイントを取得
        endpoints = [
            conn1["from"], conn1["to"], 
            conn2["from"], conn2["to"]
        ]
        
        # エンドポイントをシャッフルして再配置
        random.shuffle(endpoints)
        
        # 新しい2つの接続を作成
        new_aed.connections[conn1_idx] = {
            "from": endpoints[0],
            "to": endpoints[1]
        }
        new_aed.connections[conn2_idx] = {
            "from": endpoints[2], 
            "to": endpoints[3]
        }
        
        # 接続マップを再構築
        new_aed._connection_map = new_aed._build_connection_map()
        
        return new_aed
    
def mutate_self_loop_to_connection(aedificium: Aedificium) -> Aedificium:
        """
        局所変更：自己閉路を2つ選び、それらに変わり、閉路があった2点を結ぶ
        
        Args:
            aedificium: 変更対象のAedificium
            
        Returns:
            Aedificium: 変更後のAedificium
        """
        new_aed = copy.deepcopy(aedificium)
        
        # 自己閉路を見つける
        self_loops = []
        for i, conn in enumerate(new_aed.connections):
            if (conn["from"]["room"] == conn["to"]["room"] and 
                conn["from"]["door"] == conn["to"]["door"]):
                self_loops.append(i)
        
        if len(self_loops) < 2:
            return new_aed  # 自己閉路が2つ未満の場合は変更しない
        
        # 2つの自己閉路をランダムに選択
        loop1_idx = random.choice(self_loops)
        remaining_loops = [idx for idx in self_loops if idx != loop1_idx]
        loop2_idx = random.choice(remaining_loops)
        
        # 自己閉路の情報を取得
        loop1_room = new_aed.connections[loop1_idx]["from"]["room"]
        loop1_door = new_aed.connections[loop1_idx]["from"]["door"]
        loop2_room = new_aed.connections[loop2_idx]["from"]["room"]
        loop2_door = new_aed.connections[loop2_idx]["from"]["door"]
        
        # 新しい接続を作成（2つの部屋を結ぶ）
        new_connection = {
            "from": {"room": loop1_room, "door": loop1_door},
            "to": {"room": loop2_room, "door": loop2_door}
        }
        
        # 古い自己閉路を削除（インデックスの大きい方から削除）
        indices_to_remove = sorted([loop1_idx, loop2_idx], reverse=True)
        for idx in indices_to_remove:
            del new_aed.connections[idx]
        
        # 新しい接続を追加
        new_aed.connections.append(new_connection)
        
        # 接続マップを再構築
        new_aed._connection_map = new_aed._build_connection_map()
        
        return new_aed
    
def mutate_connection_to_self_loops(aedificium: Aedificium) -> Aedificium:
        """
        局所変更：自己閉路でないものを1つ選び、それに変わり、それぞれのfrom, toに自己閉路を追加
        
        Args:
            aedificium: 変更対象のAedificium
            
        Returns:
            Aedificium: 変更後のAedificium
        """
        new_aed = copy.deepcopy(aedificium)
        
        # 自己閉路でない接続を見つける
        non_self_loops = []
        for i, conn in enumerate(new_aed.connections):
            if not (conn["from"]["room"] == conn["to"]["room"] and 
                   conn["from"]["door"] == conn["to"]["door"]):
                non_self_loops.append(i)
        
        if not non_self_loops:
            return new_aed  # 自己閉路でない接続がない場合は変更しない
        
        # ランダムに1つ選択
        conn_idx = random.choice(non_self_loops)
        conn = new_aed.connections[conn_idx]
        
        # 接続情報を取得
        from_room = conn["from"]["room"]
        from_door = conn["from"]["door"]
        to_room = conn["to"]["room"]
        to_door = conn["to"]["door"]
        
        # 2つの自己閉路を作成
        self_loop1 = {
            "from": {"room": from_room, "door": from_door},
            "to": {"room": from_room, "door": from_door}
        }
        self_loop2 = {
            "from": {"room": to_room, "door": to_door},
            "to": {"room": to_room, "door": to_door}
        }
        
        # 古い接続を削除
        del new_aed.connections[conn_idx]
        
        # 新しい自己閉路を追加
        new_aed.connections.extend([self_loop1, self_loop2])
        
        # 接続マップを再構築
        new_aed._connection_map = new_aed._build_connection_map()
        
        return new_aed
    
def get_random_mutation(aedificium: Aedificium) -> Aedificium:
        """
        ランダムな局所変更を適用（制約を満たす場合のみ）
        
        Args:
            aedificium: 変更対象のAedificium
            
        Returns:
            Aedificium: 変更後のAedificium
        """
        mutation_functions = [
            mutate_room_label,
            mutate_connection_swap,
            mutate_self_loop_to_connection,
            mutate_connection_to_self_loops
        ]
        
        # 最大10回試行して制約を満たす変更を見つける
        for _ in range(10):
            # ランダムに変更方法を選択
            mutation_func = random.choices(mutation_functions, weights=[1, 17, 1, 1])[0]
            candidate = mutation_func(aedificium)
            
            # 制約をチェック
            if validate_constraints(candidate):
                return candidate
        
        # 制約を満たす変更が見つからない場合は元の解を返す
        return aedificium


def solve_with_seed(args):
    """
    並列実行用のsolve関数ラッパー
    各プロセスで異なる乱数状態を初期化する
    
    Args:
        args: (process_id, target_result, plan, num_rooms, max_iterations, initial_temp, terminal_temp)
        
    Returns:
        Tuple[Aedificium, int]: (推定されたAedificium, 適合度)
    """
    process_id, target_result, plan, num_rooms, max_iterations, initial_temp, terminal_temp = args
    
    # 各プロセスで異なる乱数シードを設定
    # プロセスIDとプロセス固有の値を組み合わせてシードを作成
    seed = (os.getpid() * 1000 + process_id) % (2**32)
    random.seed(seed)
    
    print(f"プロセス {process_id} (PID: {os.getpid()}): 乱数シード = {seed}")
    
    # solve関数を実行
    solution = solve(target_result, plan, num_rooms, max_iterations, initial_temp, terminal_temp)
    fitness = evaluate_fitness(solution, target_result, plan)
    
    return solution, fitness


def solve(target_result: List[int], plan: str, num_rooms: int = 3, 
          max_iterations: int = 10000, initial_temp: float = 100.0, 
          terminal_temp: float = 0.01) -> Aedificium:
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
            Aedificium: 推定されたAedificium
        """
        print("焼きなまし法による探索を開始...")
        
        # 初期解をランダム生成（制約を満たすまで繰り返し）
        current_solution = None
        for attempt in range(100):
            candidate = create_random_aedificium(num_rooms)
            if validate_constraints(candidate):
                current_solution = candidate
                break
        
        if current_solution is None:
            raise RuntimeError("制約を満たす初期解が生成できませんでした")
        
        current_fitness = evaluate_fitness(current_solution, target_result, plan)
        
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
            new_solution = get_random_mutation(current_solution)
            new_fitness = evaluate_fitness(new_solution, target_result, plan)
            
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
    num_rooms = 6
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
    
    estimated_aedificium = best_solution
    
    print(f"\n=== 並列実行結果 ===")
    print(f"最良解のコスト: {best_fitness}")
    print(f"使用したプロセス数: {num_processes}")
    
    print("\n=== 推定結果 ===")
    print(f"部屋ラベル: {estimated_aedificium.rooms}")
    print(f"開始部屋: {estimated_aedificium.starting_room}")
    print(f"接続数: {len(estimated_aedificium.connections)}")

    # 自己閉路の数をカウント
    self_loops = sum(1 for conn in estimated_aedificium.connections 
                     if (conn["from"]["room"] == conn["to"]["room"] and 
                         conn["from"]["door"] == conn["to"]["door"]))
    print(f"自己閉路数: {self_loops}")
    print(f"通常接続数: {len(estimated_aedificium.connections) - self_loops}")
    
    # 最終的なコストを確認（並列実行で得られた最良コストを使用）
    final_fitness = best_fitness
    print(f"最終コスト: {final_fitness}")

    if final_fitness == 0:
        print("最終コストが0になりました（完全一致）")
        print("サーバーに推測を提出します")
        guess_response = client.guess(estimated_aedificium.to_dict())
        print(guess_response)
        return guess_response["correct"]
    else:
        print("最終コストが0になりませんでした")
        return False


def main():
    while True:
        if try_solve():
            break
        else:
            print("推測に失敗しました。再度試行します。")


if __name__ == "__main__":
    # multiprocessingのためのメイン実行ブロック
    multiprocessing.set_start_method('spawn', force=True)  # macOSでの互換性のため
    main()