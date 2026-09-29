"""M1 仓库快照采集：克隆仓库并固定到指定 commit，生成快照清单。

设计目标：把「一次采集」固化为可复现的结果——无论后续仓库如何演进，
本次质检都基于同一个 commit 与 tree，保证结论可回溯。
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import SnapshotManifest


class SnapshotError(RuntimeError):
    """快照采集过程中的任何失败。"""


def run_git(args: list[str], cwd: Path | None = None) -> str:
    """执行 git 命令并返回去空白后的 stdout，失败时抛出 SnapshotError。"""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise SnapshotError(detail or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def clone_repo(repo_url: str, dest: Path, ref: str | None = None) -> Path:
    """把仓库克隆到 dest 目录，返回该目录路径。"""
    dest.mkdir(parents=True, exist_ok=True)
    cmd = ["clone"]
    if ref:
        cmd += ["--branch", ref]
    cmd += [repo_url, str(dest)]
    run_git(cmd)
    return dest


def current_commit(repo_path: Path) -> str:
    """返回仓库当前 HEAD 的完整 sha。"""
    return run_git(["rev-parse", "HEAD"], cwd=repo_path)


def freeze_commit(repo_path: Path, commit_sha: str) -> None:
    """把仓库检出一个到指定的 commit。"""
    run_git(["checkout", "--quiet", commit_sha], cwd=repo_path)


def capture_manifest(
    repo_url: str, repo_path: Path, commit_sha: str
) -> SnapshotManifest:
    """采集快照元信息（分支、tree、时间戳）。"""
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    tree_sha = run_git(["rev-parse", "HEAD^{tree}"], cwd=repo_path)
    return SnapshotManifest(
        repo_url=repo_url,
        commit_sha=commit_sha,
        branch=branch,
        tree_sha=tree_sha,
        captured_at=datetime.now(timezone.utc).isoformat(),
    )


def write_manifest(manifest: SnapshotManifest, out_path: Path) -> Path:
    """把快照清单序列化为 JSON 文件。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(manifest), indent=2, ensure_ascii=False) + "\n"
    out_path.write_text(payload, encoding="utf-8")
    return out_path


def capture_snapshot(
    repo_url: str,
    dest: Path,
    ref: str | None = None,
    commit_sha: str | None = None,
    manifest_path: Path | None = None,
) -> tuple[Path, SnapshotManifest]:
    """一站式快照采集：克隆 → 固定 commit → 写清单，返回 (仓库路径, 清单)。"""
    repo_path = clone_repo(repo_url, dest, ref=ref)
    if commit_sha:
        freeze_commit(repo_path, commit_sha)
    sha = current_commit(repo_path)
    manifest = capture_manifest(repo_url, repo_path, sha)
    out = manifest_path or (dest / "snapshot.json")
    write_manifest(manifest, out)
    return repo_path, manifest
