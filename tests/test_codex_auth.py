"""Codex 凭证管理与 codex-* workflow 的结构约束（fork 专用）。"""

import base64
import importlib.util
import json
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("codex_auth", ROOT / "scripts/codex_auth.py")
ca = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ca)


def jwt(claims: dict) -> str:
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{enc({'alg': 'none'})}.{enc(claims)}.sig"


def cred(exp_in_hours: float = 200, refresh="rt_old", access_extra="a") -> dict:
    exp = time.time() + exp_in_hours * 3600
    return {
        "type": "codex",
        "access_token": jwt({"exp": exp, "x": access_extra}),
        "refresh_token": refresh,
        "id_token": jwt({"email": "me@example.com",
                         "https://api.openai.com/auth": {"chatgpt_account_id": "acc_1"}}),
    }


def test_normalize_accepts_codex_cli_format():
    cli = {"OPENAI_API_KEY": None, "tokens": {k: v for k, v in cred().items() if k != "type"},
           "last_refresh": "2026-09-01T00:00:00Z"}
    data = ca.normalize(cli)
    assert data["type"] == "codex" and data["refresh_token"] == "rt_old"
    assert data["email"] == "me@example.com" and data["account_id"] == "acc_1"
    assert "tokens" not in data and "OPENAI_API_KEY" not in data
    assert data["expired"].endswith("Z")


@pytest.mark.parametrize("bad", [{}, {"type": "claude", "refresh_token": "x"}, {"access_token": "a"}])
def test_normalize_rejects_bad_credentials(bad):
    with pytest.raises(ca.CodexAuthError):
        ca.normalize(bad)


def test_hours_left_prefers_access_token_exp():
    assert 199 < ca.hours_left(cred(200)) <= 200


def test_refresh_rotates_tokens_and_keeps_identity():
    seen = {}

    def fake_post(rt):
        seen["rt"] = rt
        return {"access_token": jwt({"exp": time.time() + 864000}), "refresh_token": "rt_new", "expires_in": 864000}

    new = ca.refresh(ca.normalize(cred(10)), post=fake_post)
    assert seen["rt"] == "rt_old"
    assert new["refresh_token"] == "rt_new" and new["email"] == "me@example.com"
    assert ca.hours_left(new) > 239


def test_refresh_rejects_incomplete_response():
    with pytest.raises(ca.CodexAuthError):
        ca.refresh(ca.normalize(cred()), post=lambda rt: {"access_token": "a"})


def run(argv, monkeypatch, env=None):
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    return ca.main(argv)


def test_install_refresh_export_cycle(tmp_path, monkeypatch, capsys):
    auth_dir, digest = tmp_path / "auth", tmp_path / "installed.sha256"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert run(["install", "--dir", str(auth_dir), "--digest-out", str(digest)], monkeypatch,
               {"CODEX_AUTH_JSON": json.dumps(cred(200))}) == 0
    assert oct((auth_dir / "codex.json").stat().st_mode & 0o777) == "0o600"

    # 剩余 200 小时 > 阈值：不刷新，export 报告未变化。
    monkeypatch.setattr(ca, "post_refresh", lambda rt: pytest.fail("不应刷新"))
    assert ca.main(["refresh", "--dir", str(auth_dir), "--min-hours", "96"]) == 0
    out = tmp_path / "out.json"
    assert ca.main(["export", "--dir", str(auth_dir), "--out", str(out), "--digest-in", str(digest)]) == 0

    # proxy 只加了元数据字段：不算变化。
    data = json.loads((auth_dir / "codex.json").read_text())
    data["last_refresh"] = "2026-09-27T00:00:00Z"
    (auth_dir / "codex.json").write_text(json.dumps(data))
    assert ca.main(["export", "--dir", str(auth_dir), "--out", str(out), "--digest-in", str(digest)]) == 0

    # 强制刷新后 export 报告变化（退出码 10），导出的是新凭证。
    monkeypatch.setattr(ca, "post_refresh", lambda rt: {
        "access_token": jwt({"exp": time.time() + 864000, "n": 2}), "refresh_token": "rt_new", "expires_in": 864000})
    assert ca.main(["refresh", "--dir", str(auth_dir), "--force"]) == 0
    assert ca.main(["export", "--dir", str(auth_dir), "--out", str(out), "--digest-in", str(digest)]) == 10
    assert json.loads(out.read_text())["refresh_token"] == "rt_new"

    # 日志里只有打码命令，普通输出行不含任何 token。
    lines = capsys.readouterr().out.splitlines()
    for line in lines:
        if line.startswith("::add-mask::"):
            continue
        for secret in ("rt_old", "rt_new", "me@example.com", "acc_1", "eyJ"):
            assert secret not in line


def test_install_fails_clearly_without_secret(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("CODEX_AUTH_JSON", raising=False)
    assert ca.main(["install", "--dir", str(tmp_path)]) == 1
    assert "Codex 登录 workflow" in capsys.readouterr().err


def test_find_auth_picks_newest_codex_file(tmp_path):
    (tmp_path / "other.json").write_text(json.dumps({"type": "claude"}))
    (tmp_path / "codex.json").write_text(json.dumps(cred(refresh="rt_a")))
    time.sleep(0.01)
    newer = tmp_path / "codex-me@example.com.json"
    newer.write_text(json.dumps(cred(refresh="rt_b")))
    assert ca.find_auth(tmp_path) == newer


def load_wf(name):
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["codex-login.yml", "codex-refresh.yml", "codex-proxy-check.yml"])
def test_codex_workflows_guarded_serialized_and_write_back(name):
    wf = load_wf(name)
    assert wf["concurrency"]["group"] == "codex-auth"
    assert wf["permissions"] == {"contents": "read"}
    (job,) = wf["jobs"].values()
    assert job["if"] == "github.repository != 'ziwenhahaha/daily-paper-reader'"
    last = job["steps"][-1]
    assert last["uses"] == "./.github/actions/codex-auth-writeback" and last["if"] == "always()"
    text = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
    assert "cat " not in text and "set -x" not in text


def test_proxy_script_pins_and_verifies_binary():
    sh = (ROOT / "scripts/codex_proxy.sh").read_text(encoding="utf-8")
    assert 'CPA_VERSION="7.3.20"' in sh and "sha256sum -c" in sh
    assert 'host: "127.0.0.1"' in sh and "::add-mask::" in sh
    assert 'ROOT="${CODEX_PROXY_ROOT:-${RUNNER_TEMP:-/tmp}/codex-proxy}"' in sh
