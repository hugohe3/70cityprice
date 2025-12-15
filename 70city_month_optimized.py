import pandas as pd
import os
import re

# --- 配置 ---
# 重要：请将此URL更新为国家统计局发布的最新月度报告链接。
url = "https://www.stats.gov.cn/sj/zxfbhjd/202507/t20250715_1960403.html"

def extract_data_from_tables(tables_to_process, start_row, end_row, columns_order):
    """
    从一个或多个Pandas DataFrame中提取并展平数据。

    参数:
        tables_to_process (list): 需要处理的DataFrame列表。
        start_row (int): 切片的起始行索引。
        end_row (int): 切片的结束行索引。
        columns_order (list): 需要提取数据的列索引顺序。

    返回:
        list: 包含所提取数据的单个展平列表。
    """
    full_list = []
    for col_idx in columns_order:
        for table in tables_to_process:
            full_list.extend(table.iloc[start_row:end_row, col_idx].tolist())
    return full_list

try:
    # --- 1. 数据提取 ---
    print(f"正在从以下链接抓取数据: {url}")
    all_tables = pd.read_html(url)
    print(f"成功从链接中读取 {len(all_tables)} 个表格。")

    # --- 2. 定义提取规则 ---
    # 主要指数 (新建商品住宅和二手住宅)
    main_indices_params = {'start_row': 2, 'end_row': 37, 'columns_order': [1, 5, 2, 6, 3, 7]}
    
    # 按面积分类的指数
    size_indices_params = {'start_row': 3, 'end_row': 38}
    size_columns = {
        'below_90': [1, 2, 3],
        '90_to_144': [4, 5, 6],
        'above_144': [7, 8, 9]
    }

    # --- 3. 执行数据提取 ---
    CommodityHouseIDX = extract_data_from_tables([all_tables[0]], **main_indices_params)
    SecondHandIDX = extract_data_from_tables([all_tables[1]], **main_indices_params)

    CommodityBelow90IDX = extract_data_from_tables([all_tables[2], all_tables[3]], **size_indices_params, columns_order=size_columns['below_90'])
    Commodity144IDX = extract_data_from_tables([all_tables[2], all_tables[3]], **size_indices_params, columns_order=size_columns['90_to_144'])
    CommodityAbove144IDX = extract_data_from_tables([all_tables[2], all_tables[3]], **size_indices_params, columns_order=size_columns['above_144'])

    SecondHandBelow90IDX = extract_data_from_tables([all_tables[4], all_tables[5]], **size_indices_params, columns_order=size_columns['below_90'])
    SecondHand144IDX = extract_data_from_tables([all_tables[4], all_tables[5]], **size_indices_params, columns_order=size_columns['90_to_144'])
    SecondHandAbove144IDX = extract_data_from_tables([all_tables[4], all_tables[5]], **size_indices_params, columns_order=size_columns['above_144'])

    # --- 4. 创建最终DataFrame ---
    final_table = pd.DataFrame({
        'CommodityHouseIDX': CommodityHouseIDX,
        'SecondHandIDX': SecondHandIDX,
        'CommodityBelow90IDX': CommodityBelow90IDX,
        'Commodity144IDX': Commodity144IDX,
        'CommodityAbove144IDX': CommodityAbove144IDX,
        'SecondHandBelow90IDX': SecondHandBelow90IDX,
        'SecondHand144IDX': SecondHand144IDX,
        'SecondHandAbove144IDX': SecondHandAbove144IDX
    })

    # --- 5. 文件输出 ---
    # 从URL动态生成输出文件名
    date_match = re.search(r't(\d{8})', url)
    if date_match:
        date_str = date_match.group(1)
        output_filename = f'final{date_str}.xlsx'
    else:
        # 如果无法从URL解析日期，则使用备用文件名
        output_filename = 'final_data_optimized.xlsx'

    # 确保输出路径是相对于脚本位置的
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, output_filename)

    # 将DataFrame保存到Excel文件
    final_table.to_excel(output_path, index=False)
    print(f"成功将数据保存到: {output_path}")

except Exception as e:
    print(f"处理过程中发生错误: {e}")
