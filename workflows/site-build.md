# 网页数据构建流程

构建 GitHub Pages 数据浏览器所需的紧凑数据文件。

## 先确认你真的需要手工跑

**正常的月度更新不需要执行本流程。** [`.github/workflows/deploy-pages.yml`](../.github/workflows/deploy-pages.yml) 在每次 push 到 main 后自动构建并部署。

只有这三种情况才手工跑：本地预览网页、调试 `build_site_data.py`、排查线上页面数据异常。

## 本地构建

```bash
python3 scripts/build_site_data.py
```

默认从 [`70cityprice.csv`](../70cityprice.csv) 读，输出到 `site/data/dashboard.json`。可用 `--input` / `--output` 覆盖。

本地预览：

```bash
python3 -m http.server 8000 --directory site
```

然后访问 `http://localhost:8000`。

⚠️ `site/data/dashboard.json` **不进仓库**——它由 CI 现场生成。本地跑完记得别把它提交进去（`site/data/` 下只保留 `.gitkeep`）。

## CI 做的事

`deploy-pages.yml` 的构建步骤：

1. `cp -R site/. _site/` —— 拷静态资源
2. `cp 70cityprice.csv _site/70cityprice.csv` —— 主 CSV 直接对外提供下载
3. `python3 scripts/build_site_data.py --output _site/data/dashboard.json` —— 生成紧凑数据
4. 用 `${GITHUB_SHA::12}` 替换 `_site/index.html` 里的 `__BUILD_VERSION__` —— 资源版本号，防止浏览器缓存到旧的 JS/CSS
5. `touch _site/.nojekyll`

第 4 步是为了避免「HTML 更新了但 JS 还是缓存的旧版」这类错配。改 `site/index.html` 时**不要删掉 `__BUILD_VERSION__` 占位符**，也不要在本地把它替换成固定值。

## 站点的数据契约

`build_site_data.py` 从 `common.py` 导入 `CITY_ADCODE`，与主数据共用同一份城市清单。它对主 CSV 有字段依赖，缺列会直接抛 `主 CSV 缺少网页构建所需字段`。

因此：**改 `REQUIRED_COLUMNS` 或重命名任何列，都必须同步检查 `build_site_data.py` 和 `site/app.js`**。CSV 是唯一事实源，网页只是它的一个视图，不维护第二份数据副本。

## 排查线上异常

1. 先本地跑一遍 `build_site_data.py`，看是不是数据本身的问题
2. 跑 `python3 scripts/validate_70cityprice.py` 排除主 CSV 回归
3. 都正常就看 Actions 日志，通常是构建步骤的路径或权限问题
