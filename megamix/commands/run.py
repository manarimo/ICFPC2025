#!/usr/bin/env python3
"""
Run コマンド - ソルバーを実行する
"""


import json
import os
import random
import sys
from typing import List
import subprocess
from pathlib import Path
import api
from aedificium import Aedificium, build_connections


def run_command(args):
    """
    runコマンドの実装
    
    Args:
        args: argparseで解析された引数
    
    Returns:
        int: 終了コード
    """
    solver = args.solver
    problem_id = args.problem_id
    server = args.server
    seed = args.seed

    return run(solver, problem_id, server, seed)


def run(solver: str, problem_id: str, server: str, seed: int) -> int:
    n_plans = 1
    
    # ソルバーのバイナリが存在するかチェック
    if not os.path.exists(solver):
        print(f"エラー: ソルバーバイナリ '{solver}' が見つかりません", file=sys.stderr)
        return 1
    
    if not os.access(solver, os.X_OK):
        print(f"エラー: ソルバーバイナリ '{solver}' に実行権限がありません", file=sys.stderr)
        return 1
    
    random_state = random.Random(seed)
    api_id = f"megamix_{seed}_{problem_id}"
    client = api.create_client(api_base=server, api_id=api_id)

    client.select(problem_id)
    spoiler = client.spoiler()["map"]
    num_rooms = len(spoiler["rooms"])
    plans = [''.join(random_state.choices('012345', k=num_rooms * 6)) for _ in range(n_plans)]
    results = client.explore(plans)["results"]

    aedificium = solve(solver, plans, results, num_rooms)
    if aedificium is None:
        print(json.dumps({
            "correct": False,
            "reason": "Failed to reconstruct Aedificium"
        }))
        return 0

    judge_result = client.guess(aedificium.to_dict())
    print(json.dumps(judge_result))
    return 0


def solve(solver: str, plans: List[str], results: List[List[int]], num_rooms: int) -> Aedificium | None:
    """
    solve関数の実装
    
    Args:
        solver: ソルバーのバイナリファイルパス
        plans: プラン
        results: 結果
        num_rooms: 部屋数
    """

    solver_input = f"""\
{num_rooms}
{len(plans)}
{'\n'.join(plans)}
{'\n'.join(''.join(map(str, result)) for result in results)}
"""
    # print(solver_input)
    result = subprocess.check_output([str(Path(solver).resolve()), str(num_rooms)], text=True, input=solver_input, stderr=subprocess.DEVNULL)
    output_lines = result.splitlines()
    solution_line = None
    for i, line in enumerate(output_lines):
        if "solved" in line:
            solution_line = output_lines[i - 1]
            break
    if solution_line is None:
        print("ソルバーが解を見つけられませんでした")
        return None
    solution = [int(x) for x in solution_line.split()]

    rooms = [i % 4 for i in range(num_rooms)]
    starting_room = 0
    door_destinations = {}
    for room_id in range(num_rooms):
        for door_id in range(6):
            door_destinations[(room_id, door_id)] = solution[room_id * 6 + door_id]
    connections = build_connections(door_destinations)
    if connections is None:
        return None
    return Aedificium(rooms=rooms, starting_room=starting_room, connections=connections)


def add_run_parser(subparsers):
    """
    runサブコマンドのパーサーを追加
    
    Args:
        subparsers: argparseのサブパーサー
    """
    run_parser = subparsers.add_parser(
        "run",
        help="指定されたソルバーを実行して問題を解く"
    )
    
    run_parser.add_argument(
        "solver",
        help="ソルバーのバイナリファイルパス（例: megamix/simulated_annealing）"
    )
    
    run_parser.add_argument(
        "problem_id",
        help="解く問題のID"
    )
    
    run_parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="使用するリモートサーバーのホスト（デフォルト: http://localhost:8000）"
    )

    run_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="使用するシード（デフォルト: 42）"
    )
    
    run_parser.set_defaults(func=run_command)
