# 走势图生成流程

重绘 [`assets/price_trend.png`](../assets/price_trend.png)，也就是 README 里的那张配图。

## 用途边界

`scripts/generate_chart.py` 是**README 配图的专用生成器**，不是通用绘图工具。它硬编码了城市、指标、时间范围和输出路径。用户要别的图时见下方「画别的图」。

## 执行

```bash
python3 scripts/generate_chart.py
```

依赖 `pandas`、`matplotlib`（见 [`requirements.txt`](../requirements.txt)）。输出覆盖 `assets/price_trend.png`。

## 图表内容

| 项 | 值 |
|---|---|
| 城市 | 北京、上海、广州、深圳 |
| 指标 | `CommodityHouseIDX`（新建商品住宅指数） |
| 指数类型 | `同比` |
| 时间范围 | 2015-01 至今 |
| 参考线 | 100（与上年同期持平） |

用同比而非定基比是有意为之——定基比跨年份不可比，画成一条线会在基期轮换处出现假跳变。见 [`references/fixedbase-caliber.md`](../references/fixedbase-caliber.md)。

## 中文字体

脚本按 `PingFang SC → Heiti SC → SimHei → Arial Unicode MS` 顺序回退。Linux 上若这些都没有，图里中文会变成方框——装一个中文字体（如 `fonts-noto-cjk`）或往这个列表里加本机已有的字体名，不要改成英文标签。

## 画别的图

不要为一次性需求改 `generate_chart.py`——它一改，README 配图就跟着变了。正确做法是先用 [`extract.md`](extract.md) 取子集，再在 `projects/` 下写临时脚本，输出也放 `projects/`（已被 gitignore）。

只有当 README 配图本身要换内容时，才改 `generate_chart.py` 里的 `cities`、`start_date`、`FixedBase` 筛选条件，并同步 README 里的图注文字。

## 何时跑

月度更新的第 4 步（见 [`monthly-update.md`](monthly-update.md)）。数据没更新时不需要重跑——输出会因为 matplotlib 渲染差异产生二进制 diff，白白增加仓库体积。
