"""cli（命令行入口）模块的单元测试。"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repo_snapshot_qa.cli import _load_milestones, main


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


class CliTest(unittest.TestCase):
    def test_version(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)

    def test_load_milestones(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "milestones.json"
            path.write_text(
                '[{"title": "t", "description": "d", "start_commit": "a", "end_commit": "b"}]',
                encoding="utf-8",
            )
            milestones = _load_milestones(str(path))
            self.assertEqual(len(milestones), 1)
            self.assertEqual(milestones[0].title, "t")

    def test_snapshot_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            _git(source, "init", "-b", "main")
            (source / "a.txt").write_text("hello\n", encoding="utf-8")
            _git(source, "add", "a.txt")
            _git(source, "commit", "-m", "feat: add a.txt")
            expected_sha = _git(source, "rev-parse", "HEAD")

            dest = base / "dest"
            code = main(["snapshot", str(source), "-d", str(dest)])
            self.assertEqual(code, 0)
            manifest = dest / "snapshot.json"
            self.assertTrue(manifest.exists())
            self.assertIn(expected_sha[:8], manifest.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
