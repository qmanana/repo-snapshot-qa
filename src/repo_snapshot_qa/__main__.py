"""允许以 ``python -m repo_snapshot_qa`` 方式运行。"""
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
