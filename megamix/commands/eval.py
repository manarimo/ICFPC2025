#!/usr/bin/env python3
"""
Eval コマンド - 複数のシードでソルバーを並列実行し、正解率を評価する
"""

import json
import sys
import io
import contextlib
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, Any
from commands.run import run


def run_single_seed_worker(args_tuple):
    """
    プロセスプールで実行される単一のシードでのワーカー関数
    
    Args:
        args_tuple: (solver, problem_id, server, seed) のタプル
        
    Returns:
        dict: 実行結果
    """
    solver, problem_id, server, seed = args_tuple
    
    try:
        # runの出力をキャプチャするため、標準出力をリダイレクト
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            exit_code = run(solver, problem_id, server, seed)
        
        output = captured_output.getvalue().strip()
        
        # JSONとして解析を試行
        try:
            result = json.loads(output)
            return {
                'seed': seed,
                'exit_code': exit_code,
                'result': result,
                'success': True
            }
        except json.JSONDecodeError:
            return {
                'seed': seed,
                'exit_code': exit_code,
                'result': None,
                'success': False,
                'error': f"JSON解析エラー: {output}"
            }
    except Exception as e:
        return {
            'seed': seed,
            'exit_code': 1,
            'result': None,
            'success': False,
            'error': str(e)
        }


def eval_command(args):
    """
    evalコマンドの実装
    
    Args:
        args: argparseで解析された引数
    
    Returns:
        int: 終了コード
    """
    solver = args.solver
    problem_id = args.problem_id
    server = args.server
    num_seeds = args.num_seeds
    max_workers = args.max_workers

    # シード数からシードリストを生成
    seeds = list(range(num_seeds))
    
    return evaluate(solver, problem_id, server, seeds, max_workers)


def evaluate(solver: str, problem_id: str, server: str, seeds: list, max_workers: int) -> int:
    """
    複数のシードでソルバーを並列実行し、正解率を計算する
    
    Args:
        solver: ソルバーのバイナリファイルパス
        problem_id: 問題ID
        server: サーバーURL
        seeds: 使用するシードのリスト
        max_workers: 並列実行の最大ワーカー数
    
    Returns:
        int: 終了コード
    """
    print(f"ソルバー: {solver}", file=sys.stderr)
    print(f"問題ID: {problem_id}", file=sys.stderr)
    print(f"サーバー: {server}", file=sys.stderr)
    print(f"シード数: {len(seeds)}", file=sys.stderr)
    print(f"最大並列数: {max_workers}", file=sys.stderr)
    
    results = []
    
    # 並列実行用の引数リストを準備
    worker_args = [(solver, problem_id, server, seed) for seed in seeds]
    
    # 並列実行
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 全てのタスクを投入
        future_to_seed = {executor.submit(run_single_seed_worker, args): args[3] for args in worker_args}
        
        # 結果を収集
        for future in as_completed(future_to_seed):
            seed = future_to_seed[future]
            try:
                result = future.result()
                results.append(result)

            except Exception as e:
                print(f"シード {seed}: 例外 - {str(e)}", file=sys.stderr)
                results.append({
                    'seed': seed,
                    'exit_code': 1,
                    'result': None,
                    'success': False,
                    'error': str(e)
                })
    
    # 結果を集計
    total_runs = len(results)
    successful_runs = sum(1 for r in results if r['success'] and r['result'])
    correct_runs = sum(1 for r in results if r['success'] and r['result'] and r['result'].get('correct', False))
    
    correct_ratio = correct_runs / total_runs
    
    # 結果を出力
    evaluation_result = {
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "correct_runs": correct_runs,
        "correct_ratio": correct_ratio,
        "failed_runs": total_runs - successful_runs,
        "seeds": seeds,
        "details": results
    }
    
    print(json.dumps(evaluation_result, ensure_ascii=False))
    
    # サマリーをstderrに出力
    print(f"\n=== 評価結果サマリー ===", file=sys.stderr)
    print(f"総実行数: {total_runs}", file=sys.stderr)
    print(f"成功実行数: {successful_runs}", file=sys.stderr)
    print(f"正解数: {correct_runs}", file=sys.stderr)
    print(f"正解率: {correct_ratio:.2%}", file=sys.stderr)
    print(f"失敗数: {total_runs - successful_runs}", file=sys.stderr)
    
    return 0


def add_eval_parser(subparsers):
    """
    evalサブコマンドのパーサーを追加
    
    Args:
        subparsers: argparseのサブパーサー
    """
    eval_parser = subparsers.add_parser(
        "eval",
        help="複数のシードでソルバーを並列実行し、正解率を評価する"
    )
    
    eval_parser.add_argument(
        "solver",
        help="ソルバーのバイナリファイルパス（例: megamix/simulated_annealing）"
    )
    
    eval_parser.add_argument(
        "problem_id",
        help="解く問題のID"
    )
    
    eval_parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="使用するリモートサーバーのホスト（デフォルト: http://localhost:8000）"
    )
    
    eval_parser.add_argument(
        "--num-seeds",
        type=int,
        default=10,
        help="使用するシード数（デフォルト: 10、シードは0からnum_seeds-1まで）"
    )
    
    eval_parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="並列実行の最大ワーカー数（デフォルト: 1）"
    )
    
    eval_parser.set_defaults(func=eval_command)
