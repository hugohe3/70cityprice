# -*- coding: utf-8 -*-
"""
70城房价数据提取工具
用于从70cityprice.csv中按月份范围或城市提取数据

使用方法:
    # 按月份提取
    python3 extract_70cityprice.py month <起始月份> <结束月份> [输出文件名] [--fixedbase 指数类型]
    
    # 按城市提取
    python3 extract_70cityprice.py city <城市名1> [城市名2] ... [--output 输出文件名] [--fixedbase 指数类型]
    
    # 组合提取（指定城市+月份范围）
    python3 extract_70cityprice.py filter --cities <城市1> <城市2> ... --start <起始月份> --end <结束月份> [--output 输出文件名] [--fixedbase 指数类型]
    
    # 列出所有可用城市
    python3 extract_70cityprice.py list-cities
    
    # 列出数据日期范围
    python3 extract_70cityprice.py list-dates

示例:
    python3 extract_70cityprice.py month 202507 202511
    python3 extract_70cityprice.py month 202507 202511 output.csv
    python3 extract_70cityprice.py month 202507 202511 --fixedbase 环比
    python3 extract_70cityprice.py city 北京 上海 广州 深圳
    python3 extract_70cityprice.py city 成都 --output chengdu_data.csv
    python3 extract_70cityprice.py filter --cities 成都 重庆 --start 202401 --end 202412 --fixedbase 同比,环比
    python3 extract_70cityprice.py list-cities
    python3 extract_70cityprice.py list-dates

日期格式: YYYYMM (例如: 202507 表示2025年7月)
指数类型: 同比 / 环比 / 定基比（支持逗号分隔多个）
"""

import sys
import argparse
from pathlib import Path

import pandas as pd

from common import ALLOWED_FIXED_BASES, get_csv_path, get_repo_root, normalize_city_name


def parse_month_arg(month_str):
    """
    解析月份参数
    支持格式: YYYYMM, YYYY-MM, YYYY/MM
    返回: (year, month)
    """
    # 移除可能的分隔符
    month_str = month_str.replace('-', '').replace('/', '')
    
    if len(month_str) != 6:
        raise ValueError(f"无效的月份格式: {month_str}，请使用YYYYMM格式（如202507）")
    
    try:
        year = int(month_str[:4])
        month = int(month_str[4:6])
        
        if month < 1 or month > 12:
            raise ValueError(f"无效的月份: {month}")
        
        return year, month
    except ValueError as e:
        raise ValueError(f"无效的月份格式: {month_str}，请使用YYYYMM格式（如202507）")


def date_to_comparable(date_str):
    """
    将CSV中的日期字符串转换为可比较的格式 (year, month)
    CSV格式: YYYY/M/D
    """
    try:
        parts = date_str.split('/')
        year = int(parts[0])
        month = int(parts[1])
        return (year, month)
    except (AttributeError, IndexError, TypeError, ValueError):
        return None


def get_output_path(filename):
    """获取输出文件路径（默认保存到 projects/ 目录）"""
    output_path = Path(filename)
    # 如果文件名已包含路径分隔符，则直接使用
    if output_path.is_absolute() or output_path.parent != Path('.'):
        return output_path if output_path.is_absolute() else get_repo_root() / output_path
    # 否则默认保存到 projects/ 目录
    projects_dir = get_repo_root() / 'projects'
    projects_dir.mkdir(exist_ok=True)
    return projects_dir / filename


def load_data(csv_path=None):
    """加载CSV数据"""
    if csv_path is None:
        csv_path = get_csv_path()
    
    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"错误: CSV文件不存在: {csv_path}")
        sys.exit(1)
    
    print(f"正在读取数据文件: {csv_path}")
    df = pd.read_csv(csv_path, dtype=str)
    print(f"总记录数: {len(df)}")
    return df


def save_data(df, output_path):
    """保存数据到CSV"""
    df.to_csv(output_path, index=False, quoting=1)
    print(f"\n✅ 数据已保存到: {output_path}")


def extract_by_month(df, start_year, start_month, end_year, end_month):
    """
    按月份范围提取数据
    """
    start_tuple = (start_year, start_month)
    end_tuple = (end_year, end_month)
    
    print(f"提取范围: {start_year}年{start_month}月 至 {end_year}年{end_month}月")
    
    def in_range(date_str):
        date_tuple = date_to_comparable(date_str)
        if date_tuple is None:
            return False
        return start_tuple <= date_tuple <= end_tuple
    
    mask = df['DATE'].apply(in_range)
    return df[mask].copy()


def extract_by_city(df, cities):
    """
    按城市提取数据
    """
    print(f"提取城市: {', '.join(cities)}")

    def normalize_city_exact(name):
        """城市名精确归一化：仅清理空白和大小写"""
        if pd.isna(name):
            return ''
        return normalize_city_name(name, strip_suffix=False)

    def normalize_city_fuzzy(name):
        """城市名宽松归一化：额外忽略常见行政后缀"""
        return normalize_city_name(name, strip_suffix=True)

    # 先做精确匹配
    requested_exact = {normalize_city_exact(city) for city in cities}
    city_exact = df['CITY'].apply(normalize_city_exact)
    exact_mask = city_exact.isin(requested_exact)

    # 再做宽松匹配（兼容“北京市”这类后缀写法）
    requested_fuzzy = {normalize_city_fuzzy(city) for city in cities}
    city_fuzzy = df['CITY'].apply(normalize_city_fuzzy)
    fuzzy_mask = city_fuzzy.isin(requested_fuzzy)
    used_fuzzy_fallback = bool((~exact_mask & fuzzy_mask).any())
    if used_fuzzy_fallback:
        print("提示: 已启用宽松匹配（忽略“市/自治州/地区/盟”等后缀）补充结果")

    combined_mask = exact_mask | fuzzy_mask
    return df[combined_mask].copy()


def parse_fixedbase_arg(fixedbase_arg):
    """
    解析指数类型参数
    支持格式:
      - 单个值: 环比
      - 逗号分隔: 同比,环比
    返回: set[str]
    """
    if not fixedbase_arg:
        return None
    parts = [p.strip() for p in str(fixedbase_arg).split(',') if p.strip()]
    if not parts:
        return None
    invalid = sorted(set(parts) - ALLOWED_FIXED_BASES)
    if invalid:
        raise ValueError(
            f"无效的指数类型: {', '.join(invalid)}，可选值为: {', '.join(sorted(ALLOWED_FIXED_BASES))}"
        )
    return set(parts)


def extract_by_fixedbase(df, fixedbases):
    """
    按指数类型提取数据
    """
    if not fixedbases:
        return df
    print(f"提取指数类型: {', '.join(sorted(fixedbases))}")
    mask = df['FixedBase'].astype(str).str.strip().isin(fixedbases)
    return df[mask].copy()


def print_extraction_stats(df, extracted_df):
    """打印提取统计信息"""
    extracted_records = len(extracted_df)
    print(f"提取到 {extracted_records} 条记录")
    
    if extracted_records == 0:
        print("警告: 未找到符合条件的数据")
        return
    
    # 统计提取的月份
    months = extracted_df['DATE'].apply(date_to_comparable).dropna().unique()
    months_sorted = sorted(months)
    print(f"提取的月份: {', '.join([f'{m[0]}/{m[1]}' for m in months_sorted])}")
    
    # 统计城市数量
    cities = extracted_df['CITY'].unique()
    print(f"涉及城市数: {len(cities)}")


def cmd_month(args):
    """按月份提取命令"""
    try:
        start_year, start_month = parse_month_arg(args.start)
        end_year, end_month = parse_month_arg(args.end)
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)
    
    if (start_year, start_month) > (end_year, end_month):
        print("错误: 起始月份不能晚于结束月份")
        sys.exit(1)
    
    try:
        fixedbases = parse_fixedbase_arg(args.fixedbase)
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)

    df = load_data()
    extracted_df = extract_by_month(df, start_year, start_month, end_year, end_month)
    extracted_df = extract_by_fixedbase(extracted_df, fixedbases)
    print_extraction_stats(df, extracted_df)
    
    if len(extracted_df) > 0:
        if args.output:
            output_filename = args.output
        else:
            output_filename = f"70cityprice_{start_year}{start_month:02d}_{end_year}{end_month:02d}.csv"
        
        output_path = get_output_path(output_filename)
        save_data(extracted_df, output_path)
    
    return extracted_df


def cmd_city(args):
    """按城市提取命令"""
    if not args.cities:
        print("错误: 请指定至少一个城市")
        sys.exit(1)

    try:
        fixedbases = parse_fixedbase_arg(args.fixedbase)
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)

    df = load_data()
    extracted_df = extract_by_city(df, args.cities)
    extracted_df = extract_by_fixedbase(extracted_df, fixedbases)
    print_extraction_stats(df, extracted_df)
    
    if len(extracted_df) > 0:
        if args.output:
            output_filename = args.output
        else:
            cities_str = '_'.join(args.cities[:3])  # 最多使用3个城市名
            if len(args.cities) > 3:
                cities_str += '_等'
            output_filename = f"70cityprice_{cities_str}.csv"
        
        output_path = get_output_path(output_filename)
        save_data(extracted_df, output_path)
    else:
        # 显示可用城市提示
        all_cities = sorted(df['CITY'].unique())
        print(f"\n可用城市列表 ({len(all_cities)}个):")
        # 分列显示
        cols = 5
        for i in range(0, len(all_cities), cols):
            row = all_cities[i:i+cols]
            print("  " + "  ".join(f"{c:<8}" for c in row))
    
    return extracted_df


def cmd_filter(args):
    """组合过滤提取命令"""
    df = load_data()
    extracted_df = df.copy()

    try:
        fixedbases = parse_fixedbase_arg(args.fixedbase)
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)
    
    # 按城市过滤
    if args.cities:
        extracted_df = extract_by_city(extracted_df, args.cities)
    
    # 按月份过滤
    if args.start and args.end:
        try:
            start_year, start_month = parse_month_arg(args.start)
            end_year, end_month = parse_month_arg(args.end)
        except ValueError as e:
            print(f"错误: {e}")
            sys.exit(1)
        
        if (start_year, start_month) > (end_year, end_month):
            print("错误: 起始月份不能晚于结束月份")
            sys.exit(1)
        
        extracted_df = extract_by_month(extracted_df, start_year, start_month, end_year, end_month)

    # 按指数类型过滤
    extracted_df = extract_by_fixedbase(extracted_df, fixedbases)
    
    print_extraction_stats(df, extracted_df)
    
    if len(extracted_df) > 0:
        if args.output:
            output_filename = args.output
        else:
            output_filename = "70cityprice_filtered.csv"
        
        output_path = get_output_path(output_filename)
        save_data(extracted_df, output_path)
    
    return extracted_df


def cmd_list_cities(args):
    """列出所有可用城市"""
    df = load_data()
    all_cities = sorted(df['CITY'].unique())
    
    print(f"\n📍 可用城市列表 ({len(all_cities)}个):\n")
    
    # 按首字母分组显示
    # 简单分列显示
    cols = 5
    for i in range(0, len(all_cities), cols):
        row = all_cities[i:i+cols]
        print("  " + "  ".join(f"{c:<8}" for c in row))
    
    print(f"\n总计: {len(all_cities)} 个城市")


def cmd_list_dates(args):
    """列出数据日期范围"""
    df = load_data()
    
    all_dates = df['DATE'].apply(date_to_comparable).dropna()
    unique_dates = sorted(set(all_dates))
    
    if len(unique_dates) == 0:
        print("未找到有效日期数据")
        return
    
    min_date = min(unique_dates)
    max_date = max(unique_dates)
    
    print(f"\n📅 数据日期范围:")
    print(f"   起始: {min_date[0]}年{min_date[1]}月")
    print(f"   结束: {max_date[0]}年{max_date[1]}月")
    print(f"   共计: {len(unique_dates)} 个月份的数据")
    
    # 按年份统计
    from collections import Counter
    year_counts = Counter(d[0] for d in unique_dates)
    
    print(f"\n📊 各年份数据统计:")
    for year in sorted(year_counts.keys()):
        print(f"   {year}年: {year_counts[year]} 个月")


def main():
    parser = argparse.ArgumentParser(
        description='70城房价数据提取工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s month 202507 202511                    # 按月份提取
  %(prog)s month 202507 202511 output.csv         # 指定输出文件名
  %(prog)s month 202507 202511 --fixedbase 环比   # 只提取环比
  %(prog)s city 北京 上海 广州 深圳               # 按城市提取
  %(prog)s city 成都 --output chengdu.csv         # 按城市提取并指定输出
  %(prog)s filter --cities 成都 重庆 --start 202401 --end 202412 --fixedbase 同比,环比  # 组合过滤
  %(prog)s list-cities                            # 列出所有城市
  %(prog)s list-dates                             # 列出日期范围
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # month 子命令
    month_parser = subparsers.add_parser('month', help='按月份范围提取数据')
    month_parser.add_argument('start', help='起始月份 (格式: YYYYMM)')
    month_parser.add_argument('end', help='结束月份 (格式: YYYYMM)')
    month_parser.add_argument('output', nargs='?', help='输出文件名 (可选)')
    month_parser.add_argument('--fixedbase', '-f', help='指数类型过滤 (同比/环比/定基比，支持逗号分隔多个)')
    month_parser.set_defaults(func=cmd_month)
    
    # city 子命令
    city_parser = subparsers.add_parser('city', help='按城市提取数据')
    city_parser.add_argument('cities', nargs='+', help='城市名称列表')
    city_parser.add_argument('--output', '-o', help='输出文件名')
    city_parser.add_argument('--fixedbase', '-f', help='指数类型过滤 (同比/环比/定基比，支持逗号分隔多个)')
    city_parser.set_defaults(func=cmd_city)
    
    # filter 子命令
    filter_parser = subparsers.add_parser('filter', help='组合条件提取数据')
    filter_parser.add_argument('--cities', '-c', nargs='+', help='城市名称列表')
    filter_parser.add_argument('--start', '-s', help='起始月份 (格式: YYYYMM)')
    filter_parser.add_argument('--end', '-e', help='结束月份 (格式: YYYYMM)')
    filter_parser.add_argument('--output', '-o', help='输出文件名')
    filter_parser.add_argument('--fixedbase', '-f', help='指数类型过滤 (同比/环比/定基比，支持逗号分隔多个)')
    filter_parser.set_defaults(func=cmd_filter)
    
    # list-cities 子命令
    list_cities_parser = subparsers.add_parser('list-cities', help='列出所有可用城市')
    list_cities_parser.set_defaults(func=cmd_list_cities)
    
    # list-dates 子命令
    list_dates_parser = subparsers.add_parser('list-dates', help='列出数据日期范围')
    list_dates_parser.set_defaults(func=cmd_list_dates)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        print("\n" + "="*60)
        print(__doc__)
        sys.exit(0)
    
    try:
        args.func(args)
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
