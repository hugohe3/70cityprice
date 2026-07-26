# 数据提取流程

按城市、月份或组合条件从主 CSV 取子集。也是回答数据类问题时的查询入口。

## 输入约定

- **日期格式**：`YYYYMM`、`YYYY-MM`、`YYYY/MM` 均可
- **城市名**：默认用国家统计局当前写法（无「市」后缀），同时兼容 `北京市`、`大理白族自治州` 这类旧写法——脚本内部跑标准化链路，见 [`references/city-naming.md`](../references/city-naming.md)
- **指数类型** `--fixedbase` / `-f`：`同比` / `环比` / `定基比`，逗号分隔可多选

⚠️ 涉及 `定基比` 时，解释数值前必读 [`references/fixedbase-caliber.md`](../references/fixedbase-caliber.md)。跨年份的定基比不能拼成一条序列。

## 三个子命令

### 按月份

```bash
python3 scripts/extract_70cityprice.py month <起始月份> <结束月份> [输出文件名] [--fixedbase 指数类型]
```

```bash
python3 scripts/extract_70cityprice.py month 202507 202511
python3 scripts/extract_70cityprice.py month 2024-01 2024-12 --fixedbase 环比
```

### 按城市

```bash
python3 scripts/extract_70cityprice.py city <城市1> [城市2] ... [--output 文件名] [--fixedbase 指数类型]
```

```bash
python3 scripts/extract_70cityprice.py city 成都
python3 scripts/extract_70cityprice.py city 北京 上海 广州 深圳
python3 scripts/extract_70cityprice.py city 重庆 --fixedbase 环比
python3 scripts/extract_70cityprice.py city 成都 --fixedbase 同比,环比
```

### 组合过滤

```bash
python3 scripts/extract_70cityprice.py filter --cities <城市...> --start <起始月份> --end <结束月份> [--output 文件名] [--fixedbase 指数类型]
```

```bash
python3 scripts/extract_70cityprice.py filter --cities 成都 重庆 --start 202401 --end 202412
python3 scripts/extract_70cityprice.py filter --cities 重庆 --start 202301 --end 202512 --fixedbase 环比
```

## 辅助命令

```bash
python3 scripts/extract_70cityprice.py list-cities
python3 scripts/extract_70cityprice.py list-dates
```

用户给的城市名匹配不上时，先跑 `list-cities` 看规范写法，不要手工猜。

## 输出位置

| 情况 | 输出 |
|---|---|
| 不指定 `--output` | `projects/` 目录 |
| `--output my.csv` | `projects/my.csv` |
| `--output data/my.csv` | 指定路径 |

默认文件名：`month` → `70cityprice_<起始>_<结束>.csv`，`city` → `70cityprice_<城市名>.csv`，`filter` → `70cityprice_filtered.csv`。

`projects/` 已在 `.gitignore` 中，生成的子集不会进仓库——也**不要**手工把它们加进去。

## 指数类型速查

| 类型 | 含义 | 基期 |
|---|---|---|
| `同比` | 与上年同月相比 | 上年同月 = 100 |
| `环比` | 与上月相比 | 上月 = 100 |
| `定基比` | 与基期相比 / 年内累计 | **含义随年份变，见 fixedbase-caliber.md** |

短期趋势问题（1–2 年）一律用 `同比` / `环比`，不要碰定基比。
