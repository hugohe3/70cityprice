---
description: 更新70城房价数据 - 从国家统计局网站抓取最新月份数据
---

# 更新数据工作流

## 前置条件
- 用户需提供国家统计局发布页面的 URL
- URL 格式示例：`https://www.stats.gov.cn/sj/zxfb/202601/t20260119_1962319.html`

## 执行步骤

1. 确认用户提供的 URL 是否为国家统计局70城房价发布页面

2. 运行更新脚本
// turbo
```bash
python tools/update_70cityprice.py "<URL>"
```

3. 检查更新结果，确认数据已追加到 `70cityprice.csv`

4. 运行数据校验脚本，确认数据完整性
// turbo
```bash
python tools/validate_70cityprice.py
```

5. 如果一切正常，提示用户是否需要：
   - 生成新的图表 (`/generate-chart`)
   - 同步更新 README 中的“数据更新至-YYYY年MM月”文案
   - 提交更改 (`/smart-commit`)

## 注意事项
- 脚本会自动检测表格列数，适配不同月份格式
- 1月份数据特殊处理：使用同比数据作为定基比
- 如果该月数据已存在，脚本会替换旧数据
- `CITY` 列会按国家统计局当前写法统一为无"市"后缀
