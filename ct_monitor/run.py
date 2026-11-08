import json
from pathlib import Path

from ct_monitor.detect import detect
from ct_monitor.state import load_state, save_state


def run(
    fetched: dict[str, dict[str, int]],
    allowlist: list[str],
    state_path: Path,
    out_path: Path,
) -> list[str] | None:
    """キーワードごとの取得結果 {キーワード: {ドメイン名: id}} から、新規分だけを検知する。

    保存済みの id より大きいものだけを、キーワードごとに対象にする。状態に記録のない
    キーワードは初回扱いで、検知せず最大 id（取得結果が空なら 0）を保存する。全キーワードが初回なら None を返す。
    検知結果と状態は、ここまでの取得・検知が成功した後にだけ書く。
    """
    saved = load_state(state_path)  # 壊れていれば例外 (T5)
    updated = dict(saved)
    detected: set[str] = set()
    any_known = False
    for keyword, domains in fetched.items():
        newest = max(domains.values(), default=0)  # 空なら 0。以後に現れたものはすべて新規になる
        last = saved.get(keyword)
        if last is None:
            updated[keyword] = newest
            continue
        any_known = True
        new = {d for d, i in domains.items() if i > last}
        detected |= detect(new, [keyword], allowlist)
        if newest > last:
            updated[keyword] = newest
    if not any_known:
        if updated != saved:
            save_state(updated, state_path)
        return None
    result = sorted(detected)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    if updated != saved:
        save_state(updated, state_path)
    return result
