#!/usr/bin/env python3
"""
ICFP 2025 Contest CLI Tool
Ædificium探索のためのコマンドラインインターフェース
"""

import argparse
import json
import sys
from api import register, select, explore, guess


def cmd_register(args):
    """チーム登録コマンド"""
    try:
        response = register(args.name, args.pl, args.email)
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
        response = select(args.problem_name)
        print(f"問題選択成功: {json.dumps(response, indent=2)}")
    except Exception as e:
        print(f"問題選択エラー: {e}")
        sys.exit(1)


def cmd_explore(args):
    """探索コマンド"""
    try:
        plans = args.plans if isinstance(args.plans, list) else [args.plans]
        response = explore(plans)
        print(f"探索結果: {json.dumps(response, indent=2)}")
    except Exception as e:
        print(f"探索エラー: {e}")
        sys.exit(1)


def cmd_guess(args):
    """推測提出コマンド"""
    try:
        # JSONファイルからマップデータを読み取る
        with open(args.map_file, "r") as f:
            map_data = json.load(f)
        
        response = guess(map_data)
        print(f"推測結果: {json.dumps(response, indent=2)}")
        
        if response.get("correct"):
            print("🎉 正解です！")
        else:
            print("❌ 不正解です。再度お試しください。")
            
    except Exception as e:
        print(f"推測提出エラー: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="ICFP 2025 Contest CLI Tool")
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
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
