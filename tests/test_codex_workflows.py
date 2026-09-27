"""Fork contract: every workflow that calls an LLM goes through the local Codex proxy.

The proxy (scripts/codex_proxy.sh via .github/actions/codex-proxy) writes the
DEEPSEEK_* / SUMMARY_* / LLM_PRIMARY_BASE_URL variables into GITHUB_ENV. Values
declared in workflow YAML take precedence over GITHUB_ENV, so none of these may
appear in job or step env. The Codex refresh token rotates on every use, so each
job that starts the proxy must end with an always() write-back step.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

# workflow file -> job that calls the LLM
LLM_JOBS = {
    "daily-paper-reader.yml": "run",
    "deep-read-paper.yml": "deep-read",
    "conference-paper-retrieval.yml": "retrieve",
    "starter-pack.yml": "build",
    "topic-research.yml": "research",
}
LLM_ENV_PREFIXES = ("DEEPSEEK_", "SUMMARY_", "LLM_PRIMARY_BASE_URL")
LEGACY_LLM_SECRETS = re.compile(r"secrets\.(DEEPSEEK_|SUMMARY_|LLM_PRIMARY_BASE_URL)")


def load(name):
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def step_index(steps, name):
    for i, step in enumerate(steps):
        if step.get("name") == name:
            return i
    raise AssertionError(f"step {name!r} not found")


@pytest.mark.parametrize("name", sorted(LLM_JOBS))
def test_no_legacy_llm_secrets(name):
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    assert not LEGACY_LLM_SECRETS.search(text), name


@pytest.mark.parametrize("name", sorted(LLM_JOBS))
def test_llm_env_not_declared_in_yaml(name):
    workflow = load(name)
    for job_id, job in workflow["jobs"].items():
        scopes = [("job", job.get("env") or {})]
        scopes += [(step.get("name") or step.get("uses"), step.get("env") or {}) for step in job.get("steps", [])]
        for where, env in scopes:
            bad = [k for k in env if k.startswith(LLM_ENV_PREFIXES)]
            assert not bad, f"{name}:{job_id}:{where} declares {bad}"


@pytest.mark.parametrize("name,job_id", sorted(LLM_JOBS.items()))
def test_job_starts_proxy_after_checkout(name, job_id):
    steps = load(name)["jobs"][job_id]["steps"]
    start = step_index(steps, "Start Codex proxy")
    proxy = steps[start]
    assert proxy["uses"] == "./.github/actions/codex-proxy"
    assert proxy["with"]["auth-json"] == "${{ secrets.CODEX_AUTH_JSON }}"
    assert proxy["with"]["model"].startswith("${{ vars.CODEX_MODEL || '")
    assert proxy["with"]["fast-model"].startswith("${{ vars.CODEX_FAST_MODEL || '")
    checkout = next(i for i, s in enumerate(steps) if str(s.get("uses", "")).startswith("actions/checkout"))
    assert checkout < start


@pytest.mark.parametrize("name,job_id", sorted(LLM_JOBS.items()))
def test_job_ends_with_always_writeback(name, job_id):
    steps = load(name)["jobs"][job_id]["steps"]
    last = steps[-1]
    assert last["name"] == "Write back Codex auth"
    assert last["if"] == "always()"
    assert last["uses"] == "./.github/actions/codex-auth-writeback"
    assert last["with"]["write-token"] == "${{ secrets.CODEX_SECRET_WRITE_TOKEN }}"
    assert step_index(steps, "Start Codex proxy") < len(steps) - 1


def test_proxy_actions_and_script_exist():
    for rel in (
        ".github/actions/codex-proxy/action.yml",
        ".github/actions/codex-auth-writeback/action.yml",
        "scripts/codex_proxy.sh",
        "scripts/codex_auth.py",
    ):
        assert (ROOT / rel).exists(), rel


def test_workflow_model_fallbacks_match_proxy_script_default():
    script = (ROOT / "scripts" / "codex_proxy.sh").read_text(encoding="utf-8")
    m = re.search(r'strong="\$\{CODEX_MODEL:-([^}]+)\}"', script)
    assert m, "codex_proxy.sh default model not found"
    default_strong = m.group(1)
    for name, job_id in LLM_JOBS.items():
        steps = load(name)["jobs"][job_id]["steps"]
        proxy = steps[step_index(steps, "Start Codex proxy")]
        assert proxy["with"]["model"] == f"${{{{ vars.CODEX_MODEL || '{default_strong}' }}}}", name
