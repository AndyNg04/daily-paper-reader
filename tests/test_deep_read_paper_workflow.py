""".github/workflows/deep-read-paper.yml 的静态合同（fork 专用 workflow）。"""

import re
import shlex
from pathlib import Path

import pytest
import yaml

from src import deep_read_paper as drp

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deep-read-paper.yml"
CANONICAL_REPOSITORY = "ziwenhahaha/daily-paper-reader"
COMMIT_STEP = "Commit deep read results"


@pytest.fixture(scope="module")
def text():
    return WORKFLOW_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def workflow(text):
    return yaml.safe_load(text)


@pytest.fixture(scope="module")
def job(workflow):
    jobs = workflow["jobs"]
    assert list(jobs) == ["deep-read"]
    return jobs["deep-read"]


def steps_by_name(job):
    return {step.get("name"): step for step in job["steps"]}


def test_only_manual_dispatch_with_required_inputs(workflow):
    # PyYAML 把裸 `on` 解析成 True
    triggers = workflow.get("on", workflow.get(True))
    assert list(triggers) == ["workflow_dispatch"]
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"paper_id", "paper_date"}
    for name in ("paper_id", "paper_date"):
        assert inputs[name]["required"] is True
        assert inputs[name]["type"] == "string"


def test_commit_step_is_guarded_like_upstream_boundary_test(text, job):
    # 与 tests/test_upstream_runtime_boundary.py 的正则同一风格
    pattern = re.compile(
        rf"- name: {re.escape(COMMIT_STEP)}\n\s+if: github\.repository != '{re.escape(CANONICAL_REPOSITORY)}'"
    )
    assert pattern.search(text)
    assert job["if"] == f"github.repository != '{CANONICAL_REPOSITORY}'"


def test_no_expression_interpolation_inside_run_scripts(job):
    for step in job["steps"]:
        script = step.get("run")
        if script is None:
            continue
        assert "${{" not in script, step["name"]
        assert "github.event.inputs" not in script, step["name"]


def test_inputs_reach_scripts_only_through_env(job):
    steps = steps_by_name(job)
    validate = steps["Validate inputs and locate paper"]
    assert validate["env"] == {
        "INPUT_PAPER_ID": "${{ inputs.paper_id }}",
        "INPUT_PAPER_DATE": "${{ inputs.paper_date }}",
    }
    assert validate["id"] == "target"
    for name in ("Generate deep summary", COMMIT_STEP):
        env = steps[name]["env"]
        assert env["PAPER_ID"] == "${{ steps.target.outputs.paper_id }}"
        assert env["PAPER_DATE"] == "${{ steps.target.outputs.paper_date }}"
    # 原始输入不会越过校验步骤
    for step in job["steps"]:
        if step is validate:
            continue
        assert "inputs." not in str(step.get("env", {})), step["name"]


def test_step_order(job):
    names = [step["name"] for step in job["steps"]]
    assert names == [
        "Checkout",
        "Setup Python",
        "Validate inputs and locate paper",
        "Cache Python deps",
        "Install deps (skip sqlite3)",
        "Start Codex proxy",
        "Generate deep summary",
        COMMIT_STEP,
        "Write back Codex auth",
    ]


def test_scripts_use_strict_bash(job):
    assert job["defaults"]["run"]["shell"] == "bash"
    for step in job["steps"]:
        if "run" in step:
            assert "set -euo pipefail" in step["run"], step["name"]


def test_lightweight_install_without_torch_or_papercropper(job):
    for step in job["steps"]:
        script = step.get("run") or ""
        assert "torch" not in script, step["name"]
        assert "PaperCropper" not in script and "papercropper" not in script, step["name"]
        assert "requirements-paper-media" not in script, step["name"]
        assert "doclayout" not in script.lower(), step["name"]
        assert "cache/dpr-tools" not in str(step.get("with", {})), step["name"]
    generate = steps_by_name(job)["Generate deep summary"]
    assert generate["env"]["PAPERCROPPER_DISABLE"] == "1"


def test_only_codex_secrets_are_used(text, job):
    # LLM 走本机 Codex proxy：只允许 proxy 的凭证和写回 token 两个 secret，且只出现在这两个步骤里。
    secrets = set(re.findall(r"secrets\.([A-Z0-9_]+)", text))
    assert secrets == {"CODEX_AUTH_JSON", "CODEX_SECRET_WRITE_TOKEN"}
    for step in job["steps"]:
        if step.get("name") not in ("Start Codex proxy", "Write back Codex auth"):
            assert "secrets." not in str(step.get("env", {})), step["name"]
            assert "secrets." not in str(step.get("with", {})), step["name"]
    assert "secrets." not in str(job.get("env", {}))


def test_generate_step_reads_llm_env_from_codex_proxy(job):
    # proxy 把 DEEPSEEK_* / SUMMARY_* 写进 GITHUB_ENV；步骤级 env 里再声明会盖过它。
    names = [step.get("name") for step in job["steps"]]
    assert names.index("Start Codex proxy") < names.index("Generate deep summary")
    env = steps_by_name(job)["Generate deep summary"]["env"]
    assert not [k for k in env if k.startswith(("DEEPSEEK_", "SUMMARY_", "LLM_PRIMARY"))]


def test_codex_writeback_runs_last_after_commit_reset(job):
    # 提交步骤会 git reset --hard FETCH_HEAD，写回用的 action 与脚本要在最新 main 上存在，
    # 所以写回必须放在提交步骤之后，并且是最后一步。
    last = job["steps"][-1]
    assert last["name"] == "Write back Codex auth"
    assert last["if"] == "always()"
    assert last["uses"] == "./.github/actions/codex-auth-writeback"
    names = [step.get("name") for step in job["steps"]]
    assert names.index(COMMIT_STEP) < names.index("Write back Codex auth")
    assert (ROOT / ".github" / "actions" / "codex-auth-writeback" / "action.yml").exists()
    assert (ROOT / "scripts" / "codex_proxy.sh").exists()


def test_permissions_timeout_and_concurrency(workflow, job):
    assert workflow["permissions"] == {"contents": "write"}
    assert 30 <= job["timeout-minutes"] <= 45
    concurrency = workflow["concurrency"]
    assert concurrency["cancel-in-progress"] is False
    group = concurrency["group"]
    # 不能与日报共用并发组（同组新排队的运行会顶掉已 pending 的运行）
    assert group != "daily-paper-reader"
    assert "inputs.paper_id" in group and "inputs.paper_date" in group


def test_concurrency_comment_documents_daily_push_rejection(text):
    # 本 workflow 与日报不串行，日报推送可能被拒（日报会有限次重试）；注释里必须写明这个竞态和恢复方式。
    header = text.split("\nconcurrency:", 1)[0]
    assert "日报推送被拒" in header
    assert "重跑日报" in header


def test_commit_step_stages_deliberately_and_never_force_pushes(job):
    script = steps_by_name(job)[COMMIT_STEP]["run"]
    assert "--force" not in script and "push -f" not in script and "+HEAD" not in script
    assert 'git push origin "HEAD:refs/heads/${branch}"' in script
    assert 'branch="${GITHUB_REF_NAME}"' in script
    assert "git reset -q --hard FETCH_HEAD" in script
    assert "git clean -fdq -- docs" in script
    assert 'git add -A -- "${paths[@]}"' in script
    assert "git add docs" not in script and "git add -A docs" not in script
    assert 'git commit -q -m "[chore] deep read ${PAPER_ID}"' in script
    assert re.search(r"max_attempts=[3-5]\b", script)
    assert 'git config user.name "github-actions[bot]"' in script
    # 没有改动时必须在 git commit 之前 exit 0（重跑已升级的论文不能因为空提交失败）
    assert re.search(
        r"if git diff --cached --quiet; then\n(?:\s+echo [^\n]*\n)?\s+exit 0\n\s+fi\n", script
    )
    assert script.index("git diff --cached --quiet") < script.index("git commit")
    # reset 之前把脚本固定到 RUNNER_TEMP，循环里不再调用被 reset 替换过的 src/ 版本
    assert script.index('cp src/deep_read_paper.py "$drp"') < script.index("git reset -q --hard FETCH_HEAD")
    assert "python src/deep_read_paper.py" not in script


def test_validate_step_rejects_non_branch_refs(job):
    script = steps_by_name(job)["Validate inputs and locate paper"]["run"]
    assert '"${GITHUB_REF_TYPE}" != "branch"' in script


def test_workflow_calls_existing_cli_subcommands_with_valid_arguments(job):
    parser = drp.build_parser()
    subparsers = next(a for a in parser._actions if a.dest == "command")
    calls = []
    for step in job["steps"]:
        script = step.get("run") or ""
        joined = script.replace("\\\n", " ")
        for match in re.finditer(r'python (?:src/deep_read_paper\.py|"\$drp") ([^)\n]*)', joined):
            calls.append(shlex.split(match.group(1)))
    assert [c[0] for c in calls] == ["resolve", "generate", "apply", "promote", "paths"]
    for argv in calls:
        assert argv[0] in subparsers.choices
        # 用占位值替换 shell 变量后，参数必须能被真实的 argparse 接受
        substituted = [re.sub(r"\$\{?[A-Z_]+\}?", "x", arg) for arg in argv]
        parser.parse_args(substituted)


def test_generate_and_apply_share_the_same_stash_directory(job):
    steps = steps_by_name(job)
    generate = steps["Generate deep summary"]["run"].replace("\\\n", " ")
    commit = steps[COMMIT_STEP]["run"]
    gen_stash = re.search(r'--stash ("[^"]+"|\S+)', generate).group(1)
    assigned = re.search(r'^\s*stash=("[^"]+"|\S+)$', commit, re.M).group(1)
    assert gen_stash == assigned == '"$RUNNER_TEMP/deep-read"'
    assert '--stash "$stash"' in commit
