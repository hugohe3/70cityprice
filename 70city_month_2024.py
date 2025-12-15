import pandas as pd

url = "https://www.stats.gov.cn/sj/zxfb/202502/t20250219_1958761.html"

table = pd.read_html(url)
table1 = table[0]
table2 = table[1]
table3 = table[2]
table4 = table[3]
table5 = table[4]
table6 = table[5]

CommodityHouseIDX = list(table1.iloc[2:37, 1]) + list(table1.iloc[2:37, 4]) + list(table1.iloc[2:37, 2]) + list(
    table1.iloc[2:37, 5])
SecondHandIDX = list(table2.iloc[2:37, 1]) + list(table2.iloc[2:37, 4]) + list(table2.iloc[2:37, 2]) + list(
    table2.iloc[2:37, 5])
CommodityBelow90IDX = list(table3.iloc[3:38, 1]) + list(table4.iloc[3:38, 1]) + list(table3.iloc[3:38, 2]) + list(
    table4.iloc[3:38, 2])
Commodity144IDX = list(table3.iloc[3:38, 3]) + list(table4.iloc[3:38, 3]) + list(table3.iloc[3:38, 4]) + list(
    table4.iloc[3:38, 4])
CommodityAbove144IDX = list(table3.iloc[3:38, 5]) + list(table4.iloc[3:38, 5]) + list(table3.iloc[3:38, 6]) + list(
    table4.iloc[3:38, 6])
SecondHandBelow90IDX = list(table5.iloc[3:38, 1]) + list(table6.iloc[3:38, 1]) + list(table5.iloc[3:38, 2]) + list(
    table6.iloc[3:38, 2])
SecondHand144IDX = list(table5.iloc[3:38, 3]) + list(table6.iloc[3:38, 3]) + list(table5.iloc[3:38, 4]) + list(
    table6.iloc[3:38, 4])
SecondHandAbove144IDX = list(table5.iloc[3:38, 5]) + list(table6.iloc[3:38, 5]) + list(table5.iloc[3:38, 6]) + list(
    table6.iloc[3:38, 6])
final_table = pd.DataFrame(
    {'CommodityHouseIDX': CommodityHouseIDX, 'SecondHandIDX': SecondHandIDX, 'CommodityBelow90IDX': CommodityBelow90IDX,
     'Commodity144IDX': Commodity144IDX, 'CommodityAbove144IDX': CommodityAbove144IDX,
     'SecondHandBelow90IDX': SecondHandBelow90IDX,
     'SecondHand144IDX': SecondHand144IDX, 'SecondHandAbove144IDX': SecondHandAbove144IDX})
final_table.to_excel('final20250219.xlsx', index=False)
