"""repo_quality（Repo 质量检查）模块的单元测试。"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from repo_snapshot_qa.checks.repo_quality import (
    check_commit_message_quality,
    check_readme_consistency,
    check_subsystems,
    detect_subsystems,
)
from repo_snapshot_qa.models import CommitInfo


def _commit(message: str) -> CommitInfo:
    return CommitInfo(
        sha="0" * 40,
        author_name="Test",
        author_email="test@example.com",
        date="2026-01-01T00:00:00+00:00",
        message=message,
    )


class RepoQualityTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.pkg = self.repo / "src" / "pkg"
        self.pkg.mkdir(parents=True)
        (self.pkg / "__init__.py").write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_subsystems_detection(self) -> None:
        (self.pkg / "a.py").write_text("x = 1\n", encoding="utf-8")
        (self.pkg / "b.py").write_text("x = 1\n", encoding="utf-8")
        sub = self.pkg / "sub"
        sub.mkdir()
        (sub / "__init__.py").write_text("", encoding="utf-8")
        self.assertEqual(detect_subsystems(self.repo), ["a", "b", "sub"])
        self.assertTrue(check_subsystems(self.repo).passed)

    def test_subsystems_too_few(self) -> None:
        (self.pkg / "a.py").write_text("x = 1\n", encoding="utf-8")
        self.assertFalse(check_subsystems(self.repo).passed)

    def test_subsystems_fallback_non_python(self) -> None:
        shutil.rmtree(self.repo / "src")
        (self.repo / "lib").mkdir()
        (self.repo / "lib" / "a.js").write_text("// x\n", encoding="utf-8")
        (self.repo / "index.js").write_text("// x\n", encoding="utf-8")
        subs = detect_subsystems(self.repo)
        self.assertIn("lib", subs)
        self.assertIn("index", subs)

    def test_readme_consistency_pass(self) -> None:
        (self.repo / "pyproject.toml").write_text(
            '[project]\nname = "mypkg"\n\n[project.scripts]\nmycmd = "pkg.cli:main"\n',
            encoding="utf-8",
        )
        (self.repo / "README.md").write_text("# mypkg\n\n运行命令 `mycmd`\n", encoding="utf-8")
        self.assertTrue(check_readme_consistency(self.repo).passed)

    def test_readme_consistency_missing_script(self) -> None:
        (self.repo / "pyproject.toml").write_text(
            '[project]\nname = "mypkg"\n\n[project.scripts]\nmycmd = "pkg.cli:main"\n',
            encoding="utf-8",
        )
        (self.repo / "README.md").write_text("# mypkg\n\n没有命令入口\n", encoding="utf-8")
        self.assertFalse(check_readme_consistency(self.repo).passed)

    def test_commit_message_quality(self) -> None:
        good = [_commit(m) for m in ("feat: add x", "fix(core): handle null", "docs: update", "test: cases")]
        self.assertTrue(check_commit_message_quality(good).passed)
        bad = [_commit("update stuff"), _commit("wip"), _commit("fix")]
        self.assertFalse(check_commit_message_quality(bad).passed)


if __name__ == "__main__":
    unittest.main()
