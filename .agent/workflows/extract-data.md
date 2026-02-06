---
description: 提取70城房价数据（按城市、按月份、组合过滤）
---

# 提取数据工作流

## 前置条件
- 用户需提供提取条件（城市、月份范围、或两者组合）
- 日期格式支持：`YYYYMM`、`YYYY-MM`、`YYYY/MM`
- 城市名默认使用国家统计局当前写法（无"市"后缀），兼容旧写法（如"北京市"）

## 核心命令

// turbo
```bash
python tools/extract_70cityprice.py <subcommand> ...
```

支持子命令：
- `month`：按月份范围提取
- `city`：按城市提取
- `filter`：按城市+月份组合过滤

支持可选参数：
- `--fixedbase` / `-f`：指数类型过滤（`同比` / `环比` / `定基比`，支持逗号分隔多值）

## 指数类型速查
- `同比`：与上年同月相比
- `环比`：与上月相比
- `定基比`：与基期/累计口径相比

常用示例：
```bash
python tools/extract_70cityprice.py city 成都 --fixedbase 同比
python tools/extract_70cityprice.py city 成都 --fixedbase 环比
python tools/extract_70cityprice.py city 成都 --fixedbase 定基比
python tools/extract_70cityprice.py city 成都 --fixedbase 同比,环比
```

## 常用场景

### 1) 按月份提取
// turbo
```bash
python tools/extract_70cityprice.py month <起始月份> <结束月份> [输出文件名] [--fixedbase 指数类型]
```

示例：
```bash
python tools/extract_70cityprice.py month 202507 202511
python tools/extract_70cityprice.py month 2024-01 2024-12 --fixedbase 环比
```

### 2) 按城市提取
// turbo
```bash
python tools/extract_70cityprice.py city <城市1> [城市2] ... [--output 输出文件名] [--fixedbase 指数类型]
```

示例：
```bash
python tools/extract_70cityprice.py city 成都
python tools/extract_70cityprice.py city 北京 上海 广州 深圳
python tools/extract_70cityprice.py city 重庆 --fixedbase 环比
```

### 3) 组合过滤（城市+月份）
// turbo
```bash
python tools/extract_70cityprice.py filter --cities <城市1> <城市2> ... --start <起始月份> --end <结束月份> [--output 输出文件名] [--fixedbase 指数类型]
```

示例：
```bash
python tools/extract_70cityprice.py filter --cities 成都 重庆 --start 202401 --end 202412
python tools/extract_70cityprice.py filter --cities 重庆 --start 202301 --end 202512 --fixedbase 环比
```

## 辅助命令
// turbo
```bash
python tools/extract_70cityprice.py list-cities
python tools/extract_70cityprice.py list-dates
```

## 输出说明
- 默认保存到 `projects/` 目录
- `month` 默认文件名：`70cityprice_<起始月份>_<结束月份>.csv`
- `city` 默认文件名：`70cityprice_<城市名>.csv`
- `filter` 默认文件名：`70cityprice_filtered.csv`
