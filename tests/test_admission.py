"""admission（准入检查）模块的单元测试。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repo_snapshot_qa.checks import overall_passed
from repo_snapshot_qa.checks.admission import (
    check_code_scale,
    check_commit_count,
    check_parse_rate,
    check_readme,
    run_admission_checks,
)
from repo_snapshot_qa.models import CommitInfo


def _commit(i: int) -> CommitInfo:
    return CommitInfo(
        sha=f"{i:040x}",
        author_name="Test",
        author_email="test@example.com",
        date="2026-01-01T00:00:00+00:00",
        message=f"feat: commit {i}",
    )


class AdmissionTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        (self.repo / "src").mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_commit_count_threshold(self) -> None:
        self.assertTrue(check_commit_count([_commit(i) for i in range(10)]).passed)
        self.assertFalse(check_commit_count([_commit(i) for i in range(3)]).passed)

    def test_code_scale(self) -> None:
        self.assertFalse(check_code_scale(self.repo).passed)
        pkg = self.repo / "src" / "pkg"
        pkg.mkdir()
        for name in ("a.py", "b.py"):
            (pkg / name).write_text("\n".join(f"x = {i}" for i in range(120)) + "\n", encoding="utf-8")
        self.assertTrue(check_code_scale(self.repo).passed)

    def test_parse_rate(self) -> None:
        (self.repo / "good.py").write_text("x = 1\n", encoding="utf-8")
        (self.repo / "bad.py").write_text("def broken(:\n", encoding="utf-8")
        result = check_parse_rate(self.repo)
        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.5)
        self.assertTrue(any("bad.py" in d for d in result.details))

    def test_readme_missing(self) -> None:
        self.assertFalse(check_readme(self.repo).passed)

    def test_readme_complete(self) -> None:
        (self.repo / "README.md").write_text(
            "# 项目\n\n## 简介\n这是一个测试项目。\n\n## 安装\n```\npip install .\n```\n\n"
            "## 使用\n```\nrepo-snapshot-qa --help\n```\n\n" + "内容" * 120 + "\n",
            encoding="utf-8",
        )
        self.assertTrue(check_readme(self.repo).passed)

    def test_run_admission_checks(self) -> None:
        (self.repo / "README.md").write_text(
            "# T\n## 安装\npip install .\n## 使用\ncmd\n" + "x" * 300 + "\n", encoding="utf-8"
        )
        pkg = self.repo / "src" / "pkg"
        pkg.mkdir()
        (pkg / "a.py").write_text("\n".join(f"x = {i}" for i in range(250)) + "\n", encoding="utf-8")
        results = run_admission_checks(self.repo, [_commit(i) for i in range(10)])
        self.assertEqual(len(results), 4)
        self.assertTrue(overall_passed(results))


if __name__ == "__main__":
    unittest.main()
