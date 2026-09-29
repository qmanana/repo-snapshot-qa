"""history 模块的单元测试。"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repo_snapshot_qa.history import parse_commit_history


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


class HistoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-b", "main")
        # 第一条提交：3 行文件
        (self.repo / "a.txt").write_text("1\n2\n3\n", encoding="utf-8")
        _git(self.repo, "add", "a.txt")
        _git(self.repo, "commit", "-m", "feat: add a.txt")
        # 第二条提交：改动 2 个文件，a.txt 增加 1 行、b.txt 新增 2 行，共 +3/-0
        (self.repo / "a.txt").write_text("1\n2\n3\n4\n", encoding="utf-8")
        (self.repo / "b.txt").write_text("x\ny\n", encoding="utf-8")
        _git(self.repo, "add", ".")
        _git(self.repo, "commit", "-m", "feat: extend a.txt and add b.txt")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_parse_order_and_fields(self) -> None:
        commits = parse_commit_history(self.repo)
        self.assertEqual(len(commits), 2)
        # 倒序：最新的在最前。
        self.assertEqual(commits[0].message, "feat: extend a.txt and add b.txt")
        self.assertEqual(commits[1].message, "feat: add a.txt")
        for c in commits:
            self.assertEqual(c.author_name, "Test")
            self.assertTrue(c.sha and c.date)

    def test_parse_change_stats(self) -> None:
        commits = parse_commit_history(self.repo)
        latest = commits[0]
        self.assertEqual(latest.files_changed, 2)
        self.assertEqual(latest.insertions, 3)
        self.assertEqual(latest.deletions, 0)
        self.assertEqual(commits[1].files_changed, 1)
        self.assertEqual(commits[1].insertions, 3)

    def test_max_commits(self) -> None:
        commits = parse_commit_history(self.repo, max_commits=1)
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0].message, "feat: extend a.txt and add b.txt")


if __name__ == "__main__":
    unittest.main()
