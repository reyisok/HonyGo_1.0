# 统一坐标转换服务使用指南

## 概述

统一坐标转换服务(`CoordinateService`)是HonyGo项目中处理屏幕坐标转换的核心组件，提供DPI感知的坐标系统，支持多显示器环境下的精确坐标转换。

## 核心功能

### 1. DPI感知坐标转换
- 自动检测系统DPI缩放比例
- 逻辑坐标与物理坐标双向转换
- 支持不同DPI缩放因子的多显示器环境

### 2. 多屏幕支持
- 自动识别所有连接的显示器
- 根据坐标点自动确定所在屏幕
- 提供屏幕间坐标转换功能

### 3. 坐标规范化
- 确保坐标在有效屏幕范围内
- 处理负坐标和超出边界的情况
- 自动调整区域大小以适应屏幕边界

## 使用方法

### 获取服务实例

```python
from src.ui.services.coordinate_service import get_coordinate_service

# 获取坐标转换服务实例（单例模式）
coordinate_service = get_coordinate_service()
```

### 基本坐标转换

```python
# 逻辑坐标转物理坐标
physical_x, physical_y = coordinate_service.logical_to_physical(100, 200)

# 物理坐标转逻辑坐标
logical_x, logical_y = coordinate_service.physical_to_logical(150, 300)
```

### 专用坐标转换

```python
# 为点击操作转换坐标（适用于pyautogui等库）
click_x, click_y = coordinate_service.convert_for_click(100, 200)

# 为动画显示转换坐标（适用于UI动画组件）
animation_x, animation_y = coordinate_service.convert_for_animation(100, 200)
```

### 坐标规范化

```python
# 规范化坐标，确保在屏幕范围内
norm_x, norm_y, norm_w, norm_h = coordinate_service.normalize_coordinates(
    x=-50, y=-100, width=300, height=400
)
```

### 屏幕信息查询

```python
# 获取主屏幕DPI缩放比例
dpi_scale = coordinate_service.get_primary_screen_dpi_scale()

# 获取指定屏幕信息
screen_info = coordinate_service.get_screen_info(screen_index=0)

# 获取所有屏幕信息
all_screens = coordinate_service.get_all_screens_info()
```

### 坐标信息获取

```python
# 获取坐标的详细信息
coord_info = coordinate_service.get_coordinate_info(100, 200)
print(f"坐标: ({coord_info.x}, {coord_info.y})")
print(f"屏幕索引: {coord_info.screen_index}")
print(f"DPI缩放: {coord_info.dpi_scale}")
print(f"坐标类型: {'逻辑' if coord_info.is_logical else '物理'}")
```

## 数据结构

### CoordinateInfo
坐标信息数据类，包含以下字段：
- `x`: X坐标
- `y`: Y坐标
- `screen_index`: 屏幕索引
- `dpi_scale`: DPI缩放比例
- `is_logical`: 是否为逻辑坐标

### ScreenInfo
屏幕信息数据类，包含以下字段：
- `index`: 屏幕索引
- `geometry`: 屏幕几何信息(QRect)
- `available_geometry`: 可用区域几何信息(QRect)
- `dpi_scale`: DPI缩放比例
- `logical_dpi`: 逻辑DPI
- `physical_dpi`: 物理DPI
- `is_primary`: 是否为主屏幕

## 最佳实践

### 1. 统一使用坐标服务
- 项目中所有坐标处理都应使用统一坐标转换服务
- 避免直接使用屏幕坐标进行计算
- 通过服务获取DPI信息而不是硬编码

### 2. 选择合适的转换方法
- 点击操作使用 `convert_for_click()`
- UI动画使用 `convert_for_animation()`
- 一般坐标转换使用 `logical_to_physical()` 或 `physical_to_logical()`

### 3. 处理多屏幕环境
- 使用 `get_screen_from_point()` 确定坐标所在屏幕
- 在跨屏幕操作时考虑不同的DPI缩放比例
- 使用 `normalize_coordinates()` 确保坐标在有效范围内

### 4. 错误处理
- 服务在无QApplication环境下会使用降级方案
- 坐标超出范围时会自动规范化
- 建议在关键操作前检查坐标有效性

### 5. 性能优化
- 服务使用单例模式，避免重复初始化
- 屏幕信息会缓存，减少系统调用
- 使用 `refresh_screen_info()` 在屏幕配置变化时更新缓存

## 集成示例

### SmartClickService集成
```python
class SmartClickService:
    def __init__(self):
        self.coordinate_service = get_coordinate_service()
    
    def click_at_position(self, x: int, y: int):
        # 转换为点击坐标
        click_x, click_y = self.coordinate_service.convert_for_click(x, y)
        # 执行点击操作
        pyautogui.click(click_x, click_y)
```

### 点击动画集成
```python
class ClickAnimationWidget:
    def __init__(self, x: int, y: int):
        self.coordinate_service = get_coordinate_service()
        # 转换为动画坐标
        animation_x, animation_y = self.coordinate_service.convert_for_animation(x, y)
        # 设置窗口位置
        self.setGeometry(animation_x - size//2, animation_y - size//2, size, size)
```

## 注意事项

1. **线程安全**: 服务是线程安全的，可以在多线程环境中使用
2. **资源管理**: 服务会自动管理Qt资源，无需手动释放
3. **配置变化**: 当显示器配置发生变化时，建议调用 `refresh_screen_info()` 更新缓存
4. **测试环境**: 在测试环境中可能需要Mock QApplication相关功能

## 故障排除

### 常见问题

1. **坐标转换不准确**
   - 检查DPI缩放设置是否正确
   - 确认使用了正确的转换方法
   - 验证屏幕配置信息

2. **多屏幕环境问题**
   - 使用 `get_all_screens_info()` 检查屏幕配置
   - 确认坐标点在正确的屏幕范围内
   - 检查屏幕索引是否正确

3. **性能问题**
   - 避免频繁调用 `refresh_screen_info()`
   - 缓存转换结果以减少重复计算
   - 使用批量转换方法处理大量坐标

### 调试技巧

1. 启用调试日志查看详细转换信息
2. 使用 `get_coordinate_info()` 获取坐标详细信息
3. 比较转换前后的坐标值验证转换正确性

---

**文档版本**: 1.0  
**最后更新**: 2025-01-23  
**作者**: Mr.Rey Copyright © 2025