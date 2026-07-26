# -*- coding: utf-8 -*-
"""
70城房价数据更新工具
用于将国家统计局发布的70城房价数据追加到现有CSV数据表中

使用方法:
    python3 update_70cityprice.py <URL>

例如:
    python3 update_70cityprice.py "https://www.stats.gov.cn/sj/zxfb/202601/t20260119_1962319.html"
"""

import re
import sys
import pandas as pd

from common import (
    REQUIRED_COLUMNS,
    get_city_adcode,
    get_csv_path,
    get_standard_city_name,
    normalize_city_name,
    standardize_city_column,
)

def parse_date_from_url(url):
    """从URL中解析日期"""
    # 尝试从URL中提取日期 (格式: t20250715 或 202507)
    match = re.search(r't(\d{8})', url)
    if match:
        date_str = match.group(1)
        year = int(date_str[:4])
        month = int(date_str[4:6])
        return year, month
    
    match = re.search(r'/(\d{6})/', url)
    if match:
        date_str = match.group(1)
        year = int(date_str[:4])
        month = int(date_str[4:6])
        return year, month
    
    return None, None

def parse_date_from_title(tables):
    """从表格标题中解析日期"""
    for table in tables:
        if table.empty:
            continue
        first_row = table.iloc[0].astype(str)
        for cell in first_row:
            match = re.search(r'(\d{4})年(\d{1,2})月', str(cell))
            if match:
                return int(match.group(1)), int(match.group(2))
    return None, None

def extract_cities_from_table(table, start_row, end_row, city_col=0):
    """从表格中提取城市列表"""
    cities = []
    for i in range(start_row, end_row):
        if i < len(table):
            city = str(table.iloc[i, city_col]).strip()
            normalized = normalize_city_name(city)
            if normalized and normalized != 'nan':
                cities.append(normalized)
    return cities

def fetch_data_from_url(url):
    """从URL抓取数据"""
    print(f"正在从以下链接抓取数据: {url}")
    tables = pd.read_html(url)
    print(f"成功读取 {len(tables)} 个表格")
    return tables

def parse_main_index_table(table, start_row=2, end_row=37, is_january=False):
    """
    解析主指数表格 (表1和表2)
    返回: dict{城市: {类型: 值}}
    
    参数:
        is_january: 是否为1月份数据，1月份没有年度平均列
    """
    data = {}
    
    # 检测表格列数来判断是否有年度平均列
    # 1月份: 城市 | 环比 | 同比 | 城市 | 环比 | 同比 (6列或更少)
    # 其他月份: 城市 | 环比 | 同比 | 年度平均 | 城市 | 环比 | 同比 | 年度平均 (8列)
    
    sample_row = table.iloc[start_row] if len(table) > start_row else None
    if sample_row is not None:
        num_cols = len(sample_row)
        # 如果每侧只有3列（城市+环比+同比），则没有年度平均
        has_avg = num_cols > 6 or (not is_january and num_cols > 4)
    else:
        has_avg = not is_january
    
    for i in range(start_row, min(end_row, len(table))):
        row = table.iloc[i]
        
        # 左侧城市
        city1 = normalize_city_name(str(row.iloc[0]))
        if city1 and city1 != 'nan':
            if has_avg:
                # 有年度平均列: 城市 | 环比 | 同比 | 年度平均
                data[city1] = {
                    '环比': row.iloc[1] if pd.notna(row.iloc[1]) else None,
                    '同比': row.iloc[2] if pd.notna(row.iloc[2]) else None,
                    '定基比': row.iloc[3] if pd.notna(row.iloc[3]) else None
                }
            else:
                # 无年度平均列（1月份）: 城市 | 环比 | 同比，定基比=同比
                tongbi_val = row.iloc[2] if pd.notna(row.iloc[2]) else None
                data[city1] = {
                    '环比': row.iloc[1] if pd.notna(row.iloc[1]) else None,
                    '同比': tongbi_val,
                    '定基比': tongbi_val  # 1月份定基比等于同比
                }
        
        # 右侧城市 (如果存在)
        right_start = 4 if has_avg else 3
        if len(row) > right_start:
            city2 = normalize_city_name(str(row.iloc[right_start]))
            if city2 and city2 != 'nan':
                if has_avg:
                    data[city2] = {
                        '环比': row.iloc[right_start + 1] if pd.notna(row.iloc[right_start + 1]) else None,
                        '同比': row.iloc[right_start + 2] if pd.notna(row.iloc[right_start + 2]) else None,
                        '定基比': row.iloc[right_start + 3] if len(row) > right_start + 3 and pd.notna(row.iloc[right_start + 3]) else None
                    }
                else:
                    tongbi_val = row.iloc[right_start + 2] if len(row) > right_start + 2 and pd.notna(row.iloc[right_start + 2]) else None
                    data[city2] = {
                        '环比': row.iloc[right_start + 1] if len(row) > right_start + 1 and pd.notna(row.iloc[right_start + 1]) else None,
                        '同比': tongbi_val,
                        '定基比': tongbi_val  # 1月份定基比等于同比
                    }
    
    return data

def parse_size_index_table(table, start_row=3, end_row=38, is_january=False):
    """
    解析分类指数表格 (表3和表4)
    返回: dict{城市: {面积类型: {指数类型: 值}}}
    
    参数:
        is_january: 是否为1月份数据，1月份没有年度平均列
    """
    data = {}
    
    # 检测表格列数来判断是否有年度平均列
    # 1月份: 城市 | 90m²以下(环比|同比) | 90-144m²(环比|同比) | 144m²以上(环比|同比) = 7列
    # 其他月份: 城市 | 90m²以下(环比|同比|年度平均) | ... = 10列
    
    sample_row = table.iloc[start_row] if len(table) > start_row else None
    if sample_row is not None:
        num_cols = len(sample_row)
        # 如果总列数少于10列，则没有年度平均
        has_avg = num_cols >= 10
    else:
        has_avg = not is_january
    
    for i in range(start_row, min(end_row, len(table))):
        row = table.iloc[i]
        
        city = normalize_city_name(str(row.iloc[0]))
        if city and city != 'nan':
            if has_avg:
                # 有年度平均列: 城市 | 90m²以下(环比|同比|年度平均) | 90-144m²(环比|同比|年度平均) | 144m²以上(环比|同比|年度平均)
                data[city] = {
                    'Below90': {
                        '环比': row.iloc[1] if pd.notna(row.iloc[1]) else None,
                        '同比': row.iloc[2] if pd.notna(row.iloc[2]) else None,
                        '定基比': row.iloc[3] if pd.notna(row.iloc[3]) else None
                    },
                    '144': {
                        '环比': row.iloc[4] if pd.notna(row.iloc[4]) else None,
                        '同比': row.iloc[5] if pd.notna(row.iloc[5]) else None,
                        '定基比': row.iloc[6] if pd.notna(row.iloc[6]) else None
                    },
                    'Above144': {
                        '环比': row.iloc[7] if pd.notna(row.iloc[7]) else None,
                        '同比': row.iloc[8] if pd.notna(row.iloc[8]) else None,
                        '定基比': row.iloc[9] if pd.notna(row.iloc[9]) else None
                    }
                }
            else:
                # 无年度平均列（1月份）: 城市 | 90m²以下(环比|同比) | 90-144m²(环比|同比) | 144m²以上(环比|同比)
                tongbi_90 = row.iloc[2] if len(row) > 2 and pd.notna(row.iloc[2]) else None
                tongbi_144 = row.iloc[4] if len(row) > 4 and pd.notna(row.iloc[4]) else None
                tongbi_above = row.iloc[6] if len(row) > 6 and pd.notna(row.iloc[6]) else None
                
                data[city] = {
                    'Below90': {
                        '环比': row.iloc[1] if len(row) > 1 and pd.notna(row.iloc[1]) else None,
                        '同比': tongbi_90,
                        '定基比': tongbi_90  # 1月份定基比等于同比
                    },
                    '144': {
                        '环比': row.iloc[3] if len(row) > 3 and pd.notna(row.iloc[3]) else None,
                        '同比': tongbi_144,
                        '定基比': tongbi_144  # 1月份定基比等于同比
                    },
                    'Above144': {
                        '环比': row.iloc[5] if len(row) > 5 and pd.notna(row.iloc[5]) else None,
                        '同比': tongbi_above,
                        '定基比': tongbi_above  # 1月份定基比等于同比
                    }
                }
    
    return data

def process_tables(tables, is_january=False):
    """
    处理所有表格，提取数据
    
    参数:
        is_january: 是否为1月份数据，1月份没有年度平均列
    """
    if len(tables) < 6:
        raise ValueError(f"预期至少6个表格，实际只有 {len(tables)} 个")
    
    # 表1: 新建商品住宅销售价格指数
    commodity_main = parse_main_index_table(tables[0], is_january=is_january)
    
    # 表2: 二手住宅销售价格指数
    secondhand_main = parse_main_index_table(tables[1], is_january=is_january)
    
    # 表3(一)(二): 新建商品住宅分类指数
    commodity_size_1 = parse_size_index_table(tables[2], is_january=is_january)
    commodity_size_2 = parse_size_index_table(tables[3], is_january=is_january)
    commodity_size = {**commodity_size_1, **commodity_size_2}
    
    # 表4(一)(二): 二手住宅分类指数
    secondhand_size_1 = parse_size_index_table(tables[4], is_january=is_january)
    secondhand_size_2 = parse_size_index_table(tables[5], is_january=is_january)
    secondhand_size = {**secondhand_size_1, **secondhand_size_2}
    
    return commodity_main, secondhand_main, commodity_size, secondhand_size

def create_records(date_str, commodity_main, secondhand_main, commodity_size, secondhand_size):
    """创建CSV记录"""
    records = []
    
    # 获取所有城市
    all_cities = set(commodity_main.keys()) | set(secondhand_main.keys()) | \
                 set(commodity_size.keys()) | set(secondhand_size.keys())
    
    for city in all_cities:
        adcode = get_city_adcode(city)
        if not adcode:
            continue
        
        city_name = get_standard_city_name(city, warn_if_missing=False) or city
        
        # 为每种指数类型创建记录
        for idx_type in ['同比', '环比', '定基比']:
            record = {
                'DATE': date_str,
                'ADCODE': adcode,
                'CITY': city_name,
                'FixedBase': idx_type,
                'HouseIDX': '',
                'ResidentIDX': '',
                'CommodityHouseIDX': '',
                'SecondHandIDX': '',
                'ResidentBelow90IDX': '',
                'CommonResidentBelow90IDX': '',
                'CommodityBelow90IDX': '',
                'Commodity144IDX': '',
                'CommodityAbove144IDX': '',
                'SecondHandBelow90IDX': '',
                'SecondHand144IDX': '',
                'SecondHandAbove144IDX': ''
            }
            
            # 填充主指数
            if city in commodity_main and commodity_main[city].get(idx_type):
                record['CommodityHouseIDX'] = commodity_main[city][idx_type]
            
            if city in secondhand_main and secondhand_main[city].get(idx_type):
                record['SecondHandIDX'] = secondhand_main[city][idx_type]
            
            # 填充分类指数
            if city in commodity_size:
                size_data = commodity_size[city]
                if size_data.get('Below90', {}).get(idx_type):
                    record['CommodityBelow90IDX'] = size_data['Below90'][idx_type]
                if size_data.get('144', {}).get(idx_type):
                    record['Commodity144IDX'] = size_data['144'][idx_type]
                if size_data.get('Above144', {}).get(idx_type):
                    record['CommodityAbove144IDX'] = size_data['Above144'][idx_type]
            
            if city in secondhand_size:
                size_data = secondhand_size[city]
                if size_data.get('Below90', {}).get(idx_type):
                    record['SecondHandBelow90IDX'] = size_data['Below90'][idx_type]
                if size_data.get('144', {}).get(idx_type):
                    record['SecondHand144IDX'] = size_data['144'][idx_type]
                if size_data.get('Above144', {}).get(idx_type):
                    record['SecondHandAbove144IDX'] = size_data['Above144'][idx_type]
            
            # 只添加有数据的记录
            has_data = any([
                record['CommodityHouseIDX'], record['SecondHandIDX'],
                record['CommodityBelow90IDX'], record['Commodity144IDX'],
                record['CommodityAbove144IDX'], record['SecondHandBelow90IDX'],
                record['SecondHand144IDX'], record['SecondHandAbove144IDX']
            ])
            
            if has_data:
                records.append(record)
    
    return records

def update_csv(csv_path, new_records):
    """更新CSV文件"""
    # 读取现有CSV
    existing_df = pd.read_csv(csv_path, dtype=str, encoding='utf-8-sig')
    existing_df['CITY'] = existing_df['CITY'].apply(standardize_city_column)
    print(f"现有数据: {len(existing_df)} 条记录")
    
    # 创建新数据DataFrame
    new_df = pd.DataFrame(new_records)
    if 'CITY' in new_df.columns:
        new_df['CITY'] = new_df['CITY'].apply(standardize_city_column)
    
    # 获取新数据的日期
    if len(new_records) > 0:
        new_date = new_records[0]['DATE']
        
        # 检查是否已存在该月份的数据
        existing_dates = existing_df['DATE'].unique()
        if new_date in existing_dates:
            print(f"警告: {new_date} 的数据已存在，将替换现有数据")
            existing_df = existing_df[existing_df['DATE'] != new_date]
    
    # 合并数据
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    
    # 确保列顺序一致
    combined_df = combined_df[REQUIRED_COLUMNS]
    
    # 排序
    combined_df['DATE_SORT'] = pd.to_datetime(combined_df['DATE'], format='%Y/%m/%d', errors='coerce')
    combined_df = combined_df.sort_values(['CITY', 'DATE_SORT', 'FixedBase'])
    combined_df = combined_df.drop('DATE_SORT', axis=1)
    
    # 保存（使用引号包裹所有字段，与原始格式一致）
    combined_df.to_csv(csv_path, index=False, quoting=1, encoding='utf-8-sig')  # quoting=1 是 csv.QUOTE_ALL
    print(f"更新后数据: {len(combined_df)} 条记录")
    print(f"新增 {len(new_records)} 条记录")

def main():
    if len(sys.argv) < 2:
        print("使用方法: python3 update_70cityprice.py <URL>")
        print("例如: python3 update_70cityprice.py 'https://www.stats.gov.cn/sj/zxfb/202601/t20260119_1962319.html'")
        sys.exit(1)
    
    url = sys.argv[1]
    
    csv_path = get_csv_path()
    
    if not csv_path.exists():
        print(f"错误: CSV文件不存在: {csv_path}")
        sys.exit(1)
    
    try:
        # 抓取数据
        tables = fetch_data_from_url(url)
        
        # 解析日期
        year, month = parse_date_from_url(url)
        if not year:
            year, month = parse_date_from_title(tables)
        
        if not year:
            print("错误: 无法从URL或表格中解析日期")
            print("请检查URL格式是否正确")
            sys.exit(1)
        
        # 数据日期通常是URL发布月份的上一个月
        # 例如: 202507发布的是2025年6月的数据
        data_month = month - 1
        data_year = year
        if data_month == 0:
            data_month = 12
            data_year -= 1
        
        date_str = f"{data_year}/{data_month}/1"
        print(f"数据日期: {date_str}")
        
        # 检查是否为1月份数据
        is_january = (data_month == 1)
        if is_january:
            print("提示: 1月份数据，定基比将使用同比数据")
        
        # 处理表格
        commodity_main, secondhand_main, commodity_size, secondhand_size = process_tables(tables, is_january=is_january)
        
        print(f"解析到 {len(commodity_main)} 个城市的新建商品住宅数据")
        print(f"解析到 {len(secondhand_main)} 个城市的二手住宅数据")
        
        # 创建记录
        records = create_records(date_str, commodity_main, secondhand_main, 
                                 commodity_size, secondhand_size)
        
        print(f"生成 {len(records)} 条新记录")
        if not records:
            raise ValueError("未生成任何新记录，请检查页面表格结构或URL是否匹配70城房价发布页")
        
        # 更新CSV
        update_csv(csv_path, records)
        
        print("\n✅ 数据更新完成!")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
