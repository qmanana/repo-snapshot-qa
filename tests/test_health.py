"""health（仓库健康度）模块的单元测试。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repo_snapshot_qa.checks.health import (
    check_bus_factor,
    check_churn_hotspots,
    check_large_files,
    check_test_ratio,
    check_todo_density,
    run_health_checks,
)
from repo_snapshot_qa.models import CommitInfo


def _commit(author: str = "A", files: list[str] | None = None) -> CommitInfo:
    return CommitInfo(
        sha="0" * 40,
        author_name=author,
        author_email=f"{author}@example.com",
        date="2026-01-01T00:00:00+00:00",
        message="feat: x",
        files=files or [],
    )


class HealthTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_test_ratio(self) -> None:
        (self.repo / "src").mkdir()
        (self.repo / "tests").mkdir()
        (self.repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
        (self.repo / "src" / "b.py").write_text("x = 1\n", encoding="utf-8")
        (self.repo / "tests" / "test_a.py").write_text("x = 1\n", encoding="utf-8")
        self.assertTrue(check_test_ratio(self.repo).passed)
        (self.repo / "tests" / "test_a.py").unlink()
        self.assertFalse(check_test_ratio(self.repo).passed)

    def test_todo_density(self) -> None:
        (self.repo / "a.py").write_text("x = 1\n# TODO: do more\n", encoding="utf-8")
        self.assertTrue(check_todo_density(self.repo).passed)
        (self.repo / "a.py").write_text("".join("# TODO\n" for _ in range(11)), encoding="utf-8")
        self.assertFalse(check_todo_density(self.repo).passed)

    def test_todo_only_in_comments(self) -> None:
        # 字符串字面量与普通代码行里的标记不应计入，只有注释里的才算。
        (self.repo / "a.py").write_text(
            's = "TODO not a comment"\n# TODO: real comment\n',
            encoding="utf-8",
        )
        result = check_todo_density(self.repo)
        self.assertTrue(result.passed)
        self.assertIn("共 1 处", result.details[0])

    def test_bus_factor(self) -> None:
        # 单作者 -> 不通过
        solo = [_commit("A") for _ in range(5)]
        self.assertFalse(check_bus_factor(solo).passed)
        # 两位作者但一人占绝对多数 -> bus factor 1，不通过
        dominant = [_commit("A"), _commit("A"), _commit("A"), _commit("B")]
        self.assertFalse(check_bus_factor(dominant).passed)
        # 三位作者、任一人都不占 50% -> bus factor 2，通过
        balanced = [_commit("A"), _commit("A"), _commit("B"), _commit("B"), _commit("C")]
        self.assertTrue(check_bus_factor(balanced).passed)
        self.assertFalse(check_bus_factor([]).passed)

    def test_churn_hotspots(self) -> None:
        commits = [_commit(files=["a.py", "b.py"]), _commit(files=["a.py"])]
        result = check_churn_hotspots(commits, top_n=2)
        self.assertTrue(result.passed)
        self.assertIn("a.py", result.details[0])

    def test_large_files(self) -> None:
        (self.repo / "big.py").write_text(
            "\n".join(f"x = {i}" for i in range(100)) + "\n", encoding="utf-8"
        )
        self.assertTrue(check_large_files(self.repo, max_file_loc=200).passed)
        self.assertFalse(check_large_files(self.repo, max_file_loc=50).passed)

    def test_run_health_checks(self) -> None:
        commits = [_commit("A"), _commit("B")]
        results = run_health_checks(self.repo, commits)
        self.assertEqual(len(results), 5)


if __name__ == "__main__":
    unittest.main()
