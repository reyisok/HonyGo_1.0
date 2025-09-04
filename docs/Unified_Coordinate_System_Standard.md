# 统一坐标系统标准

## 概述

本文档定义了HonyGo项目中统一的坐标转换标准，解决DPI缩放环境下的坐标转换混乱问题。

## 坐标系统定义

### 1. 坐标类型

- **逻辑坐标（Logical Coordinates）**：应用程序内部使用的标准化坐标，不受DPI缩放影响
- **物理坐标（Physical Coordinates）**：屏幕实际像素坐标，受DPI缩放影响
- **屏幕坐标（Screen Coordinates）**：与物理坐标相同，用于系统API调用

### 2. 坐标转换原则

1. **单一转换点**：每个坐标只能在一个地方进行转换
2. **明确坐标类型**：所有函数参数和返回值必须明确标注坐标类型
3. **统一转换服务**：所有坐标转换必须通过CoordinateService进行
4. **避免重复转换**：禁止对已转换的坐标再次转换

## 核心服务接口

### CoordinateService 标准接口

```python
class CoordinateService:
    # 基础转换方法
    def logical_to_physical(self, x: int, y: int) -> Tuple[int, int]
    def physical_to_logical(self, x: int, y: int) -> Tuple[int, int]
    
    # 专用转换方法
    def convert_for_click(self, logical_x: int, logical_y: int) -> Tuple[int, int]
    def convert_for_animation(self, logical_x: int, logical_y: int) -> Tuple[int, int]
    
    # DPI信息获取
    def get_primary_screen_dpi_scale(self) -> float
    def get_coordinate_info(self, x: int, y: int) -> Dict[str, Any]
```

## 图像匹配坐标处理标准

### 1. 图像匹配算法输出

图像匹配算法（ImageReferenceAlgorithm）必须输出**逻辑坐标**：

```python
@dataclass
class MatchResult:
    similarity: float
    position: Optional[Tuple[int, int]]  # 逻辑坐标中心点
    confidence: float
    method: MatchMethod
    execution_time: float
    scale: float = 1.0
```

### 2. 中心点计算标准

在`_single_scale_match`方法中：

```python
def _single_scale_match(self, screen_gray: np.ndarray, reference_gray: np.ndarray, scale: float) -> Optional[Dict]:
    # 模板匹配
    result = cv2.matchTemplate(screen_gray, scaled_reference, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    # 计算中心点坐标（逻辑坐标）
    h, w = scaled_reference.shape
    center_x = max_loc[0] + w // 2
    center_y = max_loc[1] + h // 2
    
    return {
        'confidence': max_val,
        'position': (center_x, center_y),  # 返回逻辑坐标
        'scale': scale
    }
```

### 3. ClickTarget 坐标处理

```python
@dataclass
class ClickTarget:
    text: str
    bbox: Tuple[int, int, int, int]  # 逻辑坐标边界框
    confidence: float
    center_x: int  # 逻辑坐标中心点X
    center_y: int  # 逻辑坐标中心点Y
    similarity: float = 0.0
    source: str = 'ocr'
```

## 点击执行标准

### 1. 点击方法层次

```python
class SmartClickService:
    # 高级接口：接收逻辑坐标，内部转换
    def click_at_position(self, logical_x: int, logical_y: int, ...) -> bool:
        physical_x, physical_y = self.coordinate_service.convert_for_click(logical_x, logical_y)
        return self.perform_click(physical_x, physical_y, ...)
    
    # 低级接口：接收物理坐标，直接执行
    def perform_click(self, physical_x: int, physical_y: int, ...) -> bool:
        pyautogui.click(physical_x, physical_y)
```

### 2. 点击序列执行

```python
def _execute_click_sequence(self, targets: List[ClickTarget], ...) -> Dict[str, Any]:
    for target in targets:
        # 使用逻辑坐标调用高级接口
        success = self.click_at_position(
            target.center_x,  # 逻辑坐标
            target.center_y,  # 逻辑坐标
            ...
        )
```

## 坐标转换流程图

```
图像匹配算法
    ↓ (输出逻辑坐标)
ClickTarget.center_x/y
    ↓ (传递逻辑坐标)
click_at_position(logical_x, logical_y)
    ↓ (转换为物理坐标)
coordinate_service.convert_for_click()
    ↓ (输出物理坐标)
perform_click(physical_x, physical_y)
    ↓ (直接使用物理坐标)
pyautogui.click(physical_x, physical_y)
```

## 常见错误和修复

### 错误1：重复坐标转换

```python
# 错误：坐标被转换两次
physical_x, physical_y = self.coordinate_service.logical_to_physical(target.center_x, target.center_y)
self.perform_click(physical_x, physical_y)  # perform_click内部又转换了一次

# 正确：只转换一次
self.click_at_position(target.center_x, target.center_y)  # 内部转换一次
```

### 错误2：坐标类型混淆

```python
# 错误：将物理坐标当作逻辑坐标使用
physical_pos = pyautogui.position()
self.click_at_position(physical_pos.x, physical_pos.y)  # 错误！

# 正确：明确坐标类型
physical_pos = pyautogui.position()
logical_x, logical_y = self.coordinate_service.physical_to_logical(physical_pos.x, physical_pos.y)
self.click_at_position(logical_x, logical_y)
```

### 错误3：图像匹配结果处理错误

```python
# 错误：将匹配位置当作左上角坐标
target = ClickTarget(
    center_x=match['position'][0],  # 这已经是中心点了！
    center_y=match['position'][1],
    ...
)

# 正确：直接使用匹配结果的中心点
target = ClickTarget(
    center_x=match['position'][0],  # 正确使用中心点
    center_y=match['position'][1],
    ...
)
```

## 测试验证标准

### 1. 坐标转换测试

```python
def test_coordinate_conversion():
    service = get_coordinate_service()
    
    # 测试往返转换
    logical_x, logical_y = 100, 200
    physical_x, physical_y = service.logical_to_physical(logical_x, logical_y)
    back_logical_x, back_logical_y = service.physical_to_logical(physical_x, physical_y)
    
    assert logical_x == back_logical_x
    assert logical_y == back_logical_y
```

### 2. 点击精度测试

```python
def test_click_accuracy():
    # 测试点击位置是否准确
    target_logical_x, target_logical_y = 500, 300
    
    # 执行点击
    service.click_at_position(target_logical_x, target_logical_y)
    
    # 验证点击位置（需要实际测试环境）
    # ...
```



## 注意事项

1. **向后兼容性**：修改时保持现有API的兼容性
2. **性能考虑**：避免不必要的坐标转换计算
3. **错误处理**：添加坐标范围检查和异常处理
4. **日志记录**：记录坐标转换过程便于调试

---

@author: Mr.Rey Copyright © 2025
@created: 2025-01-25 16:30:00
@modified: 2025-01-25 16:30:00
@version: 1.0.0