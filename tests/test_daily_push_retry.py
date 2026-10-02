"""日报 Commit results 推送被拒时重试的回归测试（fork 专用）。

模拟：日报 job 提交后、第一次 push 前，另一个 workflow（如 deep-read-paper）抢先推送了 main。
期望：日报 fetch + rebase 后重试成功，远端同时保留两边的提交，且从不 force push。
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _commit_step_script():
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/daily-paper-reader.yml").read_text(encoding="utf-8")
    )
    step = next(
        s for s in workflow["jobs"]["run"]["steps"] if s.get("name") == "Commit results"
    )
    return step["run"]


def _git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


class DailyPushRetryTest(unittest.TestCase):
    def test_commit_step_retries_push_without_force(self):
        script = _commit_step_script()
        self.assertIn("max_attempts=5", script)
        self.assertNotIn("--force", script)
        self.assertNotIn("push -f", script)
        loop = script[script.index("while true; do"):]
        # 每次重试都要先同步远端再推送，long-range 索引重建也在 rebase 之后。
        self.assertLess(loop.index("git fetch origin"), loop.index("git rebase -X theirs"))
        self.assertLess(loop.index("git rebase -X theirs"), loop.index("--rebuild-index"))
        self.assertLess(loop.index("--rebuild-index"), loop.index("git push origin"))

    def test_push_rejected_once_then_retried(self):
        script = _commit_step_script()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            origin = root / "origin.git"
            work = root / "work"
            other = root / "other"
            _git(root, "init", "-q", "--bare", "-b", "main", str(origin))
            _git(root, "clone", "-q", str(origin), str(work))
            for repo in (work,):
                _git(repo, "config", "user.name", "t")
                _git(repo, "config", "user.email", "t@example.com")
            (work / "docs").mkdir()
            (work / "docs" / "_sidebar.md").write_text("* Daily Papers\n", encoding="utf-8")
            (work / "config.yaml").write_text("subscriptions: {}\n", encoding="utf-8")
            _git(work, "add", "-A")
            _git(work, "commit", "-q", "-m", "base")
            _git(work, "push", "-q", "origin", "HEAD:main")
            _git(root, "clone", "-q", str(origin), str(other))
            _git(other, "config", "user.name", "o")
            _git(other, "config", "user.email", "o@example.com")

            # 日报本次产物
            (work / "docs" / "20260927").mkdir()
            (work / "docs" / "20260927" / "README.md").write_text("daily\n", encoding="utf-8")

            # 第一次 push 前让另一个 workflow 抢先推送（改另一个文件），制造 non-fast-forward。
            racer = (
                'racer_done=""\n'
                "git() {\n"
                '  if [ "$1" = push ] && [ -z "$racer_done" ]; then\n'
                "    racer_done=1\n"
                f'    (cd "{other}" && echo deep > docs/deep.md && command git add docs/deep.md'
                ' && command git commit -q -m "[chore] deep read" && command git push -q origin HEAD:main)\n'
                "  fi\n"
                '  command git "$@"\n'
                "}\n"
                "sleep() { :; }\n"
            )
            env = dict(
                os.environ,
                GITHUB_REPOSITORY_OWNER="test",
                GITHUB_REPOSITORY="test/example",
                GITHUB_REF_NAME="main",
                REQUESTED_DAYS="1",
            )
            result = subprocess.run(
                ["bash", "-e", "-c", racer + script],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("推送被拒", result.stdout)

            log = _git(origin, "log", "--format=%s", "main")
            self.assertIn("[chore] daily pipeline", log)
            self.assertIn("[chore] deep read", log)
            files = _git(origin, "ls-tree", "-r", "--name-only", "main")
            self.assertIn("docs/deep.md", files)
            self.assertIn("docs/20260927/README.md", files)


if __name__ == "__main__":
    unittest.main()


class DailyCheckoutLatestHeadTest(unittest.TestCase):
    def test_checkout_uses_branch_head_not_trigger_sha(self):
        # 排队的手动运行若检出触发时的旧提交，看不到前一次刚提交的 _daily_state.json，
        # 同一日期块会被整块覆盖（两个方向先后手动运行时出现过）。
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/daily-paper-reader.yml").read_text(encoding="utf-8")
        )
        checkout = next(
            s for s in workflow["jobs"]["run"]["steps"] if s.get("name") == "Checkout"
        )
        self.assertEqual(checkout["with"]["ref"], "${{ github.ref_name }}")
        self.assertEqual(checkout["with"]["fetch-depth"], 0)
