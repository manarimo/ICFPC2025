import random
import multiprocessing
import os
import re
import argparse
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


public_names = {
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

def ensure_binary(mode: str | None = None):
    target = ["make", "solve.exe"]
    subprocess.run(target, check=True, cwd=Path(__file__).parent)


def solve(args) -> Aedificium | None:
    """
    並列実行用のsolve関数ラッパー
    各プロセスで異なる乱数状態を初期化する
    
    Args:
        args: (process_id, problem_config, explore, binary_name)
        
    Returns:
        Tuple[List[int], int]: (推定された部屋IDの履歴, 適合度)
    """
    process_id, problem_config, explore, binary_name = args
    
    print(f"プロセス {process_id} (PID: {os.getpid()}): 問題 = {problem_config}")
    
    # call c++ binary
    binary_path = Path(__file__).parent / binary_name
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


def _infer_mode(problem_name: str) -> str:
    name = problem_name.lower()
    single = {"probatio", "primus", "secundus", "tertius", "quartus", "quintus"}
    double = {"aleph", "beth", "gimel", "daleth", "he"}
    triple = {"vau", "zain", "hhet", "teth", "iod"}
    if name in single:
        return "SINGLE"
    if name in double:
        return "DOUBLE"
    if name in triple:
        return "TRIPLE"
    m = re.match(r"random_full_(\d+)_(\d+)", name)
    if m:
        dup = int(m.group(2))
        return {1: "SINGLE", 2: "DOUBLE", 3: "TRIPLE"}.get(dup, "DOUBLE")
    return "DOUBLE"


def _duplication_factor(mode: str) -> int:
    return {"SINGLE": 1, "DOUBLE": 2, "TRIPLE": 3}.get(mode, 2)


def _create_client_for_target(target_server: str):
    if target_server == "local":
        return api.create_client(api_base="http://localhost:8000", api_id="kawatea_parallel_local")
    if target_server == "mock":
        return api.create_client(api_base="https://lord-crossight-553250624194.asia-northeast1.run.app", api_id="kawatea_parallel_mock")
    # contest (本番用)
    return api.create_client(
        api_base="https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com",
        api_id="amylase.inquiry@gmail.com X6G0RVKUlX20I8XSUsnkIQ",
    )


def try_solve(args):
    """メイン関数"""
    client = _create_client_for_target(args.target_server)

    # 2倍問題・3倍問題の場合はnum_roomsを縮小マップのサイズで指定する
    num_rooms = public_names[args.problem_name][0]
    if args.num_rooms:
        num_rooms = args.num_rooms
    problem_config = ProblemConfig(
        problem_name=args.problem_name,
        num_rooms=num_rooms,
    )

    mode = args.mode or _infer_mode(problem_config.problem_name)
    factor = _duplication_factor(mode)

    # Build appropriate solver after we know mode
    ensure_binary(mode)
    binary_name = "solve.exe"

    client.select(problem_config.problem_name)
    plan = ''.join(random.choices('012345', k=problem_config.num_rooms * factor * 6))
    explore_response = client.explore([plan])
    result = explore_response["results"][0]
    explore = Explore(plan=plan, result=result)
    
    # 並列実行のパラメータ設定
    if getattr(args, "parallelism", None) is not None:
        num_processes = max(int(args.parallelism), 1)
    else:
        num_processes = max(multiprocessing.cpu_count() - 1, 1)  # CPUコア数に基づいて並列度を決定
    #num_processes = 1  # CPUコア数に基づいて並列度を決定
    
    print(f"並列実行開始: {num_processes}プロセス")
    
    # 各プロセス用の引数を準備
    process_args = []
    for i in range(num_processes):
        proc_arg = (
            i,  # process_id
            problem_config,
            explore,
            binary_name,
        )
        process_args.append(proc_arg)
    
    # 並列実行: 最初に成功した結果を採用して即時継続
    estimated_aedificium = None
    with multiprocessing.Pool(processes=num_processes) as pool:
        for res in pool.imap_unordered(solve, process_args):
            if res is not None:
                estimated_aedificium = res
                # 他のワーカーを停止して先に進む
                pool.terminate()
                break
    if estimated_aedificium is None:
        return False
    print('est', estimated_aedificium.to_json())
    if False:
        spoiler = client.spoiler()
        spoiler_aedificium = Aedificium.from_dict(spoiler['map'])
        print('spoiler', spoiler_aedificium.to_json())
        conns = []
        seen = set()
        for conn in spoiler_aedificium.connections:
            fr = conn['from']
            fr['room'] %= 6
            to = conn['to']
            to['room'] %= 6
            tag = (fr['room'], fr['door'])
            if tag not in seen:
                conns.append({'from': fr, 'to': to})
                seen.add(tag)

    #estimated_aedificium = Aedificium(spoiler_aedificium.rooms[0:6], spoiler_aedificium.starting_room, conns)

    # Number of random-walk augmentations to gather extra information
    random_walk_stalks = getattr(args, "deep_expeditions", 10)
    if mode == 'DOUBLE':
        # ランダムウォークして情報をあつめる
        covering_path = estimated_aedificium.build_covering_path()
        print('cover', covering_path)
        max_len = problem_config.num_rooms * 2 * 6
        plans = []
        for i in range(random_walk_stalks):
            raw_plan = ''.join(random.choices('012345', k=max_len - len(covering_path)))
            enhanced_plan = estimated_aedificium.inject_charcoal_to_walk(covering_path + raw_plan)
            plans.append(enhanced_plan)
        res = client.explore(plans)
        dests_list = []
        for (plan, results) in zip(plans, res['results']):
            dests = estimated_aedificium.build_dest_maps_double(plan, results)
            if dests is not None:
                dests_list.append(dests)
        final_dests = {}
        for dests in dests_list:
            for (key, val) in dests.items():
                if key in final_dests and final_dests[key] != val:
                    print(f"Error: conflicting dests: door={key}, dest1={final_dests[key]}, dest2={val}")
                    return
                final_dests[key] = val
        try:
            connections = build_connections(final_dests, problem_config.num_rooms * factor)
            estimated_aedificium = Aedificium(estimated_aedificium.rooms * 2, estimated_aedificium.starting_room, connections)
        except:
            print("ERROR: failed to build connections")
            return
        print("guess", estimated_aedificium.to_json())

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
    parser = argparse.ArgumentParser(description="Parallel solver runner")
    parser.add_argument("--problem-name", default=None, help="Set problem_config.problem_name (e.g., beth, secundus)")
    parser.add_argument("--num-rooms", type=int, default=None, help="Set problem_config.num_rooms (single map size)")
    parser.add_argument(
        "--mode",
        choices=["single", "double", "triple"],
        default=None,
        help="Override mode (normally inferred from problem name)",
    )
    parser.add_argument(
        "--target-server",
        choices=["local", "mock", "contest"],
        default="local",
        help="Select API server: local|mock|contest",
    )
    parser.add_argument(
        "--parallelism", "-j", type=int, default=None,
        help="Number of worker processes (default: cpu_count-1)",
    )
    parser.add_argument(
        "--deep-expeditions", type=int, default=10,
        help="Number of deep expeditions (random-walk stalks) used when refining DOUBLE mode",
    )
    args = parser.parse_args()
    # normalize mode to uppercase if provided
    if args.mode:
        args.mode = args.mode.upper()

    while True:
        if try_solve(args):
            break
        else:
            print("推測に失敗しました。再度試行します。")
    # try_solve()


if __name__ == "__main__":
    # multiprocessingのためのメイン実行ブロック
    multiprocessing.set_start_method('spawn', force=True)  # macOSでの互換性のため
    main()
