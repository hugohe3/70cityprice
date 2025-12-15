# -*- coding: utf-8 -*-
"""
70城房价数据提取工具
用于从70cityprice.csv中提取指定月份范围的数据

使用方法:
    python extract_70cityprice.py <起始月份> <结束月份> [输出文件名]
    
例如:
    python extract_70cityprice.py 202507 202511
    python extract_70cityprice.py 202507 202511 output.csv
    
日期格式: YYYYMM (例如: 202507 表示2025年7月)
"""

import pandas as pd
import os
import sys
from datetime import datetime


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
    except:
        return None


def extract_data(csv_path, start_year, start_month, end_year, end_month, output_path=None):
    """
    提取指定月份范围的数据
    
    参数:
        csv_path: CSV文件路径
        start_year, start_month: 起始年月
        end_year, end_month: 结束年月
        output_path: 输出文件路径（可选）
    
    返回:
        提取的DataFrame
    """
    print(f"正在读取数据文件: {csv_path}")
    df = pd.read_csv(csv_path, dtype=str)
    total_records = len(df)
    print(f"总记录数: {total_records}")
    
    # 转换日期范围为可比较格式
    start_tuple = (start_year, start_month)
    end_tuple = (end_year, end_month)
    
    print(f"提取范围: {start_year}年{start_month}月 至 {end_year}年{end_month}月")
    
    # 筛选数据
    def in_range(date_str):
        date_tuple = date_to_comparable(date_str)
        if date_tuple is None:
            return False
        return start_tuple <= date_tuple <= end_tuple
    
    mask = df['DATE'].apply(in_range)
    extracted_df = df[mask].copy()
    
    extracted_records = len(extracted_df)
    print(f"提取到 {extracted_records} 条记录")
    
    if extracted_records == 0:
        print("警告: 未找到符合条件的数据")
        # 显示可用的日期范围
        all_dates = df['DATE'].apply(date_to_comparable).dropna().unique()
        if len(all_dates) > 0:
            min_date = min(all_dates)
            max_date = max(all_dates)
            print(f"可用数据范围: {min_date[0]}年{min_date[1]}月 至 {max_date[0]}年{max_date[1]}月")
    else:
        # 统计提取的月份
        months = extracted_df['DATE'].apply(date_to_comparable).unique()
        months_sorted = sorted(months)
        print(f"提取的月份: {', '.join([f'{m[0]}/{m[1]}' for m in months_sorted])}")
        
        # 统计城市数量
        cities = extracted_df['CITY'].unique()
        print(f"涉及城市数: {len(cities)}")
    
    # 保存到文件
    if output_path:
        # 确保列顺序与原文件一致
        extracted_df.to_csv(output_path, index=False, quoting=1)
        print(f"\n✅ 数据已保存到: {output_path}")
    
    return extracted_df


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\n示例:")
        print("  python extract_70cityprice.py 202507 202511")
        print("  python extract_70cityprice.py 202507 202511 my_data.csv")
        print("  python extract_70cityprice.py 2024-01 2024-12")
        sys.exit(1)
    
    start_month_arg = sys.argv[1]
    end_month_arg = sys.argv[2]
    
    # 解析月份参数
    try:
        start_year, start_month = parse_month_arg(start_month_arg)
        end_year, end_month = parse_month_arg(end_month_arg)
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)
    
    # 验证日期范围
    if (start_year, start_month) > (end_year, end_month):
        print("错误: 起始月份不能晚于结束月份")
        sys.exit(1)
    
    # 确定输出文件名
    if len(sys.argv) >= 4:
        output_filename = sys.argv[3]
    else:
        # 自动生成文件名
        output_filename = f"70cityprice_{start_year}{start_month:02d}_{end_year}{end_month:02d}.csv"
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, '70cityprice.csv')
    output_path = os.path.join(script_dir, output_filename)
    
    if not os.path.exists(csv_path):
        print(f"错误: CSV文件不存在: {csv_path}")
        sys.exit(1)
    
    try:
        extract_data(csv_path, start_year, start_month, end_year, end_month, output_path)
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
