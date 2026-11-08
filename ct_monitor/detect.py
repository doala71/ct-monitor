def detect(
    domains: set[str], keywords: list[str], allowlist: list[str]
) -> set[str]:
    """キーワードを含み、許可リスト（とそのサブドメイン）に属さないドメインを返す。"""
    kws = [k.lower() for k in keywords if k]
    allowed = [a.lower() for a in allowlist if a]
    return {
        d
        for d in domains
        if any(k in d for k in kws)
        and not any(d == a or d.endswith("." + a) for a in allowed)
    }
