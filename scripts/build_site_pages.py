#!/usr/bin/env python3
"""生成 70 个城市的静态页面、分享卡片、站点地图与 robots.txt。

主页是交互式单页应用，全部内容由 JS 渲染，搜索引擎只能看到一个 URL。
本脚本为每个城市预渲染一份带真实内容的静态页，让「深圳房价指数」
这类查询能落到具体页面上，同时给出可分享的 og 卡片。
"""

import argparse
import html
import shutil
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from build_site_data import BASE_COLUMNS, MARKET_COLUMNS, read_source
from common import CITY_ADCODE, CITY_SLUG, get_csv_path, get_repo_root

DEFAULT_ORIGIN = 'https://hugohe3.github.io/70cityprice'

MARKET_LABELS = {'new': '新建商品住宅', 'resale': '二手住宅'}
AREA_LABELS = {
    'all': '综合',
    'below90': '90㎡以下',
    'between90And144': '90–144㎡',
    'above144': '144㎡以上',
}
BASIS_LABELS = {'yoy': '同比', 'mom': '环比', 'fixed': '定基/累计'}
BASIS_COMPARISON = {'yoy': '上年同月', 'mom': '上月', 'fixed': '对应基准'}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='生成 70 城静态页面与分享卡片')
    parser.add_argument('--input', type=Path, default=get_csv_path(), help='主 CSV 路径')
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=get_repo_root() / '_site',
        help='构建输出目录（默认 _site/，会先从 site/ 同步静态资源）',
    )
    parser.add_argument(
        '--origin',
        default=DEFAULT_ORIGIN,
        help='站点根 URL，用于 canonical、og:url 与 sitemap',
    )
    parser.add_argument('--build-version', default='dev', help='静态资源版本号')
    parser.add_argument(
        '--skip-images',
        action='store_true',
        help='跳过 og 分享卡片生成（缺少中文字体时用）',
    )
    return parser.parse_args()


def format_month(month: str) -> str:
    year, part = month.split('-')
    return f'{year} 年 {int(part)} 月'


def format_index(value: Optional[float]) -> str:
    return '—' if value is None else f'{value:.1f}'


def format_signed(value: Optional[float]) -> str:
    if value is None:
        return '—'
    return f'{value:+.1f}'


def describe(value: Optional[float]) -> Tuple[str, str]:
    """把指数换算成人话：100 是持平线。"""
    if value is None:
        return '暂无数据', 'flat'
    if value > 100.05:
        return f'上涨 {value - 100:.1f}%', 'rising'
    if value < 99.95:
        return f'下降 {100 - value:.1f}%', 'falling'
    return '基本持平', 'flat'


def series_of(values: Dict, dates: List[str], adcode: str, market: str, area: str, basis: str):
    return [values.get((adcode, market, area, basis, month)) for month in dates]


def latest_of(points: List[Optional[float]]) -> Tuple[Optional[int], Optional[float], Optional[float]]:
    """返回（最后有值的下标, 该值, 与上一个有值读数的差）。"""
    index = next((i for i in range(len(points) - 1, -1, -1) if points[i] is not None), None)
    if index is None:
        return None, None, None
    previous = next((i for i in range(index - 1, -1, -1) if points[i] is not None), None)
    change = None if previous is None else points[index] - points[previous]
    return index, points[index], change


def build_metric_rows(values, dates, adcode) -> List[dict]:
    rows = []
    for market, area_columns in MARKET_COLUMNS.items():
        for area in area_columns:
            entry = {'market': market, 'area': area}
            for basis in BASE_COLUMNS.values():
                points = series_of(values, dates, adcode, market, area, basis)
                index, value, change = latest_of(points)
                entry[basis] = {
                    'month': dates[index] if index is not None else None,
                    'value': value,
                    'change': change,
                }
            rows.append(entry)
    return rows


def build_history(values, dates, adcode, months: int = 12) -> List[dict]:
    new_yoy = series_of(values, dates, adcode, 'new', 'all', 'yoy')
    latest_index, _, _ = latest_of(new_yoy)
    if latest_index is None:
        return []

    start = max(0, latest_index - months + 1)
    history = []
    for index in range(latest_index, start - 1, -1):
        history.append({
            'month': dates[index],
            'new_yoy': new_yoy[index],
            'new_mom': series_of(values, dates, adcode, 'new', 'all', 'mom')[index],
            'resale_yoy': series_of(values, dates, adcode, 'resale', 'all', 'yoy')[index],
            'resale_mom': series_of(values, dates, adcode, 'resale', 'all', 'mom')[index],
        })
    return history


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def render_metric_table(rows: List[dict]) -> str:
    body = []
    for row in rows:
        cells = [
            f'<th scope="row">{esc(MARKET_LABELS[row["market"]])} · {esc(AREA_LABELS[row["area"]])}</th>'
        ]
        for basis in ('yoy', 'mom'):
            entry = row[basis]
            label, tone = describe(entry['value'])
            cells.append(
                f'<td><strong>{format_index(entry["value"])}</strong>'
                f'<span class="tone-{tone}">{esc(label)}</span></td>'
            )
        body.append(f'<tr>{"".join(cells)}</tr>')

    return (
        '<table class="metric-table"><thead><tr>'
        '<th scope="col">指标</th><th scope="col">同比</th><th scope="col">环比</th>'
        f'</tr></thead><tbody>{"".join(body)}</tbody></table>'
    )


def render_history_table(history: List[dict]) -> str:
    body = []
    for item in history:
        body.append(
            '<tr>'
            f'<th scope="row">{esc(format_month(item["month"]))}</th>'
            f'<td>{format_index(item["new_yoy"])}</td>'
            f'<td>{format_index(item["new_mom"])}</td>'
            f'<td>{format_index(item["resale_yoy"])}</td>'
            f'<td>{format_index(item["resale_mom"])}</td>'
            '</tr>'
        )

    return (
        '<table class="history-table"><thead><tr>'
        '<th scope="col">月份</th>'
        '<th scope="col">新房同比</th><th scope="col">新房环比</th>'
        '<th scope="col">二手同比</th><th scope="col">二手环比</th>'
        f'</tr></thead><tbody>{"".join(body)}</tbody></table>'
    )


def render_neighbours(city: str, ordered: List[str]) -> str:
    position = ordered.index(city)
    window = ordered[max(0, position - 3):position] + ordered[position + 1:position + 4]
    links = ''.join(
        f'<li><a href="../{CITY_SLUG[other]}/">{esc(other)}</a></li>' for other in window
    )
    return f'<ul class="neighbour-list">{links}</ul>'


def render_city_page(
    city: str,
    adcode: str,
    rows: List[dict],
    history: List[dict],
    ordered: List[str],
    origin: str,
    build_version: str,
    with_image: bool,
) -> str:
    slug = CITY_SLUG[city]
    headline = next(r for r in rows if r['market'] == 'new' and r['area'] == 'all')
    resale = next(r for r in rows if r['market'] == 'resale' and r['area'] == 'all')
    month = headline['yoy']['month'] or ''
    month_label = format_month(month) if month else '最新月份'
    yoy_value = headline['yoy']['value']
    yoy_text, yoy_tone = describe(yoy_value)
    mom_text, mom_tone = describe(headline['mom']['value'])
    resale_text, resale_tone = describe(resale['yoy']['value'])

    title = (
        f'{city}房价指数 · {month_label}新建商品住宅同比 {format_index(yoy_value)}'
        f' | 70 城房价观察'
    )
    description = (
        f'国家统计局 {month_label}数据：{city}新建商品住宅销售价格同比'
        f'{yoy_text}（指数 {format_index(yoy_value)}），环比{mom_text}；'
        f'二手住宅同比{resale_text}。含近 12 个月明细与 2006 年至今完整历史。'
    )
    canonical = f'{origin}/city/{slug}/'
    image_tags = (
        f'  <meta property="og:image" content="{origin}/og/{slug}.png">\n'
        f'  <meta name="twitter:card" content="summary_large_image">\n'
        if with_image
        else '  <meta name="twitter:card" content="summary">\n'
    )

    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{canonical}">
  <meta name="theme-color" content="#f5f2ea">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="70 城房价观察">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{canonical}">
{image_tags}  <link rel="stylesheet" href="../../city.css?v={esc(build_version)}">
</head>
<body class="city-page">
  <header class="site-header">
    <a class="brand" href="../../">
      <span class="brand-mark" aria-hidden="true">70</span>
      <span>城房价观察</span>
    </a>
    <a class="repository-link" href="https://github.com/hugohe3/70cityprice">数据与源码 <span aria-hidden="true">↗</span></a>
  </header>

  <main>
    <nav class="breadcrumb" aria-label="面包屑">
      <a href="../../">全部城市</a> <span aria-hidden="true">/</span> <span>{esc(city)}</span>
    </nav>

    <h1>{esc(city)}房价指数</h1>
    <p class="lede">
      国家统计局 <strong>{esc(month_label)}</strong>数据：{esc(city)}新建商品住宅销售价格较上年同月{esc(yoy_text)}，
      较上月{esc(mom_text)}；二手住宅较上年同月{esc(resale_text)}。
    </p>

    <div class="headline-grid">
      <article class="headline-card tone-{yoy_tone}">
        <span>新建商品住宅 · 同比</span>
        <strong>{format_index(yoy_value)}</strong>
        <em>{esc(yoy_text)}</em>
      </article>
      <article class="headline-card tone-{mom_tone}">
        <span>新建商品住宅 · 环比</span>
        <strong>{format_index(headline['mom']['value'])}</strong>
        <em>{esc(mom_text)}</em>
      </article>
      <article class="headline-card tone-{resale_tone}">
        <span>二手住宅 · 同比</span>
        <strong>{format_index(resale['yoy']['value'])}</strong>
        <em>{esc(resale_text)}</em>
      </article>
    </div>

    <p class="cta">
      <a class="cta-link" href="../../?city={esc(adcode)}">打开交互版：查看{esc(city)} 2006 年至今完整走势 →</a>
    </p>

    <section>
      <h2>{esc(month_label)}各类住宅指数</h2>
      {render_metric_table(rows)}
      <p class="note">指数以 100 为持平线，代表价格相对比较期的变化幅度，不是每平方米房价。</p>
    </section>

    <section>
      <h2>{esc(city)}近 12 个月明细</h2>
      {render_history_table(history)}
      <p class="note">
        完整历史请<a href="../../70cityprice.csv" download>下载 CSV</a>，
        或在<a href="../../?city={esc(adcode)}">交互版</a>中按面积段与口径筛选。
      </p>
    </section>

    <section>
      <h2>怎么读这些数字</h2>
      <p><strong>同比</strong>以上年同月为 100，适合看中长期变化；<strong>环比</strong>以上月为 100，对近期波动更灵敏。</p>
      <p><strong>定基/累计</strong>不是一条连续序列：基期约每五年轮换一次（2010 → 2015 → 2020），2023 年起改为年内累计同比、每年 1 月重置，跨期数值不可直接比较。</p>
      <p>调查范围为各城市市辖区，不含下辖县。如当月无成交，视为价格总体水平无变动。</p>
    </section>

    <section>
      <h2>其他城市</h2>
      {render_neighbours(city, ordered)}
      <p class="note"><a href="../../">查看全部 70 个城市 →</a></p>
    </section>
  </main>

  <footer>
    <p>70 城房价观察 · 数据来源：国家统计局</p>
    <p>开放数据与代码采用 MIT License</p>
  </footer>
</body>
</html>
'''


def render_sitemap(origin: str, cities: List[str]) -> str:
    today = date.today().isoformat()
    entries = [
        f'  <url><loc>{origin}/</loc><lastmod>{today}</lastmod>'
        f'<changefreq>monthly</changefreq><priority>1.0</priority></url>'
    ]
    entries.extend(
        f'  <url><loc>{origin}/city/{CITY_SLUG[city]}/</loc><lastmod>{today}</lastmod>'
        f'<changefreq>monthly</changefreq><priority>0.8</priority></url>'
        for city in cities
    )
    body = '\n'.join(entries)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'{body}\n'
        '</urlset>\n'
    )


def render_robots(origin: str) -> str:
    return f'User-agent: *\nAllow: /\n\nSitemap: {origin}/sitemap.xml\n'


def inject_home_links(index_path: Path, cities: List[str], origin: str, latest_month: str) -> None:
    """把 70 城静态链接与 og 标签注入主页，让爬虫能顺着爬到城市页。"""
    markup = ''.join(
        f'<li><a href="./city/{CITY_SLUG[city]}/">{esc(city)}</a></li>' for city in cities
    )
    description = (
        f'国家统计局 70 个大中城市住宅销售价格指数，更新至{format_month(latest_month)}。'
        '新房与二手房、四个面积段、同比环比与定基累计口径，2006 年至今完整月度序列。'
    )
    og_tags = (
        '  <meta property="og:type" content="website">\n'
        '  <meta property="og:site_name" content="70 城房价观察">\n'
        '  <meta property="og:title" content="70 城房价观察 · 中国 70 个大中城市住宅价格指数">\n'
        f'  <meta property="og:description" content="{esc(description)}">\n'
        f'  <meta property="og:url" content="{origin}/">\n'
        f'  <meta property="og:image" content="{origin}/og/home.png">\n'
        '  <meta name="twitter:card" content="summary_large_image">\n'
        f'  <link rel="canonical" href="{origin}/">\n'
    )

    text = index_path.read_text(encoding='utf-8')
    text = text.replace('__CITY_LINKS__', markup)
    text = text.replace('<!--__OG_TAGS__-->\n', og_tags)
    index_path.write_text(text, encoding='utf-8')


def render_og_images(site_dir: Path, values, dates, cities: List[str], latest_month: str) -> int:
    """用 matplotlib 生成分享卡片。字体缺失时直接报错，避免产出满屏豆腐块。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    candidates = [
        'PingFang SC', 'Heiti SC', 'Noto Sans CJK SC', 'Noto Sans CJK JP',
        'Source Han Sans SC', 'WenQuanYi Zen Hei', 'SimHei', 'Arial Unicode MS',
    ]
    available = {font.name for font in font_manager.fontManager.ttflist}
    usable = [name for name in candidates if name in available]
    if not usable:
        raise RuntimeError(
            '未找到可用的中文字体，分享卡片会渲染成豆腐块。'
            '请安装中文字体（如 fonts-noto-cjk）或加 --skip-images 跳过。'
        )

    plt.rcParams['font.sans-serif'] = usable
    plt.rcParams['axes.unicode_minus'] = False

    og_dir = site_dir / 'og'
    og_dir.mkdir(parents=True, exist_ok=True)

    def draw(path: Path, title: str, subtitle: str, points: List[Optional[float]]) -> None:
        figure = plt.figure(figsize=(12, 6.3), dpi=100)
        figure.patch.set_facecolor('#f5f2ea')

        figure.text(0.06, 0.86, '70 城房价观察', fontsize=20, color='#d94f31', weight='bold')
        figure.text(0.06, 0.68, title, fontsize=52, color='#1d2623', weight='bold')
        figure.text(0.06, 0.56, subtitle, fontsize=22, color='#5e5446')
        figure.text(0.06, 0.07, '数据来源：国家统计局 · hugohe3.github.io/70cityprice',
                    fontsize=15, color='#8a7f70')

        axes = figure.add_axes([0.06, 0.18, 0.88, 0.32])
        axes.set_facecolor('#f5f2ea')
        recent = [(i, v) for i, v in enumerate(points[-60:]) if v is not None]
        if len(recent) > 1:
            axes.plot([i for i, _ in recent], [v for _, v in recent],
                      color='#d94f31', linewidth=3)
            axes.axhline(100, color='#b9ada0', linewidth=1, linestyle='--')
        for spine in axes.spines.values():
            spine.set_visible(False)
        axes.set_xticks([])
        axes.set_yticks([])

        figure.savefig(path, facecolor=figure.get_facecolor())
        plt.close(figure)

    for city in cities:
        adcode = CITY_ADCODE[city]
        points = series_of(values, dates, adcode, 'new', 'all', 'yoy')
        _, value, _ = latest_of(points)
        label, _ = describe(value)
        draw(
            og_dir / f'{CITY_SLUG[city]}.png',
            f'{city}房价指数',
            f'{format_month(latest_month)} · 新建商品住宅同比 {format_index(value)}（{label}）',
            points,
        )

    beijing = series_of(values, dates, CITY_ADCODE['北京'], 'new', 'all', 'yoy')
    draw(
        og_dir / 'home.png',
        '中国 70 城住宅价格指数',
        f'国家统计局月度数据 · 2006 年至今 · 更新至{format_month(latest_month)}',
        beijing,
    )
    return len(cities) + 1


def prepare_output_dir(output_dir: Path) -> None:
    """把 site/ 的静态资源同步到构建目录。

    绝不能直接写 site/：主页里的 __CITY_LINKS__ 与 og 占位符一旦被替换掉，
    源文件就再也无法重新构建了。
    """
    source = get_repo_root() / 'site'
    if output_dir.resolve() == source.resolve():
        raise SystemExit(
            '拒绝写入 site/ 源目录：主页占位符会被替换掉且无法还原。'
            '请指定其他 --output-dir（默认 _site/）。'
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, output_dir, dirs_exist_ok=True)


def main() -> None:
    args = parse_args()
    dates, values = read_source(args.input)
    cities = list(CITY_ADCODE)
    latest_month = dates[-1]

    prepare_output_dir(args.output_dir)

    city_root = args.output_dir / 'city'
    if city_root.exists():
        shutil.rmtree(city_root)

    for city in cities:
        adcode = CITY_ADCODE[city]
        rows = build_metric_rows(values, dates, adcode)
        history = build_history(values, dates, adcode)
        page = render_city_page(
            city, adcode, rows, history, cities,
            args.origin, args.build_version, not args.skip_images,
        )
        target = city_root / CITY_SLUG[city] / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding='utf-8')

    (args.output_dir / 'sitemap.xml').write_text(
        render_sitemap(args.origin, cities), encoding='utf-8'
    )
    (args.output_dir / 'robots.txt').write_text(
        render_robots(args.origin), encoding='utf-8'
    )
    inject_home_links(args.output_dir / 'index.html', cities, args.origin, latest_month)

    print(f'静态城市页已生成: {city_root} ({len(cities)} 页)')
    print('sitemap.xml / robots.txt 已写入，主页已注入城市索引与 og 标签')

    if args.skip_images:
        print('已跳过分享卡片生成 (--skip-images)')
    else:
        count = render_og_images(args.output_dir, values, dates, cities, latest_month)
        print(f'分享卡片已生成: {args.output_dir / "og"} ({count} 张)')


if __name__ == '__main__':
    main()
