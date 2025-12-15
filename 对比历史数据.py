import pandas as pd
import numpy as np
import os
print(os.getcwd())  # 显示当前工作目录

# 读取两个文件
df1 = pd.read_excel('final20241216.xlsx')
df2 = pd.read_excel('final20241216-new.xlsx')

# 检查基本信息
print("文件1的形状:", df1.shape)
print("文件2的形状:", df2.shape)

# 检查是否完全相同
is_identical = df1.equals(df2)
print("\n文件是否完全相同:", is_identical)

# 如果不相同，找出不同的行
if not is_identical:
    # 找出不同值的位置
    diff_mask = (df1 != df2).any(axis=1)
    diff_rows = df1[diff_mask].index
    
    print("\n发现不同的行数:", len(diff_rows))
    
    # 显示前5个不同的行的对比
    if len(diff_rows) > 0:
        print("\n前5个不同行的对比示例:")
        for idx in diff_rows[:5]:
            print(f"\n行号 {idx}:")
            print("文件1:", df1.iloc[idx].to_list())
            print("文件2:", df2.iloc[idx].to_list())