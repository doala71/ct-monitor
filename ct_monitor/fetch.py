import json
import urllib.parse
import urllib.request

from ct_monitor.validate import normalize_domain

_URL = "https://crt.sh/?q=%25{keyword}%25&output=json"
_TIMEOUT = 60


def parse_crtsh(text: str) -> set[str]:
    """crt.sh の JSON 文字列からドメイン名の集合を作る。JSON でない・リストでない場合は例外。"""
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("crt.sh response is not a list")
    domains: set[str] = set()
    for entry in data:
        if not isinstance(entry, dict):
            continue
        value = entry.get("name_value")
        if not isinstance(value, str):
            continue
        for raw in value.split("\n"):
            name = normalize_domain(raw.strip())
            if name is not None:
                domains.add(name)
    return domains


def fetch_crtsh(keyword: str, timeout: float = _TIMEOUT) -> set[str]:
    """crt.sh からキーワードに一致する証明書のドメイン名を取得する。失敗は例外。"""
    url = _URL.format(keyword=urllib.parse.quote(keyword, safe=""))
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # HTTP エラーは HTTPError
        text = resp.read().decode("utf-8")
    return parse_crtsh(text)
