import pandas as pd
import os

url = "https://www.stats.gov.cn/sj/zxfb/202412/t20241216_1957755.html"

# Read all tables at once
tables = pd.read_html(url)

def extract_data(df, start_row, end_row, columns):
    """Helper function to extract and concatenate data from columns"""
    return [val for col in columns for val in df.iloc[start_row:end_row, col]]

# Extract data from tables using helper function
CommodityHouseIDX = extract_data(tables[0], 2, 37, [1, 5, 2, 6, 3, 7])
SecondHandIDX = extract_data(tables[1], 2, 37, [1, 5, 2, 6, 3, 7])

# Extract data for commodity houses by size
size_cols = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
CommodityBelow90IDX = extract_data(tables[2], 3, 38, size_cols[0]) + extract_data(tables[3], 3, 38, size_cols[0])
Commodity144IDX = extract_data(tables[2], 3, 38, size_cols[1]) + extract_data(tables[3], 3, 38, size_cols[1])
CommodityAbove144IDX = extract_data(tables[2], 3, 38, size_cols[2]) + extract_data(tables[3], 3, 38, size_cols[2])

# Extract data for second-hand houses by size 
SecondHandBelow90IDX = extract_data(tables[4], 3, 38, size_cols[0]) + extract_data(tables[5], 3, 38, size_cols[0])
SecondHand144IDX = extract_data(tables[4], 3, 38, size_cols[1]) + extract_data(tables[5], 3, 38, size_cols[1])
SecondHandAbove144IDX = extract_data(tables[4], 3, 38, size_cols[2]) + extract_data(tables[5], 3, 38, size_cols[2])

# Create final dataframe
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
script_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(script_dir, 'final20241216-new.xlsx')
final_table.to_excel(output_path, index=False)
