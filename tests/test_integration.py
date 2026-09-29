"""三阶段质检的端到端集成测试。"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repo_snapshot_qa.checks import overall_passed
from repo_snapshot_qa.checks.admission import run_admission_checks
from repo_snapshot_qa.checks.milestone_quality import run_milestone_quality_checks
from repo_snapshot_qa.checks.repo_quality import run_repo_quality_checks
from repo_snapshot_qa.config import Config
from repo_snapshot_qa.history import parse_commit_history
from repo_snapshot_qa.models import Milestone


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


class IntegrationTest(unittest.TestCase):
    def test_three_stage_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _git(repo, "init", "-b", "main")
            pkg = repo / "src" / "pkg"
            pkg.mkdir(parents=True)
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (repo / "README.md").write_text(
                "# pkg\n\n## 安装\n```\npip install .\n```\n\n## 使用\n```\ncmd\n```\n" + "x" * 300,
                encoding="utf-8",
            )
            (repo / "pyproject.toml").write_text(
                '[project]\nname = "pkg"\n\n[project.scripts]\ncmd = "pkg.cli:main"\n',
                encoding="utf-8",
            )
            # 按 a -> b -> c 的顺序分三次提交，构成三个连续开发片段。
            for mod in ("a", "b", "c"):
                (pkg / f"module_{mod}.py").write_text(
                    "\n".join(f"x{j} = {j}" for j in range(100)), encoding="utf-8"
                )
                _git(repo, "add", ".")
                _git(repo, "commit", "-m", f"feat({mod}): 实现模块 {mod}")

            commits = parse_commit_history(repo)
            self.assertEqual(len(commits), 3)

            config = Config()
            config.admission.min_commits = 2
            config.admission.min_loc = 50
            config.milestone_quality.min_commits_per = 1

            admission = run_admission_checks(repo, commits, config=config.admission)
            self.assertTrue(overall_passed(admission))

            repo_quality = run_repo_quality_checks(repo, commits, config=config.repo_quality)
            self.assertTrue(overall_passed(repo_quality))

            milestones = [
                Milestone("模块 c", "实现模块 c 的能力", commits[0].sha, commits[0].sha),
                Milestone("模块 b", "实现模块 b 的能力", commits[1].sha, commits[1].sha),
                Milestone("模块 a", "实现模块 a 的能力", commits[2].sha, commits[2].sha),
            ]
            milestone_quality = run_milestone_quality_checks(
                milestones, commits, config=config.milestone_quality
            )
            self.assertTrue(overall_passed(milestone_quality))


if __name__ == "__main__":
    unittest.main()
