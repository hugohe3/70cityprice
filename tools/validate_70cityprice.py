#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
70城房价数据质量校验工具
用于校验 70cityprice.csv 的结构完整性与关键数据质量约束

使用方法:
    python tools/validate_70cityprice.py
    python tools/validate_70cityprice.py --csv path/to/70cityprice.csv
"""

import argparse
import os
import sys
from typing import List

import pandas as pd

from update_70cityprice import CITY_ADCODE, standardize_city_column


REQUIRED_COLUMNS = [
    'DATE', 'ADCODE', 'CITY', 'FixedBase', 'HouseIDX', 'ResidentIDX',
    'CommodityHouseIDX', 'SecondHandIDX', 'ResidentBelow90IDX',
    'CommonResidentBelow90IDX', 'CommodityBelow90IDX', 'Commodity144IDX',
    'CommodityAbove144IDX', 'SecondHandBelow90IDX', 'SecondHand144IDX',
    'SecondHandAbove144IDX'
]

ALLOWED_FIXED_BASE = {'同比', '环比', '定基比'}
REQUIRED_FIXED_BASE = {'同比', '环比'}
NUMERIC_COLUMNS = [
    'HouseIDX', 'ResidentIDX', 'CommodityHouseIDX', 'SecondHandIDX',
    'ResidentBelow90IDX', 'CommonResidentBelow90IDX', 'CommodityBelow90IDX',
    'Commodity144IDX', 'CommodityAbove144IDX', 'SecondHandBelow90IDX',
    'SecondHand144IDX', 'SecondHandAbove144IDX'
]
EXPECTED_CITY_COUNT = len(CITY_ADCODE)
EXPECTED_CITY_NAMES = {standardize_city_column(f'{city}市') for city in CITY_ADCODE}


def get_repo_root() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)


def get_default_csv_path() -> str:
    return os.path.join(get_repo_root(), '70cityprice.csv')


def limit_join(items: List[str], max_items: int = 8) -> str:
    if not items:
        return ''
    shown = items[:max_items]
    suffix = '' if len(items) <= max_items else f' ... 共{len(items)}项'
    return ', '.join(shown) + suffix


def non_empty_mask(series: pd.Series) -> pd.Series:
    return series.notna() & (series.astype(str).str.strip() != '')


def validate_csv(csv_path: str, max_details: int = 8) -> int:
    issues: List[str] = []
    warnings: List[str] = []

    if not os.path.exists(csv_path):
        print(f'错误: CSV文件不存在: {csv_path}')
        return 1

    print(f'开始校验: {csv_path}')
    df = pd.read_csv(csv_path, dtype=str)
    print(f'记录数: {len(df)}')

    # 1) 列结构校验
    missing_columns = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    extra_columns = [c for c in df.columns if c not in REQUIRED_COLUMNS]
    if missing_columns:
        issues.append(f"缺少必需列: {', '.join(missing_columns)}")
    if extra_columns:
        warnings.append(f"存在额外列: {', '.join(extra_columns)}")
    if missing_columns:
        return print_report(issues, warnings)

    # 2) 日期与月份连续性校验
    date_parsed = pd.to_datetime(df['DATE'], format='%Y/%m/%d', errors='coerce')
    invalid_dates = sorted(df.loc[date_parsed.isna(), 'DATE'].dropna().astype(str).unique().tolist())
    if invalid_dates:
        issues.append(f"存在无法解析的DATE值: {limit_join(invalid_dates, max_details)}")

    month_series = date_parsed.dt.to_period('M')
    valid_months = sorted(month_series.dropna().unique())
    if not valid_months:
        issues.append('未检测到可用的月份数据')
    else:
        gaps = []
        for prev, curr in zip(valid_months[:-1], valid_months[1:]):
            month_delta = (curr.year - prev.year) * 12 + (curr.month - prev.month)
            if month_delta != 1:
                gaps.append(f'{prev}->{curr}')
        if gaps:
            issues.append(f"月份不连续: {limit_join(gaps, max_details)}")

    # 3) 固定基类型校验
    fixed_base_series = df['FixedBase'].astype(str).str.strip()
    invalid_fixed_base = sorted((set(fixed_base_series.unique()) - ALLOWED_FIXED_BASE) - {'nan'})
    if invalid_fixed_base:
        issues.append(f"存在非法FixedBase值: {', '.join(invalid_fixed_base)}")

    # 4) 城市标准化与城市集合校验
    city_std = df['CITY'].apply(standardize_city_column)
    city_raw = df['CITY'].fillna('').astype(str).str.strip()
    changed_rows = (city_std.fillna('') != city_raw).sum()
    if changed_rows > 0:
        changed_pairs = (
            pd.DataFrame({'raw': city_raw, 'std': city_std})
            .loc[lambda x: x['raw'] != x['std']]
            .drop_duplicates()
        )
        pair_strings = [f"{r.raw}->{r.std}" for r in changed_pairs.itertuples(index=False)]
        issues.append(
            f"检测到{changed_rows}条CITY值不符合标准命名: "
            f"{limit_join(pair_strings, max_details)}"
        )

    city_set = set(city_std.dropna().astype(str).str.strip().tolist())
    unknown_cities = sorted(city_set - EXPECTED_CITY_NAMES)
    if unknown_cities:
        issues.append(f"存在非70城城市名称: {limit_join(unknown_cities, max_details)}")
    if len(city_set) != EXPECTED_CITY_COUNT:
        issues.append(f"标准化后城市数异常: 实际{len(city_set)}，期望{EXPECTED_CITY_COUNT}")

    # 5) 主键唯一性校验（使用标准化城市名）
    key_df = pd.DataFrame({
        'DATE': df['DATE'].astype(str),
        'CITY_STD': city_std.astype(str),
        'FixedBase': fixed_base_series
    })
    duplicated = key_df.duplicated(['DATE', 'CITY_STD', 'FixedBase'], keep=False)
    if duplicated.any():
        dup_samples = (
            key_df.loc[duplicated, ['DATE', 'CITY_STD', 'FixedBase']]
            .drop_duplicates()
            .head(max_details)
        )
        sample_text = ', '.join(
            f"{r.DATE}|{r.CITY_STD}|{r.FixedBase}" for r in dup_samples.itertuples(index=False)
        )
        issues.append(f"存在重复主键(DATE,CITY,FixedBase)，示例: {sample_text}")

    # 6) 月度覆盖校验（每月应覆盖70城）
    coverage_df = pd.DataFrame({'MONTH': month_series, 'CITY_STD': city_std}).dropna()
    month_city_counts = coverage_df.drop_duplicates().groupby('MONTH').size()
    bad_months = month_city_counts[month_city_counts != EXPECTED_CITY_COUNT]
    if len(bad_months) > 0:
        bad_text = [f'{idx}:{val}' for idx, val in bad_months.items()]
        issues.append(f"月度城市覆盖异常(非70城): {limit_join(bad_text, max_details)}")

    # 7) 每个(月, 城市)至少有同比和环比
    base_presence = pd.DataFrame({
        'MONTH': month_series,
        'CITY_STD': city_std,
        'FixedBase': fixed_base_series
    }).dropna()
    base_sets = base_presence.groupby(['MONTH', 'CITY_STD'])['FixedBase'].agg(set)
    missing_required = base_sets[~base_sets.apply(lambda s: REQUIRED_FIXED_BASE.issubset(s))]
    if len(missing_required) > 0:
        sample_idx = list(missing_required.index[:max_details])
        sample_text = ', '.join([f'{m}|{c}' for m, c in sample_idx])
        issues.append(f"存在缺少同比或环比的(月,城市)组合: {sample_text}")

    # 8) 定基比一致性（同一月份不应部分城市有、部分城市无）
    has_fixed_base = base_sets.apply(lambda s: '定基比' in s)
    monthly_ratio = has_fixed_base.groupby(level=0).mean()
    mixed_months = monthly_ratio[(monthly_ratio > 0) & (monthly_ratio < 1)]
    if len(mixed_months) > 0:
        mixed_text = [f'{idx}:{val:.2%}' for idx, val in mixed_months.items()]
        issues.append(f"定基比发布不一致（同月仅部分城市存在）: {limit_join(mixed_text, max_details)}")

    # 9) 数值列格式校验
    for column in NUMERIC_COLUMNS:
        mask = non_empty_mask(df[column])
        if not mask.any():
            continue
        parsed = pd.to_numeric(df.loc[mask, column], errors='coerce')
        invalid_count = int(parsed.isna().sum())
        if invalid_count > 0:
            invalid_index = parsed[parsed.isna()].index
            bad_values = sorted(df.loc[invalid_index, column].astype(str).unique().tolist())
            issues.append(
                f"列{column}存在{invalid_count}个非数值内容: "
                f"{limit_join(bad_values, max_details)}"
            )

    return print_report(issues, warnings)


def print_report(issues: List[str], warnings: List[str]) -> int:
    print('\n================ 校验结果 ================')
    if issues:
        print(f'失败: 发现 {len(issues)} 个问题')
        for idx, text in enumerate(issues, start=1):
            print(f'{idx}. {text}')
    else:
        print('通过: 未发现阻断性问题')

    if warnings:
        print(f'\n告警: {len(warnings)} 项')
        for idx, text in enumerate(warnings, start=1):
            print(f'W{idx}. {text}')

    return 1 if issues else 0


def main() -> int:
    parser = argparse.ArgumentParser(description='70城房价数据质量校验工具')
    parser.add_argument('--csv', default=get_default_csv_path(), help='CSV文件路径')
    parser.add_argument('--max-details', type=int, default=8, help='每项问题最多展示的细节数量')
    args = parser.parse_args()

    return validate_csv(args.csv, max_details=args.max_details)


if __name__ == '__main__':
    sys.exit(main())
