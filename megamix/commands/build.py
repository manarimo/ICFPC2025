import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def build_command(args) -> int:
    """
    buildサブコマンドの実装
    
    eval_funcファイルをsolver/score.cppとしてコピーし、
    一時ディレクトリでmakeを実行してsimulated_annealingバイナリを生成し、
    現在のワーキングディレクトリにコピーする
    """
    eval_func_path = Path(args.eval_func)
    return _build(eval_func_path)


def _build(eval_func_path: Path) -> int:
    # eval_funcファイルの存在確認
    if not eval_func_path.exists():
        print(f"エラー: 評価関数ファイル '{eval_func_path}' が見つかりません", file=sys.stderr)
        return 1
    
    # 現在のスクリプトのディレクトリを取得
    script_dir = Path(__file__).parent.parent.absolute()
    solver_dir = script_dir / "solver"
    
    # solverディレクトリの存在確認
    if not solver_dir.exists():
        print(f"エラー: solverディレクトリ '{solver_dir}' が見つかりません", file=sys.stderr)
        return 1
    
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        temp_solver_dir = temp_path / "solver"
        
        print(f"一時ディレクトリでビルドを実行中: {temp_dir}")
        
        try:
            # solverディレクトリ全体を一時ディレクトリにコピー
            shutil.copytree(solver_dir, temp_solver_dir)
            
            # eval_funcファイルをscore.cppとしてコピー
            score_cpp_path = temp_solver_dir / "score.cpp"
            shutil.copy2(eval_func_path, score_cpp_path)
            print(f"評価関数をコピー: {eval_func_path} -> {score_cpp_path}")
            
            # makeを実行
            print("makeを実行中...")
            result = subprocess.run(
                ["make"],
                cwd=temp_solver_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("エラー: makeの実行に失敗しました", file=sys.stderr)
                print("stdout:", result.stdout, file=sys.stderr)
                print("stderr:", result.stderr, file=sys.stderr)
                return 1
            
            # 生成されたバイナリを現在のワーキングディレクトリにコピー
            binary_path = temp_solver_dir / "simulated_annealing"
            if not binary_path.exists():
                print("エラー: simulated_annealingバイナリが生成されませんでした", file=sys.stderr)
                return 1
            
            current_dir = Path.cwd()
            target_binary = current_dir / "simulated_annealing"
            shutil.rmtree(target_binary, ignore_errors=True)
            shutil.copy2(binary_path, target_binary)
            
            # 実行権限を付与
            target_binary.chmod(0o755)
            
            print(f"ビルド完了: {target_binary}")
            return 0
            
        except Exception as e:
            print(f"エラー: ビルド中に例外が発生しました: {e}", file=sys.stderr)
            return 1


def add_build_parser(subparsers):
    """
    buildサブコマンドのパーサーを追加
    
    Args:
        subparsers: argparseのサブパーサー
    """
    build_parser = subparsers.add_parser(
        "build",
        help="評価関数をビルドしてsimulated_annealingバイナリを生成"
    )
    
    build_parser.add_argument(
        "eval_func",
        help="評価関数のファイルパス（例: eval_functions/original.cpp）"
    )
    
    build_parser.set_defaults(func=build_command)
