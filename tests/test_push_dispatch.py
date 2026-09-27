"""Fork contract for remote-dispatch: push a request to dispatch/** to run an allow-listed workflow on main."""
import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
spec = importlib.util.spec_from_file_location("dispatch_request", ROOT / "scripts" / "dispatch_request.py")
dr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dr)


def load(name):
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def triggers(workflow):
    return workflow.get("on", workflow.get(True))


@pytest.mark.parametrize("name", sorted(dr.ALLOWED))
def test_allowlist_matches_declared_inputs(name):
    declared = set((triggers(load(name))["workflow_dispatch"] or {}).get("inputs") or {})
    assert dr.ALLOWED[name] == declared


def test_login_is_not_dispatchable():
    # 设备码登录必须有人在浏览器里授权，不能远程触发。
    assert "codex-login.yml" not in dr.ALLOWED


def test_parse_request_accepts_valid_and_normalizes_values():
    wf, inputs = dr.parse_request({"workflow": "codex-refresh.yml", "inputs": {"force": True}})
    assert (wf, inputs) == ("codex-refresh.yml", {"force": "true"})
    wf, inputs = dr.parse_request({"workflow": "daily-paper-reader.yml", "inputs": {"fetch_days": 3}})
    assert inputs == {"fetch_days": "3"}
    assert dr.parse_request({"workflow": "codex-proxy-check.yml"}) == ("codex-proxy-check.yml", {})


@pytest.mark.parametrize(
    "request_data",
    [
        [],
        {"workflow": "codex-login.yml"},
        {"workflow": "sync.yml"},
        {"workflow": "codex-proxy-check.yml", "ref": "other"},
        {"workflow": "codex-proxy-check.yml", "inputs": {"nope": "x"}},
        {"workflow": "codex-proxy-check.yml", "inputs": {"model": "a\nb"}},
        {"workflow": "codex-proxy-check.yml", "inputs": {"model": "x" * 501}},
        {"workflow": "codex-proxy-check.yml", "inputs": {"model": ["gpt"]}},
        {"workflow": "codex-proxy-check.yml", "inputs": "model=x"},
    ],
)
def test_parse_request_rejects_invalid(request_data):
    with pytest.raises(dr.RequestError):
        dr.parse_request(request_data)


def test_build_command_targets_main_with_sorted_fields():
    cmd = dr.build_command("deep-read-paper.yml", {"paper_id": "2609.1v1", "paper_date": "20260926"}, "o/r")
    assert cmd == ["gh", "workflow", "run", "deep-read-paper.yml", "--repo", "o/r", "--ref", "main",
                   "-f", "paper_date=20260926", "-f", "paper_id=2609.1v1"]


def test_main_dry_run_and_invalid_file(tmp_path, capsys):
    req = tmp_path / "r.json"
    req.write_text(json.dumps({"workflow": "codex-proxy-check.yml", "inputs": {"model": "gpt-5.5"}}), encoding="utf-8")
    assert dr.main(["--request", str(req), "--repo", "o/r", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert '"-f", "model=gpt-5.5"' in out
    req.write_text("{not json", encoding="utf-8")
    assert dr.main(["--request", str(req), "--repo", "o/r", "--dry-run"]) == 1
    assert dr.main(["--request", str(tmp_path / "missing.json"), "--repo", "o/r", "--dry-run"]) == 1


def test_workflow_contract():
    text = (WORKFLOWS / "remote-dispatch.yml").read_text(encoding="utf-8")
    wf = yaml.safe_load(text)
    assert triggers(wf) == {"push": {"branches": ["dispatch/**"]}}
    assert wf["permissions"] == {"actions": "write", "contents": "write"}
    (job,) = wf["jobs"].values()
    assert job["if"] == "github.repository != 'ziwenhahaha/daily-paper-reader'"
    steps = job["steps"]
    checkout = steps[0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert "docs" not in checkout["with"]["sparse-checkout"]
    for step in steps:
        run = step.get("run") or ""
        assert "${{" not in run, step["name"]
        assert "secrets." not in json.dumps(step)
    assert steps[1]["env"]["GH_TOKEN"] == "${{ github.token }}"
    last = steps[-1]
    assert last["if"] == "always()"
    assert 'git push origin --delete "refs/heads/${GITHUB_REF_NAME}"' in last["run"]
