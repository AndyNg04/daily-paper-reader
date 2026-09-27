"""Fork-specific contract for the automatic upstream sync.

GITHUB_TOKEN cannot push commits that touch .github/workflows/, so the sync
squashes the merge result into a single-parent commit and records the merged
upstream SHA in a state file that serves as the next merge base.
"""
import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SYNC_WORKFLOW = ROOT / ".github" / "workflows" / "sync.yml"
SCHEDULE_WORKFLOW = ROOT / ".github" / "workflows" / "upstream-sync-schedule.yml"
STATE_FILE = ROOT / ".github" / "upstream-sync-state.json"
GITATTRIBUTES = ROOT / ".gitattributes"


def _merge_step_script():
    workflow = yaml.safe_load(SYNC_WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["sync_latest_from_upstream"]["steps"]
    (step,) = [s for s in steps if s.get("name") == "Merge upstream changes"]
    return step["run"]


def test_schedule_workflow_calls_sync_workflow():
    workflow = yaml.safe_load(SCHEDULE_WORKFLOW.read_text(encoding="utf-8"))
    assert "schedule" in workflow[True], "scheduled caller must define a cron trigger"
    assert workflow["permissions"] == {"contents": "write"}
    (job,) = workflow["jobs"].values()
    assert job["uses"] == "./.github/workflows/sync.yml"
    # Same concurrency group on caller and callee would deadlock; it lives in sync.yml.
    assert "concurrency" not in job
    sync = yaml.safe_load(SYNC_WORKFLOW.read_text(encoding="utf-8"))
    assert sync["jobs"]["sync_latest_from_upstream"]["concurrency"]["group"] == "upstream-sync"


def test_sync_workflow_is_callable_and_manual():
    workflow = yaml.safe_load(SYNC_WORKFLOW.read_text(encoding="utf-8"))
    triggers = workflow[True]
    assert "workflow_dispatch" in triggers
    assert "workflow_call" in triggers


def test_sync_merges_from_recorded_upstream_base():
    script = _merge_step_script()
    assert 'git merge-tree --write-tree --name-only --merge-base="$base"' in script
    assert "git merge-base --is-ancestor" in script
    assert 'git merge-base HEAD "$upstream_sha"' in script, "must fall back to git merge-base"
    assert "git reset --soft" not in script


def test_sync_keeps_fork_workflows_without_pat():
    script = _merge_step_script()
    assert 'if [ "$KEEP_FORK_WORKFLOWS" = "true" ]' in script
    assert "git restore --source=HEAD --staged --worktree -- .github/workflows" in script
    text = SYNC_WORKFLOW.read_text(encoding="utf-8")
    assert "secrets.UPSTREAM_SYNC_TOKEN || github.token" in text


def test_sync_state_file_is_valid():
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    assert state["upstream_repo"] == "ziwenhahaha/daily-paper-reader"
    assert state["upstream_branch"] == "main"
    assert re.fullmatch(r"[0-9a-f]{40}", state["upstream_sha"])


def test_gitattributes_protect_fork_metadata():
    text = GITATTRIBUTES.read_text(encoding="utf-8")
    for path in (
        ".github/upstream-sync-state.json",
        ".github/workflows/*.yml",
        ".gitattributes",
        "config.yaml",
        "secret.private",
    ):
        assert re.search(rf"^{re.escape(path)} merge=ours$", text, re.M), path
