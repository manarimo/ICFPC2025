#!/usr/bin/env python3
"""
Arena - ICFPC2025 Megamix コマンドラインツール

複数のサブコマンドをサポートするコマンドラインツール
"""

import argparse
import sys
from commands.build import add_build_parser
from commands.run import add_run_parser
from commands.eval import add_eval_parser


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="Arena - ICFPC2025 Megamix コマンドラインツール",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(
        dest="command",
        help="使用可能なサブコマンド",
        metavar="COMMAND"
    )
    
    # buildサブコマンド
    add_build_parser(subparsers)
    
    # runサブコマンド
    add_run_parser(subparsers)
    
    # evalサブコマンド
    add_eval_parser(subparsers)
    
    # 引数をパース
    args = parser.parse_args()
    
    # サブコマンドが指定されていない場合はヘルプを表示
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1

    # 対応する関数を実行
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
