#!/usr/bin/env python3
"""
ICFP 2025 Contest CLI Tool
Ædificium探索のためのコマンドラインインターフェース
"""

import argparse
import json
import os
import sys
from api import APIClient, create_client


def cmd_register(args):
    """チーム登録コマンド"""
    try:
        client = create_client(api_base=args.api_base)
        response = client.register(args.name, args.pl, args.email)
        print(f"登録成功: {json.dumps(response, indent=2)}")
        
        with open("id.json", "w") as f:
            json.dump({"id": response["id"]}, f)
        print("IDをid.jsonに保存しました")
        
    except Exception as e:
        print(f"登録エラー: {e}")
        sys.exit(1)


def cmd_select(args):
    """問題選択コマンド"""
    try:
        client = create_client(api_base=args.api_base)
        response = client.select(args.problem_name)
        print(f"{json.dumps(response, indent=2)}")
    except Exception as e:
        print(f"問題選択エラー: {e}")
        sys.exit(1)


def cmd_explore(args):
    """探索コマンド"""
    try:
        client = create_client(api_base=args.api_base)
        plans = args.plans if isinstance(args.plans, list) else [args.plans]
        response = client.explore(plans)
        print(f"{json.dumps(response, indent=2)}")
    except Exception as e:
        print(f"探索エラー: {e}")
        sys.exit(1)


def cmd_guess(args):
    """推測提出コマンド"""
    try:
        client = create_client(api_base=args.api_base)
        # JSONファイルからマップデータを読み取る
        with open(args.map_file, "r") as f:
            map_data = json.load(f)
        
        response = client.guess(map_data)
        print(f"{json.dumps(response, indent=2)}")
    except Exception as e:
        print(f"推測提出エラー: {e}")
        sys.exit(1)


def cmd_spoiler(args):
    """正解を取得する"""
    try:
        client = create_client(api_base=args.api_base)
        response = client.spoiler()
        print(f"{json.dumps(response, indent=2)}")
    except Exception as e:
        print(f"正解取得エラー: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="ICFP 2025 Contest CLI Tool")
    
    # グローバルオプション
    parser.add_argument(
        "--api-base", 
        help="API ベース URL（環境変数API_BASEも使用可能、デフォルト: https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com）",
        default=None
    )
    
    subparsers = parser.add_subparsers(dest="command", help="利用可能なコマンド")
    
    # register コマンド
    register_parser = subparsers.add_parser("register", help="チームを登録する")
    register_parser.add_argument("name", help="チーム名")
    register_parser.add_argument("pl", help="プログラミング言語")
    register_parser.add_argument("email", help="メールアドレス")
    register_parser.set_defaults(func=cmd_register)
    
    # select コマンド
    select_parser = subparsers.add_parser("select", help="問題を選択する")
    select_parser.add_argument("problem_name", help="問題名（例: probatio）")
    select_parser.set_defaults(func=cmd_select)
    
    # explore コマンド
    explore_parser = subparsers.add_parser("explore", help="Ædificiumを探索する")
    explore_parser.add_argument("plans", nargs="+", help="ルートプラン（例: 012 345）")
    explore_parser.set_defaults(func=cmd_explore)
    
    # guess コマンド
    guess_parser = subparsers.add_parser("guess", help="マップを推測して提出する")
    guess_parser.add_argument("map_file", help="マップデータのJSONファイル")
    guess_parser.set_defaults(func=cmd_guess)

    # spoiler コマンド
    spoiler_parser = subparsers.add_parser("spoiler", help="正解を取得する")
    spoiler_parser.set_defaults(func=cmd_spoiler)
    
    args = parser.parse_args()
    
    # --api-baseが指定されていない場合、環境変数API_BASEを使用
    if args.api_base is None:
        args.api_base = os.environ.get('API_BASE')
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
