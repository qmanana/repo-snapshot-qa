# repo-snapshot-qa

采集 Git 仓库固定快照，并对仓库与 Milestone 执行自动质检的命令行工具。

## 简介

`repo-snapshot-qa` 把「一次仓库采集」固化为可复现的质检流程：先克隆仓库并固定到指定 commit 生成快照，再依次执行准入检查、Repo 质量检查、仓库健康度和 Milestone 质量检查四个阶段，最后输出可读的文本、JSON 或 HTML 报告。工具仅依赖 Python 标准库，支持 Python / JavaScript / TypeScript / Go / Rust / Java 等多种语言的仓库，适合在离线或最小环境中运行。

## 功能特性

- **快照采集**：克隆仓库、固定 commit，支持 `--depth` 浅克隆，生成 `snapshot.json` 清单
- **提交历史解析**：把 `git log` 解析为结构化的提交数据（作者、时间、改动量、改动文件路径）
- **多语言支持**：按扩展名识别代码文件；可解析率对 Python/JSON/TOML 做真实解析、对 C 系语言做括号配平烟测，其余语言如实标注为未支持
- **准入检查**：提交数量、代码规模、可解析率、README 基础完整性
- **Repo 质量检查**：功能子系统、README 与代码一致性、提交说明质量
- **仓库健康度**：测试覆盖比、遗留标记（TODO/FIXME）、贡献者分布/bus factor、改动热点、超大文件
- **Milestone 质量检查**：聚合性、需求可验证性、代码覆盖、拆分粒度
- **阈值配置**：通过 JSON 配置文件覆盖各阶段默认阈值
- **报告输出**：文本 / JSON / HTML 三种格式的汇总报告（含总分与通过率）
- **自动测试**：内置 GitHub Actions CI 工作流

## 安装

要求 Python >= 3.11，无第三方依赖：

```bash
pip install .
```

安装后即可使用 `repo-snapshot-qa` 命令；也可以不安装，直接以模块方式运行：

```bash
PYTHONPATH=src python -m repo_snapshot_qa --help
```

## 使用方法

### 采集快照

```bash
repo-snapshot-qa snapshot <仓库地址> -d ./snapshot -r main
# 浅克隆，仅拉取最近 50 条历史
repo-snapshot-qa snapshot <仓库地址> -d ./snapshot --depth 50
# 固定到指定 commit
repo-snapshot-qa snapshot <仓库地址> -d ./snapshot -c <commit-sha>
```

### 执行质检

```bash
repo-snapshot-qa check ./snapshot
# 某一阶段未通过时仍继续执行后续检查
repo-snapshot-qa check . --no-fail-fast
# 仅扫描 / 跳过某些文件（逗号分隔的 glob 模式）
repo-snapshot-qa check . --include "*.py,*.go" --exclude "tests/*"
# 输出 JSON/HTML 到 stdout 或文件
repo-snapshot-qa check . --format json
repo-snapshot-qa check . --json report.json --html report.html
# 带里程碑定义与阈值配置
repo-snapshot-qa check . --milestones milestones.json --config config.json
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

阈值配置 JSON 格式：

```json
{
  "admission": {"min_commits": 20},
  "milestone_quality": {"cohesion_ratio": 0.6},
  "health": {"min_test_ratio": 0.1, "max_file_loc": 800}
}
```

## 质检维度

| 阶段 | 检查项 |
|------|--------|
| 准入检查 | 提交数量、代码规模、可解析率、README 完整性 |
| Repo 质量检查 | 功能子系统、README 一致性、提交说明质量 |
| 仓库健康度 | 测试覆盖比、遗留标记、贡献者分布/bus factor、改动热点、超大文件 |
| Milestone 质量检查 | 聚合性、需求可验证性、代码覆盖、拆分粒度 |

## 项目结构

```
src/repo_snapshot_qa/
├── __main__.py             # python -m 入口
├── cli.py                  # 命令行入口
├── config.py               # 阈值配置
├── languages.py            # 语言注册表与语法校验
├── snapshot.py             # 快照采集
├── history.py              # 提交历史解析
├── models.py               # 数据模型
├── util.py                 # 共享辅助函数
├── report.py               # 报告输出（文本/JSON/HTML）
└── checks/
    ├── admission.py           # 准入检查
    ├── repo_quality.py        # Repo 质量检查
    ├── health.py              # 仓库健康度
    └── milestone_quality.py   # Milestone 质量检查
```

## 里程碑划分

按业务开发顺序，项目划分为 6 个里程碑（见 `examples/milestones.json`）：

1. **仓库快照采集**：克隆仓库并固定 commit，生成快照清单
2. **提交历史解析**：解析 git log 为结构化提交数据
3. **准入检查**：提交数量 / 代码规模 / 可解析率 / README
4. **Repo 质量检查**：功能子系统 / README 一致性 / 提交说明质量
5. **Milestone 质量检查**：聚合性 / 可验证性 / 覆盖 / 拆分粒度
6. **报告输出、CLI 编排与交付**：串联质检阶段，提供配置化、HTML 报告与 CI

## 后续工作

- 非 Python 语言的可解析率目前是启发式括号配平，可接入 tree-sitter 等真实解析器以获得更准确的语法校验
- 支持从远程仓库直接读取并自动按 commit 分段划分 Milestone，目前需手动提供 `milestones.json`
- 补充测试覆盖率统计（coverage）并集成到报告中
- 增加并发克隆以加速批量仓库采集
- 支持从 GitLab 等其它平台采集仓库
- 增加里程碑与提交依赖关系的图形化可视化

## 测试

```bash
PYTHONPATH=src python -m unittest discover -s tests -t .
```
