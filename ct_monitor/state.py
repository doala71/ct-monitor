import json
import os
from pathlib import Path

STATE_PATH = Path("out/state.json")


def _is_id(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def load_state(path: Path = STATE_PATH) -> dict[str, int]:
    """キーワードごとの保存済み最大 id を返す。ファイルがなければ空（全キーワードが初回）。壊れていれば例外 (T5)。"""
    try:
        text = path.read_text()
    except FileNotFoundError:
        return {}
    data = json.loads(text)
    ids = data.get("max_ids") if isinstance(data, dict) else None
    if not isinstance(ids, dict) or not all(isinstance(k, str) and _is_id(v) for k, v in ids.items()):
        raise ValueError("state file is corrupted")
    return dict(ids)


def save_state(max_ids: dict[str, int], path: Path = STATE_PATH) -> None:
    """キーワードごとの最大 id を保存する。途中で止まっても半端なファイルを残さないよう置き換えで書く。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({"max_ids": max_ids}, sort_keys=True))
    os.replace(tmp, path)
