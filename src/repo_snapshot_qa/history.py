"""M2 提交历史解析：把 git log 输出解析为结构化的 CommitInfo 列表。

实现上只依赖 git CLI，用带标记的 --format 配合 --numstat 一次性拿到
每条提交的作者、时间、说明与改动量，避免逐条调用 git show。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .models import CommitInfo

_HEADER_PREFIX = "COMMIT"
_FIELD_COUNT = 6  # COMMIT + sha + author_name + author_email + date + subject


def _run_git_log(repo_path: Path, max_commits: int | None) -> str:
    fmt = f"{_HEADER_PREFIX}%x09%H%x09%an%x09%ae%x09%aI%x09%s"
    cmd = ["git", "-C", str(repo_path), "log", "--numstat", f"--format={fmt}"]
    if max_commits:
        cmd += ["-n", str(max_commits)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git log failed")
    return result.stdout


def parse_commit_history(
    repo_path: Path, max_commits: int | None = None
) -> list[CommitInfo]:
    """解析仓库提交历史，返回按时间倒序排列的 CommitInfo 列表。

    numstat 行形如 ``插入数\\t删除数\\t路径``；二进制文件显示为 ``-``，
    这类行不参与改动量统计但文件数仍会累计不到（即被跳过），符合预期。
    """
    raw = _run_git_log(repo_path, max_commits)
    commits: list[CommitInfo] = []
    current: dict | None = None

    for line in raw.splitlines():
        if line.startswith(_HEADER_PREFIX + "\t"):
            fields = line.split("\t", maxsplit=_FIELD_COUNT - 1)
            if len(fields) != _FIELD_COUNT:
                current = None
                continue
            current = {
                "sha": fields[1],
                "author_name": fields[2],
                "author_email": fields[3],
                "date": fields[4],
                "message": fields[5],
                "files_changed": 0,
                "insertions": 0,
                "deletions": 0,
                "files": [],
            }
            commits.append(current)
        elif line and current is not None:
            parts = line.split("\t")
            if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
                current["files_changed"] += 1
                current["insertions"] += int(parts[0])
                current["deletions"] += int(parts[1])
                current["files"].append(parts[2])

    return [CommitInfo(**c) for c in commits]
