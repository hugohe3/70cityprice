# -*- coding: utf-8 -*-
"""70城房价工具共享定义。"""

import math
from pathlib import Path
from typing import Optional


REQUIRED_COLUMNS = [
    'DATE', 'ADCODE', 'CITY', 'FixedBase', 'HouseIDX', 'ResidentIDX',
    'CommodityHouseIDX', 'SecondHandIDX', 'ResidentBelow90IDX',
    'CommonResidentBelow90IDX', 'CommodityBelow90IDX', 'Commodity144IDX',
    'CommodityAbove144IDX', 'SecondHandBelow90IDX', 'SecondHand144IDX',
    'SecondHandAbove144IDX'
]

ALLOWED_FIXED_BASES = {'同比', '环比', '定基比'}
REQUIRED_FIXED_BASES = {'同比', '环比'}
NUMERIC_COLUMNS = [
    'HouseIDX', 'ResidentIDX', 'CommodityHouseIDX', 'SecondHandIDX',
    'ResidentBelow90IDX', 'CommonResidentBelow90IDX', 'CommodityBelow90IDX',
    'Commodity144IDX', 'CommodityAbove144IDX', 'SecondHandBelow90IDX',
    'SecondHand144IDX', 'SecondHandAbove144IDX'
]

# 70个城市的ADCODE映射
CITY_ADCODE = {
    '北京': '110100', '天津': '120100', '石家庄': '130100', '太原': '140100',
    '呼和浩特': '150100', '沈阳': '210100', '大连': '210200', '长春': '220100',
    '哈尔滨': '230100', '上海': '310100', '南京': '320100', '杭州': '330100',
    '宁波': '330200', '合肥': '340100', '福州': '350100', '厦门': '350200',
    '南昌': '360100', '济南': '370100', '青岛': '370200', '郑州': '410100',
    '武汉': '420100', '长沙': '430100', '广州': '440100', '深圳': '440300',
    '南宁': '450100', '海口': '460100', '重庆': '500100', '成都': '510100',
    '贵阳': '520100', '昆明': '530100', '西安': '610100', '兰州': '620100',
    '西宁': '630100', '银川': '640100', '乌鲁木齐': '650100',
    '唐山': '130200', '秦皇岛': '130300', '包头': '150200', '丹东': '210600',
    '锦州': '210700', '吉林': '220200', '牡丹江': '231000', '无锡': '320200',
    '徐州': '320300', '扬州': '321000', '温州': '330300', '金华': '330700',
    '蚌埠': '340300', '安庆': '340800', '泉州': '350500', '九江': '360400',
    '赣州': '360700', '烟台': '370600', '济宁': '370800', '洛阳': '410300',
    '平顶山': '410400', '宜昌': '420500', '襄阳': '420600', '岳阳': '430600',
    '常德': '430700', '韶关': '440200', '湛江': '440800', '惠州': '441300',
    '桂林': '450300', '北海': '450500', '三亚': '460200', '泸州': '510500',
    '南充': '511300', '遵义': '520300', '大理': '532900'
}

# 静态城市页的 URL slug。一旦发布就不要改动——改了等于换 URL，
# 已被收录的页面和别人分享出去的链接都会失效。
CITY_SLUG = {
    '北京': 'beijing', '天津': 'tianjin', '石家庄': 'shijiazhuang',
    '太原': 'taiyuan', '呼和浩特': 'huhehaote', '沈阳': 'shenyang',
    '大连': 'dalian', '长春': 'changchun', '哈尔滨': 'haerbin',
    '上海': 'shanghai', '南京': 'nanjing', '杭州': 'hangzhou',
    '宁波': 'ningbo', '合肥': 'hefei', '福州': 'fuzhou', '厦门': 'xiamen',
    '南昌': 'nanchang', '济南': 'jinan', '青岛': 'qingdao',
    '郑州': 'zhengzhou', '武汉': 'wuhan', '长沙': 'changsha',
    '广州': 'guangzhou', '深圳': 'shenzhen', '南宁': 'nanning',
    '海口': 'haikou', '重庆': 'chongqing', '成都': 'chengdu',
    '贵阳': 'guiyang', '昆明': 'kunming', '西安': 'xian',
    '兰州': 'lanzhou', '西宁': 'xining', '银川': 'yinchuan',
    '乌鲁木齐': 'wulumuqi', '唐山': 'tangshan', '秦皇岛': 'qinhuangdao',
    '包头': 'baotou', '丹东': 'dandong', '锦州': 'jinzhou',
    '吉林': 'jilin', '牡丹江': 'mudanjiang', '无锡': 'wuxi',
    '徐州': 'xuzhou', '扬州': 'yangzhou', '温州': 'wenzhou',
    '金华': 'jinhua', '蚌埠': 'bengbu', '安庆': 'anqing',
    '泉州': 'quanzhou', '九江': 'jiujiang', '赣州': 'ganzhou',
    '烟台': 'yantai', '济宁': 'jining', '洛阳': 'luoyang',
    '平顶山': 'pingdingshan', '宜昌': 'yichang', '襄阳': 'xiangyang',
    '岳阳': 'yueyang', '常德': 'changde', '韶关': 'shaoguan',
    '湛江': 'zhanjiang', '惠州': 'huizhou', '桂林': 'guilin',
    '北海': 'beihai', '三亚': 'sanya', '泸州': 'luzhou',
    '南充': 'nanchong', '遵义': 'zunyi', '大理': 'dali',
}

CITY_NAME_ALIASES = {
    '大理白族自治州': '大理',
    '大理自治州': '大理',
    '大理市': '大理',
}

CITY_STANDARD_NAME = {city: city for city in CITY_ADCODE}
CITY_SUFFIXES = ('自治州', '地区', '盟', '市')


def get_repo_root() -> Path:
    """获取仓库根目录。"""
    return Path(__file__).resolve().parent.parent


def get_csv_path() -> Path:
    """获取主CSV文件路径。"""
    return get_repo_root() / '70cityprice.csv'


def normalize_city_name(name: object, strip_suffix: bool = True) -> str:
    """标准化城市名称。"""
    if name is None:
        return ''
    if isinstance(name, float) and math.isnan(name):
        return ''

    normalized = str(name).replace(' ', '').replace('\u3000', '').strip()
    if not normalized or normalized.lower() == 'nan':
        return ''

    normalized = CITY_NAME_ALIASES.get(normalized, normalized)
    if strip_suffix:
        for suffix in CITY_SUFFIXES:
            if normalized.endswith(suffix):
                return normalized[:-len(suffix)]
    return normalized


def get_city_adcode(city_name: object) -> Optional[str]:
    """获取城市ADCODE。"""
    normalized = normalize_city_name(city_name)
    if not normalized:
        return None
    if normalized in CITY_ADCODE:
        return CITY_ADCODE[normalized]

    for key, adcode in CITY_ADCODE.items():
        if normalized in key or key in normalized:
            return adcode

    print(f"警告: 未找到城市 '{city_name}' 的ADCODE")
    return None


def get_standard_city_name(city_name: object, warn_if_missing: bool = False) -> Optional[str]:
    """获取标准输出城市名。"""
    normalized = normalize_city_name(city_name)
    if not normalized:
        return None
    if normalized in CITY_STANDARD_NAME:
        return CITY_STANDARD_NAME[normalized]

    for key, standard_name in CITY_STANDARD_NAME.items():
        if normalized in key or key in normalized:
            return standard_name

    if warn_if_missing:
        print(f"警告: 未找到城市 '{city_name}' 的标准名称")
    return None


def standardize_city_column(city_name: object) -> object:
    """标准化CITY列值，未命中时保留清理后的原值。"""
    standard_name = get_standard_city_name(city_name, warn_if_missing=False)
    if standard_name:
        return standard_name
    if city_name is None or (isinstance(city_name, float) and math.isnan(city_name)):
        return city_name
    return str(city_name).strip()
