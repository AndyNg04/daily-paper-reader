#!/usr/bin/env python3
"""检查并应用 CLIProxyAPI 新版本（fork 专用，由 codex-proxy-update workflow 调用，只依赖标准库）。

  check   比较 scripts/codex_proxy.sh 里固定的版本和 GitHub 最新 release，
          有新版本时向 $GITHUB_OUTPUT 写 changed=true / version / current
  apply   下载新版本的 checksums.txt 和 linux_amd64_no-plugin 安装包，校验 sha256 后
          改写 codex_proxy.sh 里的 CPA_VERSION / CPA_SHA256

脚本只改版本号和校验和；新版本能不能用由 workflow 接着启动 proxy 跑兼容性检查来确认，
再开 PR 交给人合并，不会直接改 main。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO = "router-for-me/CLIProxyAPI"
SCRIPT = Path(__file__).resolve().parent / "codex_proxy.sh"
ASSET = "CLIProxyAPI_{version}_linux_amd64_no-plugin.tar.gz"
VERSION_RE = re.compile(r'^CPA_VERSION="([0-9]+(?:\.[0-9]+)*)"$', re.M)
SHA_RE = re.compile(r'^CPA_SHA256="([0-9a-f]{64})"$', re.M)


def parse_version(text: str) -> tuple[int, ...]:
    text = str(text or "").strip().lstrip("v")
    if not re.fullmatch(r"\d+(?:\.\d+)*", text):
        raise ValueError(f"不是版本号：{text!r}")
    return tuple(int(part) for part in text.split("."))


def current_version(script_text: str) -> str:
    m = VERSION_RE.search(script_text)
    if not m:
        raise ValueError("codex_proxy.sh 里找不到 CPA_VERSION")
    return m.group(1)


def http_get(url: str, accept: str = "application/octet-stream") -> bytes:
    headers = {"Accept": accept, "User-Agent": "dpr-codex-proxy-update"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def latest_release(fetch=http_get) -> str:
    data = json.loads(fetch(f"https://api.github.com/repos/{REPO}/releases/latest", "application/vnd.github+json"))
    if data.get("draft") or data.get("prerelease"):
        raise ValueError("最新 release 是草稿或预发布")
    return str(data["tag_name"]).lstrip("v")


def sha_from_checksums(checksums: str, asset: str) -> str:
    for line in checksums.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == asset and re.fullmatch(r"[0-9a-f]{64}", parts[0]):
            return parts[0]
    raise ValueError(f"checksums.txt 里没有 {asset}")


def rewrite_script(script_text: str, version: str, sha256: str) -> str:
    parse_version(version)
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ValueError("sha256 格式不对")
    out, n1 = VERSION_RE.subn(f'CPA_VERSION="{version}"', script_text)
    out, n2 = SHA_RE.subn(f'CPA_SHA256="{sha256}"', out)
    if n1 != 1 or n2 != 1:
        raise ValueError("codex_proxy.sh 里的 CPA_VERSION / CPA_SHA256 不是恰好一处")
    return out


def write_output(**values: str) -> None:
    path = os.getenv("GITHUB_OUTPUT")
    lines = "".join(f"{k}={v}\n" for k, v in values.items())
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(lines)
    print(lines, end="")


def cmd_check(args, fetch=http_get) -> int:
    current = current_version(SCRIPT.read_text(encoding="utf-8"))
    latest = latest_release(fetch)
    changed = parse_version(latest) > parse_version(current)
    print(f"[codex-proxy-update] 当前 v{current}，最新 v{latest}")
    write_output(changed="true" if changed else "false", version=latest, current=current)
    return 0


def cmd_apply(args, fetch=http_get) -> int:
    version = args.version.lstrip("v")
    asset = ASSET.format(version=version)
    base = f"https://github.com/{REPO}/releases/download/v{version}"
    expected = sha_from_checksums(fetch(f"{base}/checksums.txt").decode("utf-8"), asset)
    actual = hashlib.sha256(fetch(f"{base}/{asset}")).hexdigest()
    if actual != expected:
        raise ValueError(f"{asset} 的 sha256 与 checksums.txt 不一致")
    SCRIPT.write_text(rewrite_script(SCRIPT.read_text(encoding="utf-8"), version, actual), encoding="utf-8")
    print(f"[codex-proxy-update] 已把 codex_proxy.sh 升级到 v{version}（sha256 {actual}）")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(func=cmd_check)
    p = sub.add_parser("apply")
    p.add_argument("--version", required=True)
    p.set_defaults(func=cmd_apply)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
