#!/usr/bin/env python3
"""把推送到 dispatch/** 分支的请求文件转成一次 workflow_dispatch（fork 专用）。

仓库的自动化助手没有触发 workflow 的权限，但可以推送分支。它推送一个只包含
.github/dispatch-request.json 的提交到 dispatch/<名字> 分支，remote-dispatch workflow
用 GITHUB_TOKEN 调用 `gh workflow run`，目标 workflow 固定在 main 上运行。

请求文件格式：
    {"workflow": "codex-proxy-check.yml", "inputs": {"model": "gpt-5.5"}}

只允许白名单里的 workflow 和它们声明过的输入；输入值必须是单行短字符串或布尔值。
只用标准库。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REF = "main"
MAX_VALUE_LEN = 500

# workflow 文件名 -> 允许的输入名。tests/test_push_dispatch.py 会核对它和各 workflow 的声明一致。
ALLOWED: dict[str, set[str]] = {
    "codex-proxy-check.yml": {"model", "fast_model", "extra_models"},
    "codex-refresh.yml": {"force"},
    "deep-read-paper.yml": {"paper_id", "paper_date"},
    "daily-paper-reader.yml": {"run_enrich", "fetch_days", "fetch_mode", "profile_tag", "reranker_profile"},
}


class RequestError(ValueError):
    pass


def parse_request(data: object) -> tuple[str, dict[str, str]]:
    if not isinstance(data, dict):
        raise RequestError("请求必须是 JSON 对象")
    unknown = set(data) - {"workflow", "inputs"}
    if unknown:
        raise RequestError(f"不认识的字段：{sorted(unknown)}")
    workflow = data.get("workflow")
    if workflow not in ALLOWED:
        raise RequestError(f"不允许的 workflow：{workflow!r}，只允许 {sorted(ALLOWED)}")
    raw_inputs = data.get("inputs") or {}
    if not isinstance(raw_inputs, dict):
        raise RequestError("inputs 必须是对象")
    extra = set(raw_inputs) - ALLOWED[workflow]
    if extra:
        raise RequestError(f"{workflow} 没有这些输入：{sorted(extra)}")
    inputs: dict[str, str] = {}
    for key, value in raw_inputs.items():
        if isinstance(value, bool):
            value = "true" if value else "false"
        elif isinstance(value, (int, float)):
            value = str(value)
        if not isinstance(value, str):
            raise RequestError(f"输入 {key} 必须是字符串、数字或布尔值")
        if "\n" in value or "\r" in value or len(value) > MAX_VALUE_LEN:
            raise RequestError(f"输入 {key} 必须是单行且不超过 {MAX_VALUE_LEN} 个字符")
        inputs[key] = value
    return workflow, inputs


def build_command(workflow: str, inputs: dict[str, str], repo: str) -> list[str]:
    cmd = ["gh", "workflow", "run", workflow, "--repo", repo, "--ref", REF]
    for key in sorted(inputs):
        cmd += ["-f", f"{key}={inputs[key]}"]
    return cmd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--request", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--dry-run", action="store_true", help="只打印要执行的命令")
    args = parser.parse_args(argv)
    try:
        data = json.loads(Path(args.request).read_text(encoding="utf-8"))
        workflow, inputs = parse_request(data)
    except (OSError, json.JSONDecodeError, RequestError) as exc:
        print(f"::error::[dispatch] 请求无效：{exc}", file=sys.stderr)
        return 1
    cmd = build_command(workflow, inputs, args.repo)
    print(f"[dispatch] {workflow} @ {REF} inputs={json.dumps(inputs, ensure_ascii=False)}", flush=True)
    if args.dry_run:
        print(json.dumps(cmd, ensure_ascii=False))
        return 0
    return subprocess.run(cmd, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
