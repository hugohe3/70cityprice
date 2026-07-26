# 月度更新流程

抓取国家统计局最新发布的月度数据，追加到主 CSV，并同步仓库里所有派生产物。

## 前置条件

- 用户提供国家统计局发布页 URL，形如 `https://www.stats.gov.cn/sj/zxfb/202601/t20260119_1962319.html`
- 确认这是「70个大中城市商品住宅销售价格变动情况」发布页，不是其他统计公报
- 记住 **URL 里的月份是发布月，数据月份要减 1**（详见 [`references/stats-table-parsing.md`](../references/stats-table-parsing.md)）

发布节奏：每月 15–17 日发布上一月数据。用户没给 URL 时，让他从 `https://www.stats.gov.cn/sj/zxfbhjd/` 找当月条目，不要自行猜测 URL。

## 步骤

### 1. 抓取并追加

```bash
python3 scripts/update_70cityprice.py "<发布页URL>"
```

脚本原地修改 [`70cityprice.csv`](../70cityprice.csv)。同月份已存在会被**替换**而非重复追加，所以重跑是安全的。

留意输出里的数据月份是否符合预期（发布月 − 1）。不符就先停下排查，不要往下走。

### 2. 校验（不可跳过）

```bash
python3 scripts/validate_70cityprice.py
```

检查结构、主键唯一性、月份连续性、70 城覆盖。本仓库没有测试套件和 CI 检查，这一步就是唯一的回归测试。

**校验不通过就停止**，按 [`references/stats-table-parsing.md`](../references/stats-table-parsing.md) 的「排查抓取失败」排查，不要带着告警继续后续步骤。

### 3. 同步 README 的月份标记

两处都要改，必须与新数据月份一致：

- 顶部徽章：`![数据更新](https://img.shields.io/badge/数据更新至-YYYY年M月-blue)`
- 「目录结构」里 `70cityprice.csv` 那行的「当前更新至YYYY年M月」

### 4. 重绘走势图

```bash
python3 scripts/generate_chart.py
```

更新 [`assets/price_trend.png`](../assets/price_trend.png)，这是 README 的配图。细节见 [`chart.md`](chart.md)。

### 5. 网页数据

GitHub Actions 在 push 到 main 后会自动构建并部署，**正常情况下本地不需要手工跑**。只在需要本地预览或调试构建时才执行 [`site-build.md`](site-build.md)。

注意 `site/data/` 下的 `index.json` 与 `series/` 不进仓库，靠 CI 现场生成——不要手工提交它们。

### 6. 提交

提交信息遵循历史格式：

```
chore(数据): 更新70城房价数据至YYYY年M月
```

本次改动应当只涉及 `70cityprice.csv`、`README.md`、`assets/price_trend.png` 三个文件。若 CSV 出现了远超一个月增量的巨量 diff，说明写回格式被破坏了（`utf-8-sig` + `QUOTE_ALL`），见 [`references/schema.md`](../references/schema.md)，**不要提交**。

## 检查清单

- [ ] 数据月份 = 发布月 − 1，且与上月连续
- [ ] `validate_70cityprice.py` 全部通过
- [ ] README 徽章与目录结构两处月份都已更新
- [ ] `price_trend.png` 已重绘
- [ ] CSV diff 规模合理（约一个月的增量，70 城 × 3 行）
