import re

_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_DOMAIN_RE = re.compile(rf"(?:{_LABEL}\.)+{_LABEL}")
_MAX_LENGTH = 253


def normalize_domain(raw: str) -> str | None:
    """ドメイン名を正規形（小文字・先頭 *. と末尾 . なし）にして返す。不正なら None。"""
    if not isinstance(raw, str) or not raw.isascii():
        return None
    name = raw.lower()
    if name.startswith("*."):
        name = name[2:]
    if name.endswith("."):
        name = name[:-1]
    if len(name) > _MAX_LENGTH or not _DOMAIN_RE.fullmatch(name):
        return None
    # 最後のラベルが数字のみなら IP アドレス形式
    if name.rsplit(".", 1)[1].isdigit():
        return None
    return name
