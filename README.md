# repo-snapshot-qa

采集 GitHub 仓库固定快照，并对仓库与 Milestone 执行自动质检的命令行工具。

## 简介

`repo-snapshot-qa` 把「一次仓库采集」固化为可复现的质检流程：先克隆仓库并固定到指定 commit 生成快照，再依次执行准入检查、Repo 质量检查和 Milestone 质量检查，最后输出可读的文本或 JSON 报告。工具仅依赖 Python 标准库，适合在离线或最小环境中运行。

## 功能特性

- **快照采集**：克隆仓库、固定 commit，生成 `snapshot.json` 清单
- **提交历史解析**：把 `git log` 解析为结构化的提交数据（作者、时间、改动量）
- **准入检查**：提交数量、代码规模、可解析率、README 基础完整性
- **Repo 质量检查**：功能子系统、README 与代码一致性、提交说明质量
- **Milestone 质量检查**：聚合性、需求可验证性、代码覆盖、拆分粒度
- **报告输出**：文本 / JSON 两种格式的汇总报告

## 安装

要求 Python >= 3.9，无第三方依赖：

```bash
pip install .
```

安装后即可使用 `repo-snapshot-qa` 命令；也可以不安装，直接以模块方式运行：

```bash
PYTHONPATH=src python -m repo_snapshot_qa.cli --help
```

## 使用方法

### 采集快照

```bash
repo-snapshot-qa snapshot <仓库地址> -d ./snapshot -r main
# 或固定到指定 commit
repo-snapshot-qa snapshot <仓库地址> -d ./snapshot -c <commit-sha>
```

### 执行质检

```bash
repo-snapshot-qa check ./snapshot
# 带里程碑定义与 JSON 报告
repo-snapshot-qa check ./snapshot --milestones milestones.json --json report.json
```

里程碑 JSON 格式：

```json
[
  {
    "title": "仓库快照采集",
    "description": "实现仓库克隆与固定 commit",
    "start_commit": "abc123",
    "end_commit": "def456"
  }
]
```

## 质检维度

| 阶段 | 检查项 |
|------|--------|
| 准入检查 | 提交数量、代码规模、可解析率、README 完整性 |
| Repo 质量检查 | 功能子系统、README 一致性、提交说明质量 |
| Milestone 质量检查 | 聚合性、需求可验证性、代码覆盖、拆分粒度 |

## 项目结构

```
src/repo_snapshot_qa/
├── cli.py                 # 命令行入口
├── snapshot.py            # 快照采集
├── history.py             # 提交历史解析
├── models.py              # 数据模型
├── util.py                # 共享辅助函数
├── report.py              # 报告输出
└── checks/
    ├── admission.py           # 准入检查
    ├── repo_quality.py        # Repo 质量检查
    └── milestone_quality.py   # Milestone 质量检查
```

## 里程碑划分

按业务开发顺序，项目划分为 5 个里程碑：

1. **仓库快照采集**：克隆仓库并固定 commit，生成快照清单
2. **提交历史解析**：解析 git log 为结构化提交数据
3. **准入检查**：提交数量 / 代码规模 / 可解析率 / README
4. **Repo 质量检查**：功能子系统 / README 一致性 / 提交说明质量
5. **Milestone 质量检查与报告**：聚合性 / 可验证性 / 覆盖 / 粒度 + 报告输出

## 后续工作

- 支持更多语言的解析率检查（Java / Go / TypeScript），当前仅支持 Python
- 支持从远程仓库直接读取里程碑并按 commit 自动分段
- 增加文件级改动追踪，用真实文件归属替代 scope 启发式
- 补充覆盖率统计与 HTML 报告
- 增加并发克隆与浅克隆参数以加速大仓库采集

## 测试

```bash
PYTHONPATH=src python -m unittest discover -s tests -t .
```
