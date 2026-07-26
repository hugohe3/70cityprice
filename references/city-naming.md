# 城市命名口径

## 权威清单

[`scripts/common.py`](../scripts/common.py) 里的 `CITY_ADCODE` 是**唯一权威城市清单**：70 个城市，键为规范名（无「市」后缀），值为行政区划代码。

规范名口径 = 国家统计局当前发布写法：`北京`（非「北京市」）、`大理`（非「大理白族自治州」）。

## 强制标准化链路

任何外部输入的城市名——从发布页抓下来的、`--cities` 参数传进来的、用户在对话里写的——都必须先经过：

```python
from common import normalize_city_name, get_standard_city_name

standard = get_standard_city_name(normalize_city_name(raw_name))
```

- `normalize_city_name(name, strip_suffix=True)` —— 清理空白、去除「市」等后缀
- `get_standard_city_name(city_name, warn_if_missing=False)` —— 映射到 `CITY_ADCODE` 的规范键，映射不到返回 `None`
- `standardize_city_column(city_name)` —— 上述链路的列级封装，供 DataFrame 的 `.apply()` 使用

**禁止直接字符串比较城市名。** 绕过这条链路会立刻产生「北京 / 北京市」「大理 / 大理白族自治州」这类重复键，污染主键并让校验脚本的 70 城覆盖检查失效。涉及城市名的新代码走同一条路径。

## 兼容性边界

- **存储口径**：CSV 的 `CITY` 列只存规范名，由 `update_70cityprice.py` 在写回前统一标准化。
- **输入口径**：`extract_70cityprice.py` 兼容常见旧写法（带「市」后缀、自治州全称），因为它对参数跑了同一条标准化链路。
- **旧导出文件**：用户手里可能有带「市」后缀的历史导出。判断口径是否一致跑 `python3 scripts/validate_70cityprice.py`，不要手工 sed 替换。

## 新增或更名城市

若官方调整了城市清单，改动顺序是：

1. 更新 `common.py` 的 `CITY_ADCODE`（这是唯一定义处）
2. 若涉及更名，在 `normalize_city_name` 里补上旧名到新名的映射，保证历史数据仍能查到
3. 跑校验确认 70 城覆盖检查通过
4. 同步 [`README.md`](../README.md) 的城市列表章节

不要在多处硬编码城市清单。`validate_70cityprice.py` 和 `build_site_data.py` 都从 `common.py` 导入 `CITY_ADCODE`，维持这个单一来源。
