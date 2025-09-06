import random
import multiprocessing
import os
from dataclasses import dataclass
from typing import List
from pathlib import Path
import subprocess

from aedificium import Aedificium, build_connections
import api


@dataclass
class ProblemConfig:
    problem_name: str
    num_rooms: int

@dataclass
class Explore:
    plan: str
    result: List[int]


def ensure_binary():
    subprocess.run(["make", "solve.exe"], check=True, cwd=Path(__file__).parent)


def solve(args) -> Aedificium | None:
    """
    並列実行用のsolve関数ラッパー
    各プロセスで異なる乱数状態を初期化する
    
    Args:
        args: (process_id, problem_config, explore)
        
    Returns:
        Tuple[List[int], int]: (推定された部屋IDの履歴, 適合度)
    """
    process_id, problem_config, explore = args
    
    print(f"プロセス {process_id} (PID: {os.getpid()}): 問題 = {problem_config}")
    
    # call c++ binary
    binary_path = Path(__file__).parent / "solve.exe"
    # subprocess feed input
    input_data = f"""\
{problem_config.num_rooms}
{explore.plan}
{''.join(map(str, explore.result))}
"""
    result = subprocess.check_output([binary_path, str(problem_config.num_rooms)], text=True, input=input_data)
    
    output_lines = result.splitlines()
    solution_line = None
    for i, line in enumerate(output_lines):
        if "solved" in line:
            solution_line = output_lines[i - 1]
            break
    if solution_line is None:
        print("焼きなましが解を見つけられませんでした")
        return None
    solution = [int(x) for x in solution_line.split()]
    # reconstruct Aedificium
    rooms = [i % 4 for i in range(problem_config.num_rooms)]
    starting_room = 0
    door_destinations = {}
    for room_id in range(problem_config.num_rooms):
        for door_id in range(6):
            door_destinations[(room_id, door_id)] = solution[room_id * 6 + door_id]
    connections = build_connections(door_destinations)
    if connections is None:
        return None
    return Aedificium(rooms=rooms, starting_room=starting_room, connections=connections)


def try_solve():
    """メイン関数"""
    # APIクライアントを作成
    api_base, api_id = "http://localhost:8000", "kawatea_parallel"  # ローカルテスト用
    # api_base, api_id = (
    #     "https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com", 
    #     "amylase.inquiry@gmail.com X6G0RVKUlX20I8XSUsnkIQ"
    # )  # 本番用

    ensure_binary()

    client = api.create_client(api_base=api_base, api_id=api_id)
    
    problem_config = ProblemConfig(
        problem_name="random_room_size_12", 
        num_rooms=12,
    )

    client.select(problem_config.problem_name)
    plan = ''.join(random.choices('012345', k=problem_config.num_rooms * 18))
    explore_response = client.explore([plan])
    result = explore_response["results"][0]
    explore = Explore(plan=plan, result=result)
    
    # 並列実行のパラメータ設定
    num_processes = max(multiprocessing.cpu_count() - 1, 1)  # CPUコア数に基づいて並列度を決定
    
    print(f"並列実行開始: {num_processes}プロセス")
    
    # 各プロセス用の引数を準備
    process_args = []
    for i in range(num_processes):
        args = (
            i,  # process_id
            problem_config,
            explore,
        )
        process_args.append(args)
    
    # 並列実行
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.map(solve, process_args)

    candidates = [candidate for candidate in results if candidate is not None]    
    if not candidates:
        return False

    estimated_aedificium = candidates[0]

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


def main():
    while True:
        if try_solve():
            break
        else:
            print("推測に失敗しました。再度試行します。")
    # try_solve()


if __name__ == "__main__":
    # multiprocessingのためのメイン実行ブロック
    multiprocessing.set_start_method('spawn', force=True)  # macOSでの互換性のため
    main()