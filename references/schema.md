# CSV Schema 与写回约定

主数据文件：仓库根 [`70cityprice.csv`](../70cityprice.csv)。列常量的唯一定义在 [`scripts/common.py`](../scripts/common.py) 的 `REQUIRED_COLUMNS`，改列必须改那里。

## 列定义

| 列名 | 说明 | 示例 |
|---|---|---|
| `DATE` | 数据月份，恒为该月 1 日 | `2025/10/1` |
| `ADCODE` | 城市行政区划代码 | `110100` |
| `CITY` | 城市名（国家统计局当前写法，无「市」后缀） | `北京` |
| `FixedBase` | 指数类型 | `同比` / `环比` / `定基比` |
| `HouseIDX` | 住宅价格指数（早期数据，新月份为空） | |
| `ResidentIDX` | 住宅价格指数（早期数据，新月份为空） | |
| `CommodityHouseIDX` | 新建商品住宅指数 | `99.7` |
| `SecondHandIDX` | 二手住宅指数 | `99.0` |
| `ResidentBelow90IDX` | 住宅 90m² 以下（早期数据） | |
| `CommonResidentBelow90IDX` | 普通住宅 90m² 以下（早期数据） | |
| `CommodityBelow90IDX` | 新建商品住宅 90m² 以下 | `99.5` |
| `Commodity144IDX` | 新建商品住宅 90–144m² | `99.6` |
| `CommodityAbove144IDX` | 新建商品住宅 144m² 以上 | `99.9` |
| `SecondHandBelow90IDX` | 二手住宅 90m² 以下 | `98.8` |
| `SecondHand144IDX` | 二手住宅 90–144m² | `99.3` |
| `SecondHandAbove144IDX` | 二手住宅 144m² 以上 | `99.1` |

前四列是标识列，其余 12 列都是数值指数列（`NUMERIC_COLUMNS`）。早期数据列（`HouseIDX`、`ResidentIDX`、`ResidentBelow90IDX`、`CommonResidentBelow90IDX`）在近年数据中恒为空，这是历史口径差异而非缺失错误，不要试图回填。

## 行的展开规则

**2011 年起，一个「日期 × 城市」恰好展开为 3 行**，`FixedBase` 分别取 `同比`、`环比`、`定基比`。2006–2010 年官方还没有定基指数，只有 `同比`、`环比` 2 行，这是历史口径而非缺失。

带面积后缀的列（`Below90` / `144` / `Above144`）是**同一行内的分户型细分**，属于列维度。绝不要把它们再展开成额外的行——那会让主键失效并使记录数翻数倍。

`ALLOWED_FIXED_BASES = {同比, 环比, 定基比}`，其中 `REQUIRED_FIXED_BASES = {同比, 环比}` 是每月必须齐备的；`定基比` 行是否存在由月份决定：同一个月要么 70 城都有，要么都没有，校验脚本据此区分「合法缺失」与「抓取失败」。2023 年起官方停发定基指数，但该行仍然有值——存的是发布表里的「1-N月平均」（年内累计同比，1 月份等于当月同比），含义已与 2022 年及以前不同，见 [`fixedbase-caliber.md`](fixedbase-caliber.md)。

## 主键与排序

- **主键**：`(DATE, CITY, FixedBase)`
- **排序键**：`(CITY, DATE, FixedBase)`，在 `update_csv()` 末尾统一排序

同月份重复写入时，`update_csv()` 会**替换**旧记录而非追加，所以重跑更新脚本是幂等的。

## 写回格式（不可改）

```python
df.to_csv(csv_path, index=False, quoting=1, encoding='utf-8-sig')
```

- `encoding='utf-8-sig'` —— 带 BOM，保证 Excel 直接双击打开中文不乱码
- `quoting=1`（即 `csv.QUOTE_ALL`）—— 全字段加引号

这两项任何一项改动都会让整个近 5 万行的文件产生逐行 diff，把一次月度更新的 commit 从几十行变成全文件重写。修改写入逻辑时必须原样保留。

日期字符串格式固定 `YYYY/M/D`，**无前导零**（`2025/1/1` 而非 `2025/01/01`），日恒为 `1`。

数值写法去掉多余的 `.0`（`97`、`103.2`，不写 `97.0`）。`pd.read_html` 读出的是浮点数，写回前必须经 `common.py` 的 `format_index_value()`，否则会和历史数据写法不一致。

## 校验

```bash
python3 scripts/validate_70cityprice.py
```

检查结构（列齐备）、主键唯一性、月份连续性、70 城覆盖、ADCODE 与城市一致、数值区间与写法、排序与写回格式（文件必须能被 `update_csv()` 的写法逐字节复现）。数值区间 `INDEX_VALUE_RANGE` 定义在 `common.py`。本仓库没有测试套件，这个脚本就是唯一的回归测试，任何改动 CSV 的操作之后都必须跑；Pages 部署前 CI 也会跑它，不通过不上线。
