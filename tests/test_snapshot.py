"""snapshot 模块的单元测试。"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from repo_snapshot_qa.models import SnapshotManifest
from repo_snapshot_qa.snapshot import (
    capture_snapshot,
    clone_repo,
    current_commit,
    freeze_commit,
    write_manifest,
)


def _git(repo: Path, *args: str) -> str:
    """在 fixture 仓库里执行 git，并带上测试身份。"""
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def _make_source_repo(base: Path) -> tuple[Path, str, str]:
    """创建一个带两条提交的本地源仓库，返回 (路径, 第一条 sha, 第二条 sha)。"""
    repo = base / "source"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "a.txt").write_text("v1\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "first commit")
    first = _git(repo, "rev-parse", "HEAD")
    (repo / "a.txt").write_text("v2\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "second commit")
    second = _git(repo, "rev-parse", "HEAD")
    return repo, first, second


class SnapshotTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.source, self.first, self.second = _make_source_repo(self.base)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_clone_and_manifest(self) -> None:
        dest = self.base / "clone"
        repo, manifest = capture_snapshot(str(self.source), dest)

        self.assertTrue((dest / "a.txt").exists())
        self.assertEqual(manifest.commit_sha, self.second)
        self.assertEqual(manifest.branch, "main")
        self.assertEqual(current_commit(repo), self.second)

    def test_freeze_to_earlier_commit(self) -> None:
        dest = self.base / "clone"
        repo, manifest = capture_snapshot(str(self.source), dest, commit_sha=self.first)

        self.assertEqual(manifest.commit_sha, self.first)
        self.assertEqual(current_commit(repo), self.first)
        # 冻结到第一条提交后，a.txt 应是 v1 内容。
        self.assertEqual((dest / "a.txt").read_text(encoding="utf-8"), "v1\n")

    def test_manifest_roundtrip(self) -> None:
        manifest = SnapshotManifest(
            repo_url="https://example.com/x.git",
            commit_sha="abc123",
            branch="main",
            tree_sha="tree123",
            captured_at="2026-01-01T00:00:00+00:00",
        )
        out = self.base / "manifest.json"
        write_manifest(manifest, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["commit_sha"], "abc123")
        self.assertEqual(data["tree_sha"], "tree123")


if __name__ == "__main__":
    unittest.main()
