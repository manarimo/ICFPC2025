import json
import urllib.request
import urllib.parse
from urllib.error import HTTPError, URLError
from typing import Optional, Dict, List, Any


class APIClient:
    """ICFPC2025 API クライアント"""
    
    def __init__(self, api_base: Optional[str] = None, api_id: Optional[str] = None, id_json_path: str = "id.json"):
        """
        APIクライアントを初期化する
        
        Args:
            api_base: API ベース URL（Noneの場合はデフォルト値を使用）
            api_id: API ID（Noneの場合はid.jsonから読み込み）
            id_json_path: id.jsonファイルのパス
        """
        self.api_base = api_base or "https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com"
        
        if api_id:
            self.api_id = api_id
        else:
            try:
                with open(id_json_path, "r") as f:
                    data = json.load(f)
                    self.api_id = data["id"]
            except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
                raise ValueError(f"API IDの読み込みに失敗しました: {e}")
    
    def _make_json_post_request(self, path: str, data_dict: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        JSON POSTリクエストを送信する
        
        Args:
            path: APIパス
            data_dict: 送信するデータ
            headers: 追加のヘッダー
            
        Returns:
            dict: APIレスポンス
        """
        url = f"{self.api_base}{path}"
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
    
    def register(self, name: str, pl: str, email: str) -> Dict[str, Any]:
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
        return self._make_json_post_request("/register", request_data)
    
    def select(self, problem_name: str) -> Dict[str, Any]:
        """
        問題を選択する
        
        Args:
            problem_name: 選択する問題名
            
        Returns:
            dict: {"problemName": string} レスポンス
        """
        request_data = {
            "id": self.api_id,
            "problemName": problem_name,
        }
        return self._make_json_post_request("/select", request_data)
    
    def explore(self, plans: List[str]) -> Dict[str, Any]:
        """
        Ædificiumを探索する
        
        Args:
            plans: ルートプランのリスト（各プランは"0"～"5"の数字の文字列）
            
        Returns:
            dict: {"results": [[int]], "queryCount": int} レスポンス
        """
        request_data = {
            "id": self.api_id,
            "plans": plans,
        }
        return self._make_json_post_request("/explore", request_data)
    
    def guess(self, map_data: Dict[str, Any]) -> Dict[str, Any]:
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
            "id": self.api_id,
            "map": map_data,
        }
        return self._make_json_post_request("/guess", request_data)
    
    def spoiler(self) -> Dict[str, Any]:
        """
        正解を取得する
        """
        request_data = {
            "id": self.api_id,
        }
        return self._make_json_post_request("/spoiler", request_data)


# 後方互換性のためのデフォルトクライアントインスタンス
_default_client = None

def _get_default_client() -> APIClient:
    """デフォルトクライアントを取得する（遅延初期化）"""
    global _default_client
    if _default_client is None:
        _default_client = APIClient()
    return _default_client


# 後方互換性のための関数インターフェース
def register(name: str, pl: str, email: str) -> Dict[str, Any]:
    """
    新しいチームを登録する（後方互換性のための関数）
    
    Args:
        name: チーム名
        pl: プログラミング言語
        email: メールアドレス
        
    Returns:
        dict: {"id": string} レスポンス
    """
    return _get_default_client().register(name, pl, email)


def select(problem_name: str) -> Dict[str, Any]:
    """
    問題を選択する（後方互換性のための関数）
    
    Args:
        problem_name: 選択する問題名
        
    Returns:
        dict: {"problemName": string} レスポンス
    """
    return _get_default_client().select(problem_name)


def explore(plans: List[str]) -> Dict[str, Any]:
    """
    Ædificiumを探索する（後方互換性のための関数）
    
    Args:
        plans: ルートプランのリスト（各プランは"0"～"5"の数字の文字列）
        
    Returns:
        dict: {"results": [[int]], "queryCount": int} レスポンス
    """
    return _get_default_client().explore(plans)


def guess(map_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    候補となるマップを提出する（後方互換性のための関数）
    
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
    return _get_default_client().guess(map_data)


# 便利な関数
def create_client(api_base: Optional[str] = None, api_id: Optional[str] = None, id_json_path: str = "id.json") -> APIClient:
    """
    新しいAPIクライアントインスタンスを作成する
    
    Args:
        api_base: API ベース URL（Noneの場合はデフォルト値を使用）
        api_id: API ID（Noneの場合はid.jsonから読み込み）
        id_json_path: id.jsonファイルのパス
        
    Returns:
        APIClient: 新しいクライアントインスタンス
    """
    return APIClient(api_base=api_base, api_id=api_id, id_json_path=id_json_path)


