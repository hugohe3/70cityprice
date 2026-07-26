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
        '--output',
        type=Path,
        default=get_repo_root() / 'site' / 'data' / 'dashboard.json',
        help='网页数据输出路径',
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


def build_payload(
    dates: List[str],
    values: Dict[SeriesKey, Optional[Number]],
) -> dict:
    cities = [
        {'name': city, 'adcode': adcode}
        for city, adcode in CITY_ADCODE.items()
    ]
    series = {}

    for city in cities:
        adcode = city['adcode']
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
                            f"{city['name']} 的 "
                            f"{market}/{area}/{base} 没有可用数据"
                        )
                    area_series[base] = points
                market_series[area] = area_series
            city_series[market] = market_series
        series[adcode] = city_series

    return {
        'schemaVersion': 2,
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
        },
        'dates': dates,
        'cities': cities,
        'series': series,
    }


def main() -> None:
    args = parse_args()
    dates, values = read_source(args.input)
    payload = build_payload(dates, values)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n',
        encoding='utf-8',
    )
    print(
        f"网页数据已生成: {args.output} "
        f"({payload['meta']['cityCount']} 城市, "
        f"{payload['meta']['monthCount']} 个月)"
    )


if __name__ == '__main__':
    main()
