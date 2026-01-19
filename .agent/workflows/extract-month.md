---
description: 按月份范围提取70城房价数据
---

# 按月份提取数据工作流

## 前置条件
- 用户需提供起始月份和结束月份
- 日期格式支持：YYYYMM、YYYY-MM、YYYY/MM

## 执行步骤

1. 确认用户要提取的月份范围

2. 运行提取脚本
// turbo
```bash
python tools/extract_70cityprice.py month <起始月份> <结束月份> [输出文件名]
```

**示例**：
```bash
# 提取2025年7月至11月数据
python tools/extract_70cityprice.py month 202507 202511

# 指定输出文件名
python tools/extract_70cityprice.py month 202507 202511 my_data.csv

# 支持多种日期格式
python tools/extract_70cityprice.py month 2024-01 2024-12
```

3. 确认数据已保存到 `projects/` 目录

## 组合过滤（城市+月份）

如需同时按城市和月份过滤：
// turbo
```bash
python tools/extract_70cityprice.py filter --cities <城市1> <城市2> --start <起始月份> --end <结束月份>
```

**示例**：
```bash
python tools/extract_70cityprice.py filter --cities 成都市 重庆市 --start 202401 --end 202412
```

## 辅助命令

查看数据日期范围：
// turbo
```bash
python tools/extract_70cityprice.py list-dates
```

## 输出说明
- 默认保存到 `projects/` 目录
- 文件名格式：`70cityprice_<起始月份>_<结束月份>.csv`
