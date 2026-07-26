---
name: 70cityprice
description: >
  中国国家统计局「70个大中城市商品住宅销售价格变动情况」长时间序列数据集的维护与分析入口。
  当需要更新月度房价数据、按城市/月份提取子集、生成走势图、构建网页数据，
  或回答任何涉及 70 城房价指数口径的问题时使用。
metadata:
  version: "1.0.0"
---

# 70城房价数据集

本仓库是一个围绕单一 CSV 的数据集包。本文件只负责建立数据心智模型和选择流程；每条流程自己拥有完整步骤。

## 加载顺序

1. 读本文件。
2. 从下表选中**恰好一条**流程，读它的流程文档。
3. 只在流程文档显式要求时才读对应的 `references/`。

| 意图 | 流程authority |
|---|---|
| 抓取并追加新月份数据 | [`workflows/monthly-update.md`](workflows/monthly-update.md) |
| 按城市/月份/组合条件取子集 | [`workflows/extract.md`](workflows/extract.md) |
| 重绘 README 走势图 | [`workflows/chart.md`](workflows/chart.md) |
| 构建/调试 GitHub Pages 数据 | [`workflows/site-build.md`](workflows/site-build.md) |

**纯数据问答**（"深圳最近同比怎么走"）不需要选流程，直接用 `workflows/extract.md` 里的只读命令查，但**必须**先读 [`references/fixedbase-caliber.md`](references/fixedbase-caliber.md) 再解释任何定基比数值。

---

## 数据心智模型

只有一个事实源：仓库根的 [`70cityprice.csv`](70cityprice.csv)，2006 年至今的月度数据，约 4.7 万行。不引入数据库，所有工具都是围绕这份 CSV 的读写。

四条必须先内化的约束：

1. **一个「日期 × 城市」= 3 行**，`FixedBase` ∈ {`同比`, `环比`, `定基比`}。`Below90 / 144 / Above144` 这类带后缀的列是同一行内的分户型细分，**不要**再展开成额外行。

2. **写回格式不可改**：`utf-8-sig` 编码 + `csv.QUOTE_ALL` 全字段加引号（`update_csv()` 里的 `to_csv(..., quoting=1, encoding='utf-8-sig')`）。改动它会造成大规模无意义 diff 或 BOM 错乱。排序键固定为 `(CITY, DATE, FixedBase)`，日期格式固定 `YYYY/M/D`（无前导零，恒为该月 1 日）。

3. **城市名必须走标准化链路**：任何外部输入（抓来的城市名、`--cities` 参数）都要经 `normalize_city_name` → `get_standard_city_name` 才能落库或比对。禁止直接字符串比较。细节见 [`references/city-naming.md`](references/city-naming.md)。

4. **定基比不是一条连续序列**。基期在 2010 / 2015 / 2020 之间轮换过，2023 年起停止公布。任何跨期拼接都是错的。在给出涉及该字段的结论前，必读 [`references/fixedbase-caliber.md`](references/fixedbase-caliber.md)。

## 全局执行纪律

- **命令一律用 `python3` / `pip3`**，不要在文档、docstring 或 print 里写裸 `python`。本机已在 `.venv/` 装好依赖，直接用系统解释器时命令写成 `.venv/bin/python3 scripts/...`。
- **改完数据必跑校验**。`scripts/validate_70cityprice.py` 是本仓库事实上的回归测试（没有测试套件、lint 和 CI 检查）。
- **`projects/` 是输出沙箱**，已被 `.gitignore` 忽略，脚本默认输出到这里。不要把生成的子集提交进仓库。
- **`scripts/` 是扁平脚本目录，不是 Python 包**。各脚本直接 `from common import ...`，依赖同目录运行。新加工具脚本时维持这种扁平结构，共用逻辑放进 `common.py`。
- **不要为本仓库引入通用工程脚手架**（`tests/`、分支流程、打包配置）。它是数据集包，不是应用。

## 参考资料索引

按需加载，不要预读：

| 文档 | 何时读 |
|---|---|
| [`references/schema.md`](references/schema.md) | 需要理解列含义、主键、排序、写回约定时 |
| [`references/city-naming.md`](references/city-naming.md) | 涉及城市名匹配、去重、新增城市时 |
| [`references/fixedbase-caliber.md`](references/fixedbase-caliber.md) | **任何**涉及定基比字段的分析或回答（强制） |
| [`references/stats-table-parsing.md`](references/stats-table-parsing.md) | 改动 `update_70cityprice.py` 的解析逻辑，或抓取失败排查时 |

面向人类读者的完整叙述（数据来源、官方附注、城市清单、引用格式）在 [`README.md`](README.md)，不要把它的内容复制到本包里。
