"""Run the codex-auth-writeback composite action script the way GitHub does.

GitHub runs composite `run:` steps with `bash --noprofile --norc -e -o pipefail`.
`codex_auth.py export` exits 10 when the credentials changed, which used to end
the script under -e before `gh secret set` ran, so a fresh login was never saved.
"""
import base64
import importlib.util
import json
import os
import stat
import subprocess
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / ".github" / "actions" / "codex-auth-writeback" / "action.yml"
spec = importlib.util.spec_from_file_location("codex_auth", ROOT / "scripts/codex_auth.py")
ca = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ca)


def jwt(claims):
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{enc({'alg': 'none'})}.{enc(claims)}.sig"


def cred(refresh="rt_1"):
    return {
        "type": "codex",
        "access_token": jwt({"exp": time.time() + 200 * 3600}),
        "refresh_token": refresh,
        "id_token": jwt({"email": "me@example.com"}),
    }


def action_script():
    steps = yaml.safe_load(ACTION.read_text(encoding="utf-8"))["runs"]["steps"]
    (step,) = steps
    assert step["shell"] == "bash"
    return step["run"]


@pytest.fixture
def env(tmp_path):
    """Workspace with the real scripts, a fake `gh` that records its stdin, and RUNNER_TEMP."""
    workspace = tmp_path / "ws"
    (workspace / "scripts").mkdir(parents=True)
    for name in ("codex_auth.py", "codex_proxy.sh"):
        (workspace / "scripts" / name).write_bytes((ROOT / "scripts" / name).read_bytes())
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gh_log = tmp_path / "gh.log"
    gh = bindir / "gh"
    gh.write_text(f'#!/usr/bin/env bash\necho "$*" >> "{gh_log}"\ncat >> "{gh_log}"\n', encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    runner_temp = tmp_path / "runner"
    (runner_temp / "codex-proxy" / "auth").mkdir(parents=True)
    base = {k: v for k, v in os.environ.items() if not k.startswith(("GITHUB_", "CODEX_"))}
    base.update(
        PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}",
        GITHUB_WORKSPACE=str(workspace),
        GITHUB_REPOSITORY="owner/repo",
        RUNNER_TEMP=str(runner_temp),
        GH_TOKEN="write-token",
    )
    return {"env": base, "root": runner_temp / "codex-proxy", "gh_log": gh_log}


def run_action(env, write_always):
    e = dict(env["env"], WRITE_ALWAYS=write_always)
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", action_script()],
        env=e, capture_output=True, text=True, timeout=60,
    )


def install(root, data):
    ca.write_auth(root / "auth" / ca.AUTH_FILENAME, data)


def test_login_always_writes_back_under_bash_e(env):
    install(env["root"], cred())
    result = run_action(env, "true")
    assert result.returncode == 0, result.stdout + result.stderr
    log = env["gh_log"].read_text(encoding="utf-8")
    assert log.startswith("secret set CODEX_AUTH_JSON --repo owner/repo")
    assert "rt_1" in log
    assert not (env["root"] / "export.json").exists()


def test_refreshed_credentials_are_written_back(env):
    old = ca.normalize(cred("rt_old"))
    (env["root"] / "installed.sha256").write_text(ca.digest(old), encoding="utf-8")
    install(env["root"], cred("rt_new"))
    result = run_action(env, "false")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "rt_new" in env["gh_log"].read_text(encoding="utf-8")


def test_unchanged_credentials_are_not_written(env):
    data = ca.normalize(cred())
    (env["root"] / "installed.sha256").write_text(ca.digest(data), encoding="utf-8")
    install(env["root"], data)
    result = run_action(env, "false")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not env["gh_log"].exists()


def test_skips_when_proxy_never_installed_credentials(env):
    # CODEX_AUTH_JSON 为空时 install 失败：auth 目录存在但没有凭证，也没有 installed.sha256。
    result = run_action(env, "false")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "跳过写回" in result.stdout
    assert not env["gh_log"].exists()
