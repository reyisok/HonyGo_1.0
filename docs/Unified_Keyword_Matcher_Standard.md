# HonyGo 统一关键字判断逻辑规范

## 概述

本文档定义了 HonyGo 项目的统一关键字判断逻辑规范，确保整个项目使用一致的关键字匹配机制。

## 核心原则

### 单一关键字判断逻辑

**强制要求**：整个项目必须使用唯一的关键字判断逻辑模块

- **统一模块**：`src\core\ocr\keyword_matcher.py`
- **禁止行为**：不得在项目中创建或使用多套关键字判断逻辑
- **违规后果**：任何违反此规范的代码将被拒绝合并

## 统一关键字匹配器 (KeywordMatcher)

### 核心功能

`KeywordMatcher` 类提供以下核心功能：

1. **多种匹配策略**：
   - `EXACT`：精确匹配
   - `CONTAINS`：包含匹配
   - `FUZZY`：模糊匹配
   - `REGEX`：正则表达式匹配
   - `SIMILARITY`：相似度匹配

2. **性能优化**：
   - 预编译正则表达式缓存
   - 相似度计算缓存
   - 并行处理支持
   - 智能缓存管理

3. **结果标准化**：
   - 统一的 `MatchResult` 数据结构
   - 置信度评分
   - 位置信息
   - 匹配策略记录

### 标准使用方式

#### 基本用法

```python
from src.core.ocr.keyword_matcher import KeywordMatcher, MatchStrategy

# 创建匹配器实例
matcher = KeywordMatcher()

# 单个关键字匹配
result = matcher.match_keyword(
    target_keyword="确定",
    ocr_results=ocr_data,
    strategy=MatchStrategy.CONTAINS,
    min_confidence=0.8
)

# 检查匹配结果
if result.found:
    print(f"找到匹配: {result.matched_text}")
    print(f"置信度: {result.confidence}")
    print(f"位置: {result.position}")
```

#### 多关键字匹配

```python
# 批量关键字匹配
keywords = ["确定", "取消", "保存"]
results = matcher.match_multiple_keywords(
    keywords=keywords,
    ocr_results=ocr_data,
    strategy=MatchStrategy.FUZZY,
    parallel=True  # 启用并行处理
)

# 处理结果
for keyword, result in results.items():
    if result.found:
        print(f"关键字 '{keyword}' 匹配成功")
```

#### 最佳匹配

```python
# 获取最佳匹配结果
best_result = matcher.get_best_match(
    target_keyword="登录",
    ocr_results=ocr_data
)

if best_result.found:
    print(f"最佳匹配: {best_result.matched_text}")
    print(f"相似度: {best_result.similarity_score}")
```

## 匹配策略详解

### 1. 精确匹配 (EXACT)

- **用途**：需要完全一致的文本匹配
- **特点**：大小写敏感，字符完全相同
- **适用场景**：按钮文本、标题等固定文本

### 2. 包含匹配 (CONTAINS)

- **用途**：目标文本包含在OCR结果中
- **特点**：不区分大小写，支持部分匹配
- **适用场景**：长文本中查找关键词

### 3. 模糊匹配 (FUZZY)

- **用途**：容错匹配，处理OCR识别错误
- **特点**：基于编辑距离算法
- **适用场景**：OCR识别质量不高的情况

### 4. 正则表达式匹配 (REGEX)

- **用途**：复杂模式匹配
- **特点**：支持正则表达式语法
- **适用场景**：格式化文本（如日期、电话号码）

### 5. 相似度匹配 (SIMILARITY)

- **用途**：基于相似度阈值的匹配
- **特点**：返回相似度分数
- **适用场景**：需要量化匹配程度的场景

## 性能优化特性

### 1. 缓存机制

- **正则表达式缓存**：预编译常用正则表达式
- **相似度缓存**：缓存相似度计算结果
- **智能清理**：基于访问频率自动清理缓存

### 2. 并行处理

- **多线程支持**：支持并行处理多个关键字
- **线程池管理**：自动管理线程资源
- **性能监控**：实时统计处理性能

### 3. 性能统计

```python
# 获取性能统计信息
stats = matcher.get_performance_stats()
print(f"总匹配次数: {stats['total_matches']}")
print(f"缓存命中率: {stats['cache_hits']}")
print(f"平均匹配时间: {stats['avg_match_time']}ms")
```

## 集成规范

### 1. 导入规范

```python
# 标准导入方式
from src.HonyGo.core.ocr.keyword_matcher import (
    KeywordMatcher, 
    MatchStrategy, 
    MatchResult
)
```

### 2. 实例化规范

```python
# 推荐：使用单例模式或模块级实例
matcher = KeywordMatcher(max_workers=4)

# 或者在模块初始化时创建全局实例
_global_matcher = None

def get_keyword_matcher() -> KeywordMatcher:
    global _global_matcher
    if _global_matcher is None:
        _global_matcher = KeywordMatcher()
    return _global_matcher
```

### 3. 错误处理规范

```python
try:
    result = matcher.match_keyword(keyword, ocr_results)
    if result.found:
        # 处理匹配成功的情况
        handle_match_success(result)
    else:
        # 处理未找到匹配的情况
        handle_no_match(keyword)
except Exception as e:
    logger.error(f"关键字匹配失败: {e}")
    # 处理异常情况
```

## 禁止行为

### 严格禁止以下行为：

1. **创建自定义关键字匹配逻辑**：
   ```python
   # ❌ 禁止：自定义匹配函数
   def my_custom_match(keyword, text):
       return keyword in text
   ```

2. **直接使用字符串匹配**：
   ```python
   # ❌ 禁止：直接字符串操作
   if "确定" in ocr_text:
       click_button()
   ```

3. **重复实现相似功能**：
   ```python
   # ❌ 禁止：重复实现匹配逻辑
   class MyMatcher:
       def find_text(self, target, results):
           # 重复实现
   ```

4. **绕过统一接口**：
   ```python
   # ❌ 禁止：绕过KeywordMatcher
   import re
   pattern = re.compile(keyword)
   matches = pattern.findall(text)
   ```

## 代码审查要点

### 审查清单

- [ ] 是否使用了统一的 `KeywordMatcher`
- [ ] 是否避免了自定义匹配逻辑
- [ ] 是否正确处理了 `MatchResult`
- [ ] 是否选择了合适的匹配策略
- [ ] 是否包含了适当的错误处理
- [ ] 是否添加了必要的日志记录

### 常见违规模式

1. **字符串直接比较**：
   ```python
   # 违规示例
   if text == "确定":
       return True
   ```

2. **自定义正则匹配**：
   ```python
   # 违规示例
   import re
   if re.search(r"确定|OK", text):
       return True
   ```

3. **重复实现相似度计算**：
   ```python
   # 违规示例
   def calculate_similarity(a, b):
       # 重复实现
   ```

