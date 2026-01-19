---
description: 按城市提取70城房价数据
---

# 按城市提取数据工作流

## 前置条件
- 用户需提供要提取的城市名称（支持多个）
- 城市名称需包含"市"后缀，如"成都市"、"北京市"

## 执行步骤

1. 确认用户要提取的城市名称

2. 运行提取脚本
// turbo
```bash
python tools/extract_70cityprice.py city <城市1> [城市2] ... [--output 输出文件名]
```

**示例**：
```bash
# 单个城市
python tools/extract_70cityprice.py city 成都市

# 多个城市
python tools/extract_70cityprice.py city 北京市 上海市 广州市 深圳市

# 指定输出文件名
python tools/extract_70cityprice.py city 成都市 --output chengdu.csv
```

3. 确认数据已保存到 `projects/` 目录

## 辅助命令

列出所有可用城市：
// turbo
```bash
python tools/extract_70cityprice.py list-cities
```

## 输出说明
- 默认保存到 `projects/` 目录
- 文件名格式：`70cityprice_<城市名>.csv`
