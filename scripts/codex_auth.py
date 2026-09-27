#!/usr/bin/env python3
"""Codex（ChatGPT 订阅）登录凭证的安装、刷新、导出（fork 专用，只依赖标准库）。

凭证文件是 CLIProxyAPI 的格式（type=codex）。也接受 Codex CLI 的 ~/.codex/auth.json
（{"tokens": {...}}），安装时会转换。

refresh token 每用一次就作废并换一个新的，所以凭证一旦刷新，必须写回 repo secret
CODEX_AUTH_JSON，否则下一次运行拿到的是作废的旧凭证。

仓库是公开的，运行日志任何人都能看：本脚本从不打印凭证内容，并对所有 token 输出
::add-mask::（刷新出来的新 token 不是已注册的 secret，GitHub 不会自动打码）。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TOKEN_URL = "https://auth.openai.com/oauth/token"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTH_FILENAME = "codex.json"
SENSITIVE_KEYS = ("access_token", "refresh_token", "id_token", "email", "account_id")


class CodexAuthError(Exception):
    pass


def log(msg: str) -> None:
    print(msg, flush=True)


def mask(data: dict) -> None:
    # 只在 GitHub Actions 里输出 mask 命令；本地运行时打印 token 反而会泄露到终端。
    if os.getenv("GITHUB_ACTIONS") != "true":
        return
    for key in SENSITIVE_KEYS:
        value = str(data.get(key) or "").strip()
        if value:
            print(f"::add-mask::{value}", flush=True)


def normalize(raw: dict) -> dict:
    """把 Codex CLI 或 CLIProxyAPI 两种格式统一成 CLIProxyAPI 的 codex 凭证。"""
    if not isinstance(raw, dict):
        raise CodexAuthError("凭证不是 JSON 对象")
    src = raw.get("tokens") if isinstance(raw.get("tokens"), dict) else raw
    data = {k: v for k, v in raw.items() if k not in ("tokens", "OPENAI_API_KEY")}
    for key in ("id_token", "access_token", "refresh_token", "account_id"):
        if src.get(key):
            data[key] = src[key]
    if not str(data.get("refresh_token") or "").strip():
        raise CodexAuthError("凭证里没有 refresh_token")
    if data.get("type") not in (None, "", "codex"):
        raise CodexAuthError(f"凭证 type={data.get('type')!r}，不是 codex")
    data["type"] = "codex"
    if not data.get("email"):
        data["email"] = jwt_claims(data.get("id_token")).get("email", "")
    if not data.get("account_id"):
        auth = jwt_claims(data.get("id_token")).get("https://api.openai.com/auth") or {}
        data["account_id"] = auth.get("chatgpt_account_id", "")
    if not data.get("expired"):
        exp = jwt_claims(data.get("access_token")).get("exp")
        if exp:
            data["expired"] = iso(float(exp))
    return data


def jwt_claims(token) -> dict:
    try:
        payload = str(token).split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def expiry_ts(data: dict) -> float | None:
    exp = jwt_claims(data.get("access_token")).get("exp")
    if exp:
        return float(exp)
    raw = str(data.get("expired") or "").strip()
    if raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def hours_left(data: dict, now: float | None = None) -> float | None:
    exp = expiry_ts(data)
    if exp is None:
        return None
    return (exp - (time.time() if now is None else now)) / 3600.0


def read_auth(path: Path) -> dict:
    try:
        return normalize(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise CodexAuthError(f"读不了凭证文件 {path.name}: {type(exc).__name__}") from None


def write_auth(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def find_auth(auth_dir: Path) -> Path:
    """CLIProxyAPI 登录或刷新后可能用自己的文件名保存，取最新的 codex 凭证。"""
    found = []
    for path in auth_dir.glob("*.json"):
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("type") == "codex":
                found.append(path)
        except (OSError, json.JSONDecodeError, AttributeError):
            continue
    if not found:
        raise CodexAuthError("凭证目录里没有 codex 凭证")
    return max(found, key=lambda p: p.stat().st_mtime)


def digest(data: dict) -> str:
    # 只比较 token：proxy 可能给文件加元数据字段，那不需要写回。
    tokens = [str(data.get(k) or "") for k in ("refresh_token", "access_token")]
    return hashlib.sha256("\n".join(tokens).encode("utf-8")).hexdigest()


def post_refresh(refresh_token: str, timeout: float = 30.0) -> dict:
    body = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "openid profile email",
    }).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 错误体里只取 error 代码，不回显可能带 token 的内容。
        code = ""
        try:
            err = json.loads(exc.read().decode("utf-8")).get("error")
            code = err.get("code") if isinstance(err, dict) else str(err or "")
        except Exception:
            pass
        raise CodexAuthError(f"刷新失败 HTTP {exc.code} {code}".strip()) from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise CodexAuthError(f"刷新请求失败: {type(exc).__name__}") from None


def refresh(data: dict, now: float | None = None, post=None) -> dict:
    resp = (post or post_refresh)(str(data["refresh_token"]))
    if not resp.get("access_token") or not resp.get("refresh_token"):
        raise CodexAuthError("刷新响应里缺少 token")
    now = time.time() if now is None else now
    new = dict(data)
    new["access_token"] = resp["access_token"]
    new["refresh_token"] = resp["refresh_token"]
    if resp.get("id_token"):
        new["id_token"] = resp["id_token"]
    new["last_refresh"] = iso(now)
    if resp.get("expires_in"):
        new["expired"] = iso(now + float(resp["expires_in"]))
    else:
        new.pop("expired", None)
    return normalize(new)


def describe(data: dict) -> str:
    left = hours_left(data)
    return "剩余有效期未知" if left is None else f"access token 剩余 {left:.1f} 小时"


def cmd_install(args) -> int:
    raw = os.getenv(args.env, "")
    if not raw.strip():
        raise CodexAuthError(f"环境变量 {args.env} 为空：先运行 Codex 登录 workflow")
    try:
        data = normalize(json.loads(raw))
    except json.JSONDecodeError:
        raise CodexAuthError(f"{args.env} 不是合法 JSON") from None
    mask(data)
    path = Path(args.dir) / AUTH_FILENAME
    write_auth(path, data)
    log(f"[codex-auth] 已安装凭证，{describe(data)}")
    if args.digest_out:
        Path(args.digest_out).write_text(digest(data), encoding="utf-8")
    return 0


def cmd_refresh(args) -> int:
    path = find_auth(Path(args.dir))
    data = read_auth(path)
    mask(data)
    left = hours_left(data)
    if not args.force and left is not None and left > args.min_hours:
        log(f"[codex-auth] 不需要刷新，{describe(data)}（阈值 {args.min_hours} 小时）")
        return 0
    new = refresh(data)
    mask(new)
    write_auth(path, new)
    log(f"[codex-auth] 已刷新，{describe(new)}")
    return 0


def cmd_status(args) -> int:
    data = read_auth(find_auth(Path(args.dir)))
    mask(data)
    log(f"[codex-auth] {describe(data)}")
    return 0


def cmd_export(args) -> int:
    """输出当前凭证（给 gh secret set），并告诉调用方它和安装时相比是否变了。"""
    data = read_auth(find_auth(Path(args.dir)))
    mask(data)
    write_auth(Path(args.out), data)
    changed = True
    if args.digest_in and Path(args.digest_in).exists():
        changed = Path(args.digest_in).read_text(encoding="utf-8").strip() != digest(data)
    log(f"[codex-auth] 凭证{'已变化' if changed else '未变化'}，{describe(data)}")
    return 10 if changed else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("install", help="从环境变量安装凭证到凭证目录")
    p.add_argument("--dir", required=True)
    p.add_argument("--env", default="CODEX_AUTH_JSON")
    p.add_argument("--digest-out")
    p.set_defaults(func=cmd_install)
    p = sub.add_parser("refresh", help="剩余有效期低于阈值时刷新")
    p.add_argument("--dir", required=True)
    p.add_argument("--min-hours", type=float, default=96.0)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_refresh)
    p = sub.add_parser("status", help="打印剩余有效期")
    p.add_argument("--dir", required=True)
    p.set_defaults(func=cmd_status)
    p = sub.add_parser("export", help="导出当前凭证；变化时退出码 10")
    p.add_argument("--dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--digest-in")
    p.set_defaults(func=cmd_export)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CodexAuthError as exc:
        print(f"::error::[codex-auth] {exc}" if os.getenv("GITHUB_ACTIONS") == "true" else f"[codex-auth] {exc}",
              file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
