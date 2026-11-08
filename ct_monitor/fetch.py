import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, NamedTuple

from ct_monitor.validate import normalize_domain

_URL = "https://crt.sh/?q=%25{keyword}%25&output=json"
_TIMEOUT = 60
_RETRY_STATUS = (502, 503, 504)
_BACKOFF = (15, 30, 60)  # 再試行前の待ち秒数。長さが最大再試行回数


def parse_crtsh(text: str) -> dict[str, int]:
    """crt.sh の JSON 文字列から {ドメイン名: 最大の id} を作る。

    id が整数でない行は捨てる。JSON でない・リストでない場合は例外。
    """
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("crt.sh response is not a list")
    domains: dict[str, int] = {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        cert_id = entry.get("id")
        if not isinstance(cert_id, int) or isinstance(cert_id, bool):
            continue
        value = entry.get("name_value")
        if not isinstance(value, str):
            continue
        for raw in value.split("\n"):
            name = normalize_domain(raw.strip())
            if name is not None:
                domains[name] = max(cert_id, domains.get(name, cert_id))
    return domains


def summarize_crtsh(text: str) -> tuple[int, int | None]:
    """crt.sh の JSON 文字列から (応答の行数, 応答の最大 id) を返す。id が取れなければ最大 id は None。"""
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("crt.sh response is not a list")
    ids = [
        e["id"]
        for e in data
        if isinstance(e, dict) and isinstance(e.get("id"), int) and not isinstance(e["id"], bool)
    ]
    return len(data), max(ids, default=None)


class Fetched(NamedTuple):
    domains: dict[str, int]
    rows: int
    max_id: int | None
    retries: int


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in _RETRY_STATUS
    if isinstance(exc, urllib.error.URLError):
        return isinstance(exc.reason, (TimeoutError, socket.timeout))
    return isinstance(exc, (TimeoutError, socket.timeout))


def fetch_crtsh(
    keyword: str,
    timeout: float = _TIMEOUT,
    sleep: Callable[[float], None] = time.sleep,
) -> Fetched:
    """crt.sh からキーワードに一致する証明書を取得する。失敗は例外 (T6)。

    HTTP 502・503・504 とタイムアウトだけを、待ち時間を伸ばしながら再試行する。
    それ以外のエラーは再試行しない。再試行をすべて失敗したら最後の例外を送出する。
    """
    url = _URL.format(keyword=urllib.parse.quote(keyword, safe=""))
    retries = 0
    while True:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                text = resp.read().decode("utf-8")
            break
        except Exception as exc:
            if not _is_retryable(exc) or retries >= len(_BACKOFF):
                raise
            sleep(_BACKOFF[retries])
            retries += 1
    rows, max_id = summarize_crtsh(text)
    return Fetched(parse_crtsh(text), rows, max_id, retries)
