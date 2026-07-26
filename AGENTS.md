# AGENTS.md

本文件是 70cityprice 仓库面向 AI 助手的入口。

**处理任何数据更新、提取、绘图、网页构建，或回答任何涉及 70 城房价指数的问题之前，你必须先读 [`SKILL.md`](SKILL.md)。** 它拥有数据心智模型和全局执行纪律，并指向具体流程。本文件之后的内容只说明各类材料放在哪里。

## 项目概述

本仓库维护中国国家统计局发布的「70个大中城市商品住宅销售价格变动情况」长时间序列数据集。核心产物是单一的 [`70cityprice.csv`](70cityprice.csv)（2006 年至今的月度数据），其余 Python 脚本只是围绕这份 CSV 的更新、提取、校验与可视化工具。所有读写都基于 CSV，不引入数据库。

## 材料分布

| 位置 | 内容 |
|---|---|
| [`SKILL.md`](SKILL.md) | AI 入口：数据心智模型、执行纪律、流程索引 |
| [`workflows/`](workflows/) | 可执行流程，每条流程拥有自己的完整步骤 |
| [`references/`](references/) | 领域知识，按流程文档的显式要求加载，不要预读 |
| [`scripts/`](scripts/) | 扁平脚本目录（非 Python 包），共用逻辑在 `common.py` |
| [`README.md`](README.md) | 面向人类读者的完整叙述：数据来源、官方附注、城市清单、引用格式 |
| [`site/`](site/) | GitHub Pages 静态浏览器，是 CSV 的一个视图，不维护第二份数据 |

## 流程入口

| 意图 | 流程 |
|---|---|
| 抓取并追加新月份数据 | [`workflows/monthly-update.md`](workflows/monthly-update.md) |
| 按城市/月份取子集、查数据 | [`workflows/extract.md`](workflows/extract.md) |
| 重绘 README 走势图 | [`workflows/chart.md`](workflows/chart.md) |
| 构建/调试网页数据 | [`workflows/site-build.md`](workflows/site-build.md) |

## 硬性约定

- **命令一律 `python3` / `pip3`**，不要在文档、docstring 或 print 信息里写裸 `python`。Windows 用户自备 `python3` 别名。
- **本机（Ubuntu 24.04）已在 `.venv/` 装好依赖**，未做系统软链接。直接用系统解释器时命令写成 `.venv/bin/python3 scripts/...`。
- **改完 CSV 必跑 `python3 scripts/validate_70cityprice.py`。** 仓库没有测试套件、lint 配置和 CI 检查，这个脚本是事实上的质量回归测试。
- **涉及 `定基比` 字段的任何回答，先读 [`references/fixedbase-caliber.md`](references/fixedbase-caliber.md)。** 该字段基期轮换过三次、2023 年起停发，跨期拼接是本数据集最容易出的实质性错误。
- **不要为本仓库引入通用工程脚手架**（`tests/`、分支流程、打包配置）。它是数据集包，不是应用。
- **`projects/` 是输出沙箱**，已被 `.gitignore` 忽略，脚本默认输出到这里。

## 文档职责边界

避免同一份知识出现多个副本：

- `README.md` 面向人类，拥有**完整叙述**（背景、口径演变长文、城市列表、免责声明）
- `references/` 面向 AI，只放**可执行的约束**，需要背景时链接回 README 对应章节
- `workflows/` 只放**步骤和命令**，领域知识一律链接到 `references/`

新增说明时先判断它属于哪一层，不要三处都写一遍。
