"""仓库扫描与查找的共享辅助函数，供各检查模块复用。"""
from __future__ import annotations

from pathlib import Path

SKIP_DIRS = {
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "site-packages",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
}

README_CANDIDATES = ("README.md", "README.rst", "README.txt", "readme.md")


def iter_python_files(repo_path: Path):
    """遍历仓库下的 Python 源文件，跳过依赖与构建产物目录。"""
    for path in repo_path.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


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
    """定位源码包根目录（src 布局优先，其次仓库根目录）。"""
    for base in (repo_path / "src", repo_path):
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if child.is_dir() and (child / "__init__.py").exists():
                return child
    return None
