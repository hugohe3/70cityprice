# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

本仓库维护中国国家统计局发布的「70个大中城市商品住宅销售价格变动情况」长时间序列数据集。核心产物是单一的 [70cityprice.csv](70cityprice.csv)（2006 年至今的月度数据），其余 Python 脚本只是围绕这份 CSV 的更新、提取、校验与可视化工具。所有读写都基于 CSV，不引入数据库。

## 常用命令

统一使用 `python3` / `pip3`（Linux/macOS 主流默认提供；Windows 用户若仅有 `python.exe` 可自行替换为 `python`）。依赖见 [requirements.txt](requirements.txt)：`pandas`、`matplotlib`、`lxml`。

```bash
# 安装依赖（Ubuntu 24+ 若拒绝可加 --break-system-packages，或用 venv）
pip3 install -r requirements.txt

# 抓取并追加最新月份数据（URL 取自国家统计局发布页）
python3 tools/update_70cityprice.py "<国家统计局发布页URL>"

# 校验主 CSV 的结构、主键、月份连续性与 70 城覆盖（每次 update 后必跑）
python3 tools/validate_70cityprice.py

# 按月份 / 城市 / 组合条件提取子集，默认输出到 projects/
python3 tools/extract_70cityprice.py month 202401 202412
python3 tools/extract_70cityprice.py city 北京 上海 广州 深圳
python3 tools/extract_70cityprice.py filter --cities 成都 重庆 --start 202401 --end 202412 --fixedbase 同比,环比

# 重绘 assets/price_trend.png 走势图
python3 tools/generate_chart.py
```

仓库没有测试套件、lint 配置或 CI；`validate_70cityprice.py` 就是事实上的"质量回归测试"。`projects/` 目录被 `.gitignore` 忽略，是脚本默认的输出沙箱。

> 本机（Ubuntu 24.04）当前已通过 `.venv/` 装好依赖，未做系统软链接；如直接用系统解释器，相应命令请写成 `.venv/bin/python3 tools/...`。

## 完成一次月度更新后必须做的事

1. 运行 `update_70cityprice.py` 抓取新月份。脚本会原地修改 [70cityprice.csv](70cityprice.csv)（同月份已存在会被替换）。
2. 运行 `validate_70cityprice.py`，确保没有结构/覆盖回归。
3. 修改 [README.md](README.md) 顶部的「数据更新至-YYYY年M月」徽章以及目录结构说明中"当前更新至"那一行，使其与新数据对齐。
4. 如需展示，重跑 `generate_chart.py` 更新 [assets/price_trend.png](assets/price_trend.png)。
5. 历史 commit 信息显示，月度更新的提交规范是 `chore(数据): 更新70城房价数据至YYYY年M月...`，遵循此格式。

## 架构要点

### 单一 CSV 作为事实源（schema 见 README.md「数据结构」）

[70cityprice.csv](70cityprice.csv) 用 `utf-8-sig` 编码、`csv.QUOTE_ALL` 全字段加引号写入——`update_70cityprice.update_csv()` 中的 `to_csv(..., quoting=1, encoding='utf-8-sig')` 必须保持，否则会造成大规模 diff 或 BOM/编码错乱。

排序键是 `(CITY, DATE, FixedBase)`（在 `update_csv()` 末尾排序）。日期字符串格式固定为 `YYYY/M/D`（无前导零），月份恒为该月 1 日。

每个「日期 × 城市」会展开为 3 行：`FixedBase` ∈ {`同比`, `环比`, `定基比`}。`Below90 / 144 / Above144` 这类带后缀的列是同一行内的分户型细分，**不要**再展开成额外行。

### 国家统计局表格的解析约定（[tools/update_70cityprice.py](tools/update_70cityprice.py)）

发布页一般含 6 张表（新建商品住宅主表、二手住宅主表，再加各自的分面积表 (一)(二)），脚本按固定下标 `tables[0..5]` 处理。

两类历史口径差异已经在 `parse_main_index_table` / `parse_size_index_table` 中通过列数嗅探处理，新月份解析改动时请保留：
- **1 月份**没有「年度平均」列，脚本将「同比」复制到「定基比」字段。
- **2023 年起**官方不再发布定基指数，但旧数据保留定基行，因此 schema 仍含该列；新增逻辑不要假设定基比对 2023+ 月份必有值。

URL 中的日期编码（如 `t20260518` 或路径中的 `202605`）代表**发布月份**，数据月份是发布月减 1，这一减法在 `main()` 中完成，跨年时回退到上一年 12 月。

### 城市命名口径

`CITY_ADCODE` 是权威城市清单（70 个，规范名无「市」后缀）。所有外部输入（抓取下来的城市名、提取脚本里的 `--cities` 参数）都要先经 `normalize_city_name` → `get_standard_city_name` 才能落库或比对，否则会出现"北京/北京市"或"大理白族自治州/大理"这种重复键。涉及城市名的新代码请走相同路径，不要直接字符串比较。

[tools/validate_70cityprice.py](tools/validate_70cityprice.py) 直接 `from update_70cityprice import CITY_ADCODE, standardize_city_column`，所以 `tools/` 不是包，而是一个被加入到 `sys.path` 的扁平脚本目录——校验脚本依赖与更新脚本同目录运行。新加工具脚本时维持这种扁平结构。

### 定基指数的口径演变（务必先读 README）

「定基比」字段的基期在 2010 / 2015 / 2020 之间轮换过，2023 年起停止公布。跨期分析必须分段，禁止把不同基期的定基比直接拼成一条序列。README.md 中「定基指数的口径演变说明」一节是任何涉及该字段的建议与回答的必读上下文。

## 数据来源

国家统计局月度发布页：`https://www.stats.gov.cn/sj/zxfbhjd/` 下属各月份目录。通常每月 15–17 日发布上一月数据。
