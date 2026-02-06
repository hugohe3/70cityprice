---
description: 生成北上广深房价趋势图
---

# 生成图表工作流

## 功能说明
生成北上广深近10年新建商品住宅价格指数（同比）走势图，保存到 `assets/price_trend.png`。

## 执行步骤

1. 确认已安装必要依赖（pandas, matplotlib）

2. 运行图表生成脚本
// turbo
```bash
python tools/generate_chart.py
```

3. 确认图表已生成到 `assets/price_trend.png`

4. 如需提交更新，建议使用 `/smart-commit`

## 图表内容
- **城市**：北京、上海、广州、深圳
- **指标**：新建商品住宅价格指数（同比）
- **时间范围**：2015年至今
- **参考线**：100（与上年同期持平）
- **城市命名口径**：与主数据一致，使用无"市"后缀写法

## 自定义图表
如需生成其他城市或指标的图表，可修改 `tools/generate_chart.py` 中的参数：
- `cities`: 修改要展示的城市列表
- `start_date`: 修改起始日期
- `FixedBase`: 修改指数类型（同比/环比/定基比）
