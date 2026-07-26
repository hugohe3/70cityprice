# 网页构建流程

构建 GitHub Pages 站点：交互式浏览器的分片数据，加 70 个城市的静态页与分享卡片。

## 先确认你真的需要手工跑

**正常的月度更新不需要执行本流程。** [`.github/workflows/deploy-pages.yml`](../.github/workflows/deploy-pages.yml) 在每次 push 到 main 后自动构建并部署。

只有这三种情况才手工跑：本地预览、调试构建脚本、排查线上页面异常。

## 两个脚本各管一段

| 脚本 | 产出 |
|---|---|
| `build_site_data.py` | `data/index.json` + `data/series/<adcode>.json`，供交互版按需加载 |
| `build_site_pages.py` | `city/<slug>/index.html` × 70、`og/*.png`、`sitemap.xml`、`robots.txt`，并向主页注入城市索引与 og 标签 |

```bash
python3 scripts/build_site_data.py --output-dir _site/data
python3 scripts/build_site_pages.py --output-dir _site --build-version dev
```

`build_site_pages.py` 会先把 `site/` 的静态资源同步进输出目录，所以本地只跑它也能得到完整站点。

⚠️ **它拒绝写入 `site/` 源目录**。主页里的 `__CITY_LINKS__` 与 `<!--__OG_TAGS__-->` 是一次性占位符，被替换掉就无法还原，脚本检测到目标是源目录会直接退出。

### 数据分片

| 文件 | 内容 | 体积 |
|---|---|---|
| `data/index.json` | 元信息、月份轴、70 城清单、各城最新读数截面 | ~44 KB（gz 7 KB） |
| `data/series/<adcode>.json` | 单城完整历史序列（2 住宅类型 × 4 面积 × 3 口径） | ~31 KB（gz 7 KB） |

首屏只加载 `index.json` 加当前城市一片，切换城市时按需拉取对应分片并缓存。**不要合并回单文件**——那会让首屏重新背上全部 70 城的历史数据。

### 静态城市页

URL 形如 `/city/shenzhen/`，slug 来自 `common.py` 的 `CITY_SLUG`。**这些 slug 一旦发布就不要改**——改了等于换 URL，已收录的页面和分享出去的链接都会失效。

每页是纯静态 HTML（不加载 `app.js`），含最新读数、8 项指标表、近 12 个月明细、口径说明，以及指回交互版的深链 `../../?city=<adcode>`。主页底部的城市索引是爬虫进入这些页面的唯一静态路径——排行榜是 JS 渲染的，爬虫看不到。

### 分享卡片

`og/*.png` 由 matplotlib 绘制，1200×630。**缺少中文字体时脚本直接报错**而不是产出满屏豆腐块；确实没字体又想先出页面，加 `--skip-images`（此时 og:image 标签也会相应省略）。

## 本地预览

```bash
python3 -m http.server 8000 --directory _site
```

⚠️ `site/data/`、`site/city/`、`site/og/`、`site/sitemap.xml`、`site/robots.txt` 全部 **不进仓库**——由 CI 现场生成。

## CI 做的事

`deploy-pages.yml` 的构建步骤：

1. 装 `fonts-noto-cjk` 与 `matplotlib` —— 分享卡片需要
2. `cp -R site/. _site/` + `cp 70cityprice.csv _site/70cityprice.csv` —— 主 CSV 直接对外提供下载
3. `build_site_data.py --output-dir _site/data` —— 生成分片数据
4. `build_site_pages.py --output-dir _site --origin https://hugohe3.github.io/70cityprice --build-version <sha12>` —— 生成城市页、卡片、sitemap，并注入主页
5. 用 `${GITHUB_SHA::12}` 替换 `_site/index.html` 里的 `__BUILD_VERSION__` —— 资源版本号，防止浏览器缓存到旧的 JS/CSS
6. `touch _site/.nojekyll`

第 5 步是为了避免「HTML 更新了但 JS 还是缓存的旧版」这类错配。改 `site/index.html` 时**不要删掉 `__BUILD_VERSION__`、`__CITY_LINKS__`、`<!--__OG_TAGS__-->` 三个占位符**，也不要在本地把它们替换成固定值。

`--origin` 必须与实际部署地址一致，它决定 canonical、og:url 和 sitemap 里的绝对地址。换域名时改这里。

## 站点的数据契约

`build_site_data.py` 从 `common.py` 导入 `CITY_ADCODE`，与主数据共用同一份城市清单。它对主 CSV 有字段依赖，缺列会直接抛 `主 CSV 缺少网页构建所需字段`。

因此：**改 `REQUIRED_COLUMNS` 或重命名任何列，都必须同步检查 `build_site_data.py` 和 `site/app.js`**。CSV 是唯一事实源，网页只是它的一个视图，不维护第二份数据副本。

## 排查线上异常

1. 先本地跑一遍两个构建脚本，看是不是数据本身的问题
2. 跑 `python3 scripts/validate_70cityprice.py` 排除主 CSV 回归
3. 都正常就看 Actions 日志，通常是构建步骤的路径或权限问题
4. 城市页少了几页 → 检查 `CITY_SLUG` 是否与 `CITY_ADCODE` 完全对齐（新增城市时两处都要加）
5. 分享卡片是豆腐块 → CI 的字体安装步骤失败了，脚本本应拦住这种情况，检查报错为何被吞掉
