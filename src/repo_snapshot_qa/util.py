"""仓库扫描与查找的共享辅助函数，供各检查模块复用。"""
from __future__ import annotations

import fnmatch
from pathlib import Path

from .languages import is_code_file

SKIP_DIRS = {
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    "node_modules",
    "bower_components",
    "dist",
    "build",
    "target",
    "site-packages",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".gradle",
    ".idea",
    "vendor",
}

README_CANDIDATES = ("README.md", "README.rst", "README.txt", "readme.md")


def iter_code_files(
    repo_path: Path,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
):
    """遍历仓库下的代码文件（多语言），跳过依赖/构建产物目录。

    include/exclude 均为 glob 模式列表，作用于相对仓库根的 posix 路径；
    两者可组合使用（先 include 收窄，再 exclude 剔除）。
    """
    for path in sorted(repo_path.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not is_code_file(path):
            continue
        rel = path.relative_to(repo_path).as_posix()
        if include and not any(fnmatch.fnmatch(rel, pat) for pat in include):
            continue
        if exclude and any(fnmatch.fnmatch(rel, pat) for pat in exclude):
            continue
        yield path


def is_test_file(path: Path) -> bool:
    """判断文件是否为测试文件：位于测试目录，或文件名符合测试命名约定。"""
    parts = [p.lower() for p in path.parts]
    if any(seg in ("test", "tests", "__tests__", "spec", "specs", "testdata") for seg in parts):
        return True
    stem = path.stem
    return (
        stem.startswith("test_")
        or stem.endswith("_test")
        or stem.endswith(".test")
        or stem.endswith(".spec")
    )


def count_non_blank_lines(path: Path) -> int:
    """统计文件的有效代码行数（忽略空白行）。"""
    total = 0
    with path.open(encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.strip():
                total += 1
    return total


def find_readme(repo_path: Path) -> Path | None:
    """返回仓库根目录下的 README 文件路径，不存在则返回 None。"""
    for name in README_CANDIDATES:
        candidate = repo_path / name
        if candidate.exists():
            return candidate
    return None


def find_package_root(repo_path: Path) -> Path | None:
    """定位 Python 源码包根目录（src 布局优先，其次仓库根目录）。"""
    for base in (repo_path / "src", repo_path):
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if child.is_dir() and (child / "__init__.py").exists():
                return child
    return None
