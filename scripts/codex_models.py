#!/usr/bin/env python3
"""从 Codex proxy 的 /v1/models 列表里挑某个系列的最新模型（fork 专用，只依赖标准库）。

例如系列 sol：gpt-6.1-sol > gpt-6-sol > gpt-5.6-sol。只认 `gpt-<版本号>-<系列>` 这种完整名字，
带其它后缀的（如 gpt-6-sol-mini）不算。列表里没有该系列时输出 fallback。

    curl .../v1/models | python3 codex_models.py pick --family sol --fallback gpt-6-sol
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Iterable


def version_of(model_id: str, family: str) -> tuple[int, ...] | None:
    m = re.fullmatch(rf"gpt-(\d+(?:\.\d+)*)-{re.escape(family)}", str(model_id or "").strip())
    if not m:
        return None
    return tuple(int(part) for part in m.group(1).split("."))


def pick_latest(model_ids: Iterable[str], family: str, fallback: str) -> str:
    best, best_version = fallback, None
    for model_id in model_ids:
        version = version_of(model_id, family)
        if version is not None and (best_version is None or version > best_version):
            best, best_version = str(model_id).strip(), version
    return best


def model_ids_from_response(text: str) -> list[str]:
    try:
        data = json.loads(text or "{}")
    except json.JSONDecodeError:
        return []
    items = data.get("data") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    return [str(item.get("id") or "") for item in items if isinstance(item, dict)]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pick", help="从 stdin 的 /v1/models 响应里挑最新模型")
    p.add_argument("--family", required=True)
    p.add_argument("--fallback", required=True)
    args = parser.parse_args(argv)
    print(pick_latest(model_ids_from_response(sys.stdin.read()), args.family, args.fallback))
    return 0


if __name__ == "__main__":
    sys.exit(main())
