import json

def json_response(data, headers=None):
    return (200, [('Content-Type', 'application/json; charset=utf-8')] + (headers or []), json.dumps(data, ensure_ascii=False).encode())
