"""cli（命令行入口）模块的单元测试。"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
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

    def test_check_non_git_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = main(["check", tmp])
            self.assertEqual(code, 1)

    def test_check_format_json_no_fail_fast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            repo.mkdir()
            _git(repo, "init", "-b", "main")
            (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
            _git(repo, "add", "a.py")
            _git(repo, "commit", "-m", "feat: add a.py")

            buf = StringIO()
            with redirect_stdout(buf):
                code = main(["check", str(repo), "--no-fail-fast", "--format", "json"])
            data = json.loads(buf.getvalue())
            self.assertIn("admission", data)
            self.assertIn("health", data)
            self.assertIn("summary", data)
            self.assertEqual(code, 1)  # 单提交仓库不满足准入


if __name__ == "__main__":
    unittest.main()
