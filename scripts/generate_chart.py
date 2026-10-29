#!/usr/bin/env python3
"""生成北上广深近10年房价走势图"""

import math

import pandas as pd
import matplotlib.pyplot as plt

from common import find_cjk_fonts, get_csv_path, get_repo_root

# 纵轴默认范围，保持历年配图观感一致；数据超出时再向外扩
DEFAULT_YLIM = (85, 170)

def main():
    # 设置中文字体（找不到就报错，而不是画出豆腐块）
    plt.rcParams['font.sans-serif'] = find_cjk_fonts()
    plt.rcParams['axes.unicode_minus'] = False

    # 读取数据
    df = pd.read_csv(get_csv_path())
    
    # 转换日期
    df['DATE'] = pd.to_datetime(df['DATE'])
    
    # 筛选条件：2015年至今，北上广深，同比数据
    cities = ['北京', '上海', '广州', '深圳']
    start_date = '2015-01-01'
    
    mask = (
        (df['CITY'].isin(cities)) & 
        (df['FixedBase'] == '同比') & 
        (df['DATE'] >= start_date)
    )
    data = df[mask].copy()
    data['CommodityHouseIDX'] = pd.to_numeric(data['CommodityHouseIDX'], errors='coerce')
    data = data.dropna(subset=['CommodityHouseIDX'])
    if data.empty:
        raise ValueError('未找到可用于绘图的新建商品住宅同比数据')
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    
    colors = {
        '北京': '#E53935',
        '上海': '#1E88E5',
        '广州': '#43A047',
        '深圳': '#FB8C00'
    }
    
    for city in cities:
        city_data = data[data['CITY'] == city].sort_values('DATE')
        ax.plot(city_data['DATE'], city_data['CommodityHouseIDX'], 
                label=city, color=colors[city], linewidth=1.5)
    
    # 添加基准线（100 = 与上年同期持平）
    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    
    # 美化图表
    ax.set_title('北上广深新建商品住宅价格指数（同比）', fontsize=16, fontweight='bold', pad=15)
    ax.set_xlabel('')
    ax.set_ylabel('价格指数（上年同期=100）', fontsize=11)
    ax.legend(loc='upper right', framealpha=0.9)
    ax.grid(True, alpha=0.3)
    low = min(DEFAULT_YLIM[0], math.floor(data['CommodityHouseIDX'].min()) - 2)
    high = max(DEFAULT_YLIM[1], math.ceil(data['CommodityHouseIDX'].max()) + 2)
    ax.set_ylim(low, high)
    
    # 添加数据来源
    ax.text(0.02, 0.02, '数据来源：国家统计局', transform=ax.transAxes, 
            fontsize=9, color='gray', alpha=0.7)
    
    plt.tight_layout()
    
    # 保存图片
    output_path = get_repo_root() / 'assets' / 'price_trend.png'
    output_path.parent.mkdir(exist_ok=True)
    plt.savefig(output_path, bbox_inches='tight', facecolor='white')
    print(f'图表已保存至: {output_path}')

if __name__ == '__main__':
    main()
