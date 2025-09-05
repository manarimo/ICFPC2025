import json
import urllib.request
import urllib.parse
from urllib.error import HTTPError, URLError

API_BASE = "https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com"


with open("id.json", "r") as f:
    data = json.load(f)
    API_ID = data["id"]


def make_json_post_request(path, data_dict, headers=None):
    url = f"{API_BASE}{path}"
    json_data = json.dumps(data_dict).encode('utf-8')
    
    default_headers = {
        'Content-Type': 'application/json',
        'Content-Length': str(len(json_data))
    }
    
    if headers:
        default_headers.update(headers)
    
    request = urllib.request.Request(
        url=url,
        data=json_data,
        headers=default_headers,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(request) as response:
            response_data = response.read().decode('utf-8')
            return json.loads(response_data)
            
    except HTTPError as e:
        print(f"HTTPエラーが発生しました: {e.code} - {e.reason}")
        error_response = e.read().decode('utf-8')
        print(f"エラーレスポンス: {error_response}")
        raise
    except URLError as e:
        print(f"URLエラーが発生しました: {e.reason}")
        raise
    except json.JSONDecodeError as e:
        print(f"JSONデコードエラーが発生しました: {e}")
        raise


def register(name: str, pl: str, email: str):
    """
    新しいチームを登録する
    
    Args:
        name: チーム名
        pl: プログラミング言語
        email: メールアドレス
        
    Returns:
        dict: {"id": string} レスポンス
    """
    request_data = {
        "name": name,
        "pl": pl,
        "email": email,
    }
    return make_json_post_request("/register", request_data)


def select(problem_name: str):
    """
    問題を選択する
    
    Args:
        problem_name: 選択する問題名
        
    Returns:
        dict: {"problemName": string} レスポンス
    """
    request_data = {
        "id": API_ID,
        "problemName": problem_name,
    }
    return make_json_post_request("/select", request_data)


def explore(plans: list):
    """
    Ædificiumを探索する
    
    Args:
        plans: ルートプランのリスト（各プランは"0"～"5"の数字の文字列）
        
    Returns:
        dict: {"results": [[int]], "queryCount": int} レスポンス
    """
    request_data = {
        "id": API_ID,
        "plans": plans,
    }
    return make_json_post_request("/explore", request_data)


def guess(map_data: dict):
    """
    候補となるマップを提出する
    
    Args:
        map_data: マップの説明を含む辞書
                 {
                   "rooms": [int],
                   "startingRoom": int,
                   "connections": [
                     {
                       "from": {"room": int, "door": int},
                       "to": {"room": int, "door": int}
                     }
                   ]
                 }
                 
    Returns:
        dict: {"correct": boolean} レスポンス
    """
    request_data = {
        "id": API_ID,
        "map": map_data,
    }
    return make_json_post_request("/guess", request_data)


