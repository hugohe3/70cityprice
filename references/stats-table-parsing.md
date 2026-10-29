# 国家统计局发布页的表格解析约定

改动 [`scripts/update_70cityprice.py`](../scripts/update_70cityprice.py) 的解析逻辑，或排查抓取失败时读本文件。

## 发布页结构

来源：`https://www.stats.gov.cn/sj/zxfbhjd/` 下属各月份目录，通常每月 15–17 日发布上一月数据。

一个发布页含 **6 张表**。当前页面 `pd.read_html` 实际读出 12 张——后 6 张与前 6 张完全相同（页面内嵌了两份），脚本只用前 6 张，按固定下标处理（`process_tables()`）：

| 下标 | 内容 | 解析函数 |
|---|---|---|
| `tables[0]` | 新建商品住宅主表 | `parse_main_index_table` |
| `tables[1]` | 二手住宅主表 | `parse_main_index_table` |
| `tables[2]` | 新建商品住宅分面积表（一） | `parse_size_index_table` |
| `tables[3]` | 新建商品住宅分面积表（二） | `parse_size_index_table` |
| `tables[4]` | 二手住宅分面积表（一） | `parse_size_index_table` |
| `tables[5]` | 二手住宅分面积表（二） | `parse_size_index_table` |

主表是**左右双栏**布局（一页塞 70 个城市），`parse_main_index_table` 会同时解析左半和右半。分面积表拆成 (一)(二) 两张，各覆盖一部分城市，合并后才是完整 70 城。

## 数据月份 = 发布月份 − 1

URL 里的日期编码（`t20260518` 或路径中的 `202605`）是**发布月份**，数据月份要减 1。这个减法在 `main()` 里做，跨年时回退到上一年 12 月：

```python
data_month = month - 1
data_year = year
if data_month == 0:
    data_month = 12
    data_year -= 1
```

`parse_date_from_url()` 拿不到日期时会退回 `parse_date_from_title()` 从表格首行里找「YYYY年M月」。**标题里写的就是数据月份，不再减 1**——两条路径的换算统一在 `resolve_data_month()` 里。注意当前发布页的标题不在 `<table>` 内，这条退路实际上找不到日期；两者都失败就中止，不要瞎猜月份。

## 两类历史口径差异（改代码时必须保留）

### 1. 1 月份数据没有「年度平均」列

其他月份的主表每侧是 4 列：`城市 | 环比 | 同比 | 年度平均`（左右双栏共 8 列）。
1 月份只有 3 列：`城市 | 环比 | 同比` —— 因为 1 月是当年第一个月，累计平均就等于当月。

判断「有没有年度平均列」时，列数嗅探与月份一起用，命中「无年度平均」时把**同比值复制进定基比**字段：

- 主表（`parse_main_index_table`）：总列数 > 6 判为有；4 < 列数 ≤ 6 时，非 1 月判为有、1 月判为无。即 6 列的表在 1 月以外仍会按「有年度平均」解析。
- 分面积表（`parse_size_index_table`）：其他月份每个面积段 3 列（环比/同比/年度平均）共 10 列，1 月份每段 2 列，纯按总列数 ≥ 10 判断，不看月份。

`is_january` 由数据月份算出：

```python
is_january = (data_month == 1)
```

### 2. 2023 年起官方不再发布定基指数

发布表第三列从「定基」变成了「1-N月平均」（年内累计同比），脚本照旧把它写进 `定基比` 行，所以 2023 年起该行有值但含义已变。**新增逻辑不要假设这些值是定基指数**，也不要假设官方以后一定继续发布这一列。详见 [`fixedbase-caliber.md`](fixedbase-caliber.md)。

## 排查抓取失败

写入前检查（`check_new_records()`）不通过时，脚本会列出问题并退出，主 CSV 不会被改动。先用 `--dry-run` 只抓取、解析和检查，不写文件，然后按这个顺序看：

1. **表格数量不足 6，或前 6 张对应关系变了** —— 官方改版了页面结构。不要盲目调整下标，先把 6 张表逐一打出来确认对应关系。
2. **列数嗅探误判** —— 官方增删了列。检查 `parse_main_index_table` / `parse_size_index_table` 里的列数分支是否还成立。
3. **城市数不足 70 / 城市名无法匹配** —— 分面积表 (一)(二) 的行范围（`start_row` / `end_row`）偏了，或某个城市名没通过标准化链路（见 [`city-naming.md`](city-naming.md)）。
4. **月份解析错 / 与现有最新月份不连续** —— URL 格式变了，`parse_date_from_url()` 的正则没命中。
5. **数值超出区间** —— 几乎一定是列错位，把序号、年份写进了数值列；对照第 2 条检查列数分支。

抓取成功后**必跑** `python3 scripts/validate_70cityprice.py`，它会捕获上述 3 和月份连续性问题。
