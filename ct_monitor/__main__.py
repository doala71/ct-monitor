import os
from pathlib import Path

from ct_monitor.fetch import fetch_crtsh
from ct_monitor.run import run
from ct_monitor.state import STATE_PATH
from ct_monitor.validate import normalize_domain

OUT_PATH = Path("out/detected.json")


def _split(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def main() -> None:
    keywords = [k.lower() for k in _split(os.environ.get("CT_KEYWORDS", ""))]
    if not keywords:
        raise SystemExit("CT_KEYWORDS is not set")
    allowlist = [
        n for n in map(normalize_domain, _split(os.environ.get("CT_ALLOWLIST", ""))) if n
    ]

    fetched: dict[str, dict[str, int]] = {}
    rows = retries = 0
    max_id: int | None = None
    for keyword in keywords:
        # 失敗は例外のままジョブ失敗にする (T6)
        result = fetch_crtsh(keyword)
        fetched[keyword] = result.domains
        rows += result.rows
        retries += result.retries
        if result.max_id is not None:
            max_id = result.max_id if max_id is None else max(max_id, result.max_id)

    detected = run(fetched, allowlist, STATE_PATH, OUT_PATH)
    # ドメイン名は出さない (T1)
    print(f"detected: {len(detected) if detected is not None else 'first run'}")
    print(f"response rows: {rows}")
    print(f"response max id: {max_id if max_id is not None else 'none'}")
    print(f"retries: {retries}")


if __name__ == "__main__":
    main()
