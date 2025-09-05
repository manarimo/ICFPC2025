import json
import urllib.request
import urllib.parse
from urllib.error import HTTPError, URLError

API_BASE = "https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com"


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
    request_data = {
        "name": name,
        "pl": pl,
        "email": email,
    }
    return make_json_post_request("/register", request_data)
