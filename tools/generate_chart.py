#!/usr/bin/env python3
"""生成北上广深近10年房价走势图"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def main():
    # 读取数据
    script_dir = Path(__file__).parent
    csv_path = script_dir.parent / '70cityprice.csv'
    df = pd.read_csv(csv_path)
    
    # 转换日期
    df['DATE'] = pd.to_datetime(df['DATE'])
    
    # 筛选条件：2015年至今，北上广深，同比数据
    cities = ['北京市', '上海市', '广州市', '深圳市']
    start_date = '2015-01-01'
    
    mask = (
        (df['CITY'].isin(cities)) & 
        (df['FixedBase'] == '同比') & 
        (df['DATE'] >= start_date)
    )
    data = df[mask].copy()
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    
    colors = {
        '北京市': '#E53935',
        '上海市': '#1E88E5', 
        '广州市': '#43A047',
        '深圳市': '#FB8C00'
    }
    
    for city in cities:
        city_data = data[data['CITY'] == city].sort_values('DATE')
        ax.plot(city_data['DATE'], city_data['CommodityHouseIDX'], 
                label=city.replace('市', ''), color=colors[city], linewidth=1.5)
    
    # 添加基准线（100 = 与上年同期持平）
    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    
    # 美化图表
    ax.set_title('北上广深新建商品住宅价格指数（同比）', fontsize=16, fontweight='bold', pad=15)
    ax.set_xlabel('')
    ax.set_ylabel('价格指数（上年同期=100）', fontsize=11)
    ax.legend(loc='upper right', framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(85, 170)
    
    # 添加数据来源
    ax.text(0.02, 0.02, '数据来源：国家统计局', transform=ax.transAxes, 
            fontsize=9, color='gray', alpha=0.7)
    
    plt.tight_layout()
    
    # 保存图片
    output_path = script_dir.parent / 'assets' / 'price_trend.png'
    output_path.parent.mkdir(exist_ok=True)
    plt.savefig(output_path, bbox_inches='tight', facecolor='white')
    print(f'图表已保存至: {output_path}')

if __name__ == '__main__':
    main()
