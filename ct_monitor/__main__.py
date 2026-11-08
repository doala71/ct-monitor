import json
import os
from pathlib import Path

from ct_monitor.detect import detect
from ct_monitor.fetch import fetch_crtsh
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

    domains: set[str] = set()
    for keyword in keywords:
        domains |= fetch_crtsh(keyword)  # 失敗は例外のままジョブ失敗にする (T6)

    detected = sorted(detect(domains, keywords, allowlist))
    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(detected, ensure_ascii=False, indent=2))
    print(len(detected))


if __name__ == "__main__":
    main()
