#!/usr/bin/env python3
"""从主 CSV 生成 GitHub Pages 使用的紧凑数据文件。"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from common import CITY_ADCODE, get_csv_path, get_repo_root


BASE_COLUMNS = {
    '同比': 'yoy',
    '环比': 'mom',
    '定基比': 'fixed',
}

MARKET_COLUMNS = {
    'new': {
        'all': 'CommodityHouseIDX',
        'below90': 'CommodityBelow90IDX',
        'between90And144': 'Commodity144IDX',
        'above144': 'CommodityAbove144IDX',
    },
    'resale': {
        'all': 'SecondHandIDX',
        'below90': 'SecondHandBelow90IDX',
        'between90And144': 'SecondHand144IDX',
        'above144': 'SecondHandAbove144IDX',
    },
}

Number = Union[int, float]
SeriesKey = Tuple[str, str, str, str, str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='生成 70 城房价网页数据')
    parser.add_argument(
        '--input',
        type=Path,
        default=get_csv_path(),
        help='主 CSV 路径',
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=get_repo_root() / 'site' / 'data',
        help='网页数据输出目录（生成 index.json 与 series/<adcode>.json）',
    )
    return parser.parse_args()


def parse_month(value: str) -> str:
    return datetime.strptime(value, '%Y/%m/%d').strftime('%Y-%m')


def parse_number(value: str) -> Optional[Number]:
    stripped = value.strip()
    if not stripped:
        return None

    number = float(stripped)
    return int(number) if number.is_integer() else number


def read_source(
    csv_path: Path,
) -> Tuple[List[str], Dict[SeriesKey, Optional[Number]]]:
    dates = set()
    values: Dict[SeriesKey, Optional[Number]] = {}

    with csv_path.open(encoding='utf-8-sig', newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {
            'DATE',
            'ADCODE',
            'CITY',
            'FixedBase',
            *(
                column
                for area_columns in MARKET_COLUMNS.values()
                for column in area_columns.values()
            ),
        }
        missing_columns = required_columns.difference(reader.fieldnames or [])
        if missing_columns:
            missing = ', '.join(sorted(missing_columns))
            raise ValueError(f'主 CSV 缺少网页构建所需字段: {missing}')

        for row in reader:
            base = BASE_COLUMNS.get(row['FixedBase'])
            if not base:
                continue

            city = row['CITY'].strip()
            expected_adcode = CITY_ADCODE.get(city)
            if not expected_adcode:
                raise ValueError(f'发现未知城市: {city}')
            if row['ADCODE'].strip() != expected_adcode:
                raise ValueError(f'{city} 的 ADCODE 与权威清单不一致')

            month = parse_month(row['DATE'])
            dates.add(month)
            for market, area_columns in MARKET_COLUMNS.items():
                for area, column in area_columns.items():
                    key = (expected_adcode, market, area, base, month)
                    if key in values:
                        raise ValueError(f'发现重复网页数据键: {key}')
                    values[key] = parse_number(row[column])

    return sorted(dates), values


def build_city_series(
    adcode: str,
    city_name: str,
    dates: List[str],
    values: Dict[SeriesKey, Optional[Number]],
) -> dict:
    """构建单个城市的完整序列分片。"""
    city_series = {}
    for market, area_columns in MARKET_COLUMNS.items():
        market_series = {}
        for area in area_columns:
            area_series = {}
            for base in BASE_COLUMNS.values():
                points = [
                    values.get((adcode, market, area, base, month))
                    for month in dates
                ]
                if all(point is None for point in points):
                    raise ValueError(
                        f'{city_name} 的 {market}/{area}/{base} 没有可用数据'
                    )
                area_series[base] = points
            market_series[area] = area_series
        city_series[market] = market_series
    return city_series


def summarize_latest(points: List[Optional[Number]]) -> Optional[List]:
    """取最后一个有值的读数及其与前一个有值读数的差，返回 [值, 变化, 月份下标]。"""
    latest_index = next(
        (i for i in range(len(points) - 1, -1, -1) if points[i] is not None),
        None,
    )
    if latest_index is None:
        return None

    previous_index = next(
        (i for i in range(latest_index - 1, -1, -1) if points[i] is not None),
        None,
    )
    change = (
        None
        if previous_index is None
        else round(points[latest_index] - points[previous_index], 2)
    )
    return [points[latest_index], change, latest_index]


def build_index(
    dates: List[str],
    series_by_city: Dict[str, dict],
) -> dict:
    """构建首屏骨架：元信息、月份轴、城市清单、各城最新读数截面。"""
    cities = [
        {'name': city, 'adcode': adcode}
        for city, adcode in CITY_ADCODE.items()
    ]
    latest: Dict[str, dict] = {}
    latest_index_by_basis: Dict[str, int] = {}

    for adcode, city_series in series_by_city.items():
        city_latest = {}
        for market, area_columns in MARKET_COLUMNS.items():
            market_latest = {}
            for area in area_columns:
                area_latest = {}
                for base in BASE_COLUMNS.values():
                    summary = summarize_latest(city_series[market][area][base])
                    if summary is None:
                        continue
                    area_latest[base] = summary[:2]
                    latest_index_by_basis[base] = max(
                        latest_index_by_basis.get(base, -1), summary[2]
                    )
                market_latest[area] = area_latest
            city_latest[market] = market_latest
        latest[adcode] = city_latest

    # 各口径的数据终止月份并不相同：定基比 2023 年起停发，
    # 直接用 endMonth 标注定基截面会把 2022 年的读数标成最新月份。
    latest_month_by_basis = {
        base: dates[index] for base, index in latest_index_by_basis.items()
    }

    return {
        'schemaVersion': 3,
        'meta': {
            'source': '国家统计局',
            'startMonth': dates[0],
            'endMonth': dates[-1],
            'monthCount': len(dates),
            'cityCount': len(cities),
            'marketCount': len(MARKET_COLUMNS),
            'areaCount': len(next(iter(MARKET_COLUMNS.values()))),
            'metricCount': sum(
                len(area_columns)
                for area_columns in MARKET_COLUMNS.values()
            ),
            'basisCount': len(BASE_COLUMNS),
            'latestMonthByBasis': latest_month_by_basis,
        },
        'dates': dates,
        'cities': cities,
        'latest': latest,
    }


def write_json(path: Path, payload: dict) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n'
    path.write_text(text, encoding='utf-8')
    return len(text.encode('utf-8'))


def main() -> None:
    args = parse_args()
    dates, values = read_source(args.input)

    series_by_city = {
        adcode: build_city_series(adcode, city, dates, values)
        for city, adcode in CITY_ADCODE.items()
    }

    index_payload = build_index(dates, series_by_city)
    index_bytes = write_json(args.output_dir / 'index.json', index_payload)

    series_bytes = 0
    for adcode, city_series in series_by_city.items():
        series_bytes += write_json(
            args.output_dir / 'series' / f'{adcode}.json', city_series
        )

    print(
        f'网页数据已生成: {args.output_dir} '
        f"({index_payload['meta']['cityCount']} 城市, "
        f"{index_payload['meta']['monthCount']} 个月)"
    )
    print(
        f'  index.json {index_bytes / 1024:.1f} KB · '
        f'series/ {len(series_by_city)} 个分片，'
        f'平均 {series_bytes / len(series_by_city) / 1024:.1f} KB'
    )


if __name__ == '__main__':
    main()
