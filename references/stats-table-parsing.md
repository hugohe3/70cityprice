# 国家统计局发布页的表格解析约定

改动 [`scripts/update_70cityprice.py`](../scripts/update_70cityprice.py) 的解析逻辑，或排查抓取失败时读本文件。

## 发布页结构

来源：`https://www.stats.gov.cn/sj/zxfbhjd/` 下属各月份目录，通常每月 15–17 日发布上一月数据。

一个发布页含 **6 张表**，脚本按固定下标处理（`process_tables()`）：

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

`parse_date_from_url()` 拿不到日期时会退回 `parse_date_from_title()` 从表格标题里找。两者都失败就中止，不要瞎猜月份。

## 两类历史口径差异（改代码时必须保留）

### 1. 1 月份数据没有「年度平均」列

其他月份的主表每侧是 4 列：`城市 | 环比 | 同比 | 年度平均`（左右双栏共 8 列）。
1 月份只有 3 列：`城市 | 环比 | 同比` —— 因为 1 月是当年第一个月，累计平均就等于当月。

脚本通过**列数嗅探**判断（不是靠月份硬编码），命中时把**同比值复制进定基比**字段：

```python
is_january = (data_month == 1)
```

分面积表同理：其他月份每个面积段 3 列（环比/同比/年度平均）共 10 列，1 月份每段 2 列。`parse_size_index_table` 用总列数少于 10 来判断。

### 2. 2023 年起官方不再发布定基指数

旧数据保留定基行，所以 schema 仍含该列。**新增逻辑不要假设定基比对 2023 年以后的月份必有值**。详见 [`fixedbase-caliber.md`](fixedbase-caliber.md)。

## 排查抓取失败

按这个顺序看：

1. **表格数量不是 6** —— 官方改版了页面结构。不要盲目调整下标，先把 6 张表逐一打出来确认对应关系。
2. **列数嗅探误判** —— 官方增删了列。检查 `parse_main_index_table` / `parse_size_index_table` 里的列数分支是否还成立。
3. **城市数不足 70** —— 分面积表 (一)(二) 的行范围（`start_row` / `end_row`）偏了，或某个城市名没通过标准化链路（见 [`city-naming.md`](city-naming.md)）。
4. **月份解析错** —— URL 格式变了，`parse_date_from_url()` 的正则没命中。

抓取成功后**必跑** `python3 scripts/validate_70cityprice.py`，它会捕获上述 3 和月份连续性问题。
