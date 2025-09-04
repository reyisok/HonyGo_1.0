# HonyGo OCR服务架构与调用规范



## 服务架构总览

### 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    HonyGo OCR服务架构                            │
├─────────────────────────────────────────────────────────────────┤
│  应用层 (Application Layer)                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   主程序界面     │  │   业务逻辑模块   │  │   自动化脚本     │ │
│  │   (main.py)     │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  服务层 (Service Layer)                                          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              OCR实例池服务 (OCRPoolService)                  │ │
│  │              统一对外服务端口: 8900                          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  统一关键字判断  │  │   OCR性能优化    │  │   统一日志服务   │ │
│  │  (KeywordMatcher)│  │ (PerformanceService)│ (LoggingService)│ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  管理层 (Management Layer)                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   实例池管理     │  │   动态扩容管理   │  │   端口管理       │ │
│  │ (PoolManager)   │  │(ScalingManager) │  │ (PortManager)   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  实例层 (Instance Layer)                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   OCR实例 #1     │  │   OCR实例 #2     │  │   OCR实例 #N     │ │
│  │   端口: 8901     │  │   端口: 8902     │  │   端口: 890N     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  基础层 (Foundation Layer)                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   EasyOCR引擎    │  │   GPU/CPU资源    │  │   模型文件       │ │
│  │                 │  │                 │  │   (静态资源)     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件关系

1. **统一入口**：OCR实例池服务 (端口8900)
2. **实例管理**：动态创建和管理多个OCR实例
3. **性能优化**：智能缓存、负载均衡、资源优化
4. **关键字处理**：统一的关键字匹配逻辑
5. **日志记录**：统一的日志服务

## 核心组件详解

### 1. OCR实例池服务 (OCRPoolService)

#### 职责
- 提供统一的OCR服务入口
- 管理多个OCR实例的生命周期
- 实现负载均衡和请求分发
- 提供智能缓存和性能监控

#### 关键特性
- **统一端口**：8900（固定不变）
- **智能缓存**：基于图像内容的结果缓存
- **负载均衡**：基于实例负载的智能分发
- **性能监控**：实时监控服务性能指标

#### 服务接口

```python
# 主要API端点
POST /ocr/recognize          # OCR识别接口
GET  /ocr/status            # 服务状态查询
GET  /ocr/pool/status       # 实例池状态
GET  /ocr/performance       # 性能统计
POST /ocr/config/update     # 配置更新
```

### 2. 统一关键字判断逻辑 (KeywordMatcher)

#### 职责
- 提供统一的关键字匹配功能
- 支持多种匹配策略
- 优化匹配性能和准确性

#### 核心功能
- **多策略匹配**：精确、包含、模糊、正则、相似度
- **性能优化**：缓存、并行处理、预编译
- **结果标准化**：统一的匹配结果格式

#### 使用规范

```python
from src.core.ocr.keyword_matcher import KeywordMatcher, MatchStrategy

# 创建匹配器（推荐单例模式）
matcher = KeywordMatcher()

# 标准调用方式
result = matcher.match_keyword(
    target_keyword="确定",
    ocr_results=ocr_data,
    strategy=MatchStrategy.CONTAINS,
    min_confidence=0.8
)
```

### 3. OCR性能优化服务 (OCRPerformanceService)

#### 职责
- 优化OCR识别性能
- 管理GPU/CPU资源
- 提供模型预热和缓存

#### 核心功能
- **模型预热**：启动时预热模型，提升首次识别速度
- **GPU加速**：自动检测和使用GPU资源
- **资源优化**：CPU、内存、GPU资源的智能管理
- **性能监控**：实时监控和性能统计

### 4. 统一日志服务 (LoggingService)

#### 职责
- 提供统一的日志记录功能
- 支持多种输出目标
- 实现日志分类和归档

#### 输出目标
- **文件输出**：分类存储到不同日志文件
- **控制台输出**：实时显示在控制台
- **UI界面输出**：显示在主程序界面的运行日志

## 服务调用规范

### 1. OCR识别服务调用

#### 标准调用流程

```python
import requests
import base64
from src.core.ocr.keyword_matcher import KeywordMatcher, MatchStrategy
from src.core.services.logging_service import get_logger

# 获取日志记录器
logger = get_logger("OCRClient", "Application")

def recognize_and_match(image_path: str, target_keywords: list) -> dict:
    """
    标准OCR识别和关键字匹配流程
    
    Args:
        image_path: 图像文件路径
        target_keywords: 目标关键字列表
    
    Returns:
        dict: 识别和匹配结果
    """
    try:
        # 1. 图像预处理和编码
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # 2. 调用OCR实例池服务
        ocr_response = requests.post(
            'http://127.0.0.1:8900/ocr/recognize',
            json={
                'image': image_data,
                'languages': ['ch_sim', 'en']
            },
            timeout=30
        )
        
        if ocr_response.status_code != 200:
            logger.error(f"OCR识别失败: {ocr_response.status_code}")
            return {'success': False, 'error': 'OCR服务调用失败'}
        
        ocr_result = ocr_response.json()
        
        if not ocr_result.get('success'):
            logger.error(f"OCR识别失败: {ocr_result.get('error')}")
            return {'success': False, 'error': ocr_result.get('error')}
        
        # 3. 使用统一关键字匹配器
        matcher = KeywordMatcher()
        match_results = {}
        
        for keyword in target_keywords:
            match_result = matcher.match_keyword(
                target_keyword=keyword,
                ocr_results=ocr_result['result'],
                strategy=MatchStrategy.CONTAINS,
                min_confidence=0.8
            )
            match_results[keyword] = match_result
        
        # 4. 记录日志
        logger.info(f"OCR识别完成，识别到 {len(ocr_result['result'])} 个文本块")
        logger.info(f"关键字匹配完成，匹配结果: {len([k for k, v in match_results.items() if v.found])} / {len(target_keywords)}")
        
        return {
            'success': True,
            'ocr_result': ocr_result['result'],
            'match_results': match_results,
            'processing_time': ocr_result.get('processing_time', 0)
        }
        
    except Exception as e:
        logger.error(f"OCR识别和匹配过程异常: {e}")
        return {'success': False, 'error': str(e)}
```

#### 调用规范要点

1. **必须使用OCR实例池服务**：禁止直接调用OCR实例
2. **必须使用统一关键字匹配器**：禁止自定义匹配逻辑
3. **必须使用统一日志服务**：记录关键操作和异常
4. **必须处理异常情况**：网络异常、服务异常、识别失败等

### 2. 服务状态监控

#### 健康检查

```python
def check_ocr_service_health() -> dict:
    """
    检查OCR服务健康状态
    
    Returns:
        dict: 服务健康状态
    """
    try:
        # 检查主服务状态
        response = requests.get('http://127.0.0.1:8900/ocr/status', timeout=5)
        
        if response.status_code == 200:
            status_data = response.json()
            return {
                'service_available': True,
                'status': status_data,
                'timestamp': time.time()
            }
        else:
            return {
                'service_available': False,
                'error': f'HTTP {response.status_code}',
                'timestamp': time.time()
            }
            
    except Exception as e:
        return {
            'service_available': False,
            'error': str(e),
            'timestamp': time.time()
        }
```

#### 性能监控

```python
def get_ocr_performance_metrics() -> dict:
    """
    获取OCR服务性能指标
    
    Returns:
        dict: 性能指标数据
    """
    try:
        response = requests.get('http://127.0.0.1:8900/ocr/performance', timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"获取性能指标失败: HTTP {response.status_code}")
            return {}
            
    except Exception as e:
        logger.error(f"获取性能指标异常: {e}")
        return {}
```

## 服务生命周期管理

### 1. 服务启动流程

```python
# 主程序启动时的服务初始化顺序
def initialize_ocr_services():
    """
    初始化OCR相关服务
    """
    logger = get_logger("ServiceInitializer", "Application")
    
    try:
        # 1. 启动统一日志服务（已在main.py中初始化）
        logger.info("统一日志服务已启动")
        
        # 2. 启动OCR性能优化服务
        performance_service = OCRPerformanceService()
        performance_service.start_performance_monitoring()
        logger.info("OCR性能优化服务已启动")
        
        # 3. 启动OCR实例池服务
        pool_service = OCRPoolService(host='127.0.0.1', port=8900)
        pool_service.start(enable_scaling=True)
        logger.info("OCR实例池服务已启动，端口: 8900")
        
        # 4. 等待服务就绪
        time.sleep(3)
        
        # 5. 验证服务状态
        health_status = check_ocr_service_health()
        if health_status['service_available']:
            logger.info("OCR服务初始化完成，服务正常运行")
            return True
        else:
            logger.error(f"OCR服务初始化失败: {health_status.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"OCR服务初始化异常: {e}")
        return False
```

### 2. 服务关闭流程

```python
def shutdown_ocr_services():
    """
    关闭OCR相关服务
    """
    logger = get_logger("ServiceShutdown", "Application")
    
    try:
        # 1. 关闭OCR实例池服务
        # 发送关闭信号到池服务
        requests.post('http://127.0.0.1:8900/ocr/shutdown', timeout=10)
        logger.info("OCR实例池服务关闭信号已发送")
        
        # 2. 关闭性能优化服务
        # 性能服务会随主程序关闭
        logger.info("OCR性能优化服务已关闭")
        
        # 3. 清理资源
        time.sleep(2)  # 等待服务完全关闭
        logger.info("OCR服务关闭完成")
        
    except Exception as e:
        logger.error(f"OCR服务关闭异常: {e}")
```

## 配置管理规范

### 1. 配置文件结构

```
src/HonyGo/config/
├── ocr_service_config.json         # 主服务配置
├── ocr_performance_config.json     # 性能优化配置
├── ocr_pool_config.json           # 实例池配置
├── keyword_matcher_config.json    # 关键字匹配配置
└── logging_config.json            # 日志配置
```

### 2. 配置加载和验证

```python
def load_and_validate_config(config_path: str) -> dict:
    """
    加载和验证配置文件
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        dict: 验证后的配置数据
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 配置验证逻辑
        if 'ocr_service' in config_path:
            validate_ocr_service_config(config)
        elif 'performance' in config_path:
            validate_performance_config(config)
        # ... 其他配置验证
        
        logger.info(f"配置文件加载成功: {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"配置文件加载失败 {config_path}: {e}")
        raise
```

## 错误处理和异常管理

### 1. 统一异常处理

```python
class OCRServiceException(Exception):
    """OCR服务异常基类"""
    pass

class OCRRecognitionException(OCRServiceException):
    """OCR识别异常"""
    pass

class OCRServiceUnavailableException(OCRServiceException):
    """OCR服务不可用异常"""
    pass

class KeywordMatchException(OCRServiceException):
    """关键字匹配异常"""
    pass
```

### 2. 异常处理策略

```python
def handle_ocr_exception(func):
    """
    OCR异常处理装饰器
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OCRServiceUnavailableException as e:
            logger.error(f"OCR服务不可用: {e}")
            # 尝试重启服务或使用备用方案
            return handle_service_unavailable(e)
        except OCRRecognitionException as e:
            logger.error(f"OCR识别失败: {e}")
            # 记录失败信息，返回默认结果
            return handle_recognition_failure(e)
        except Exception as e:
            logger.error(f"OCR操作异常: {e}")
            # 通用异常处理
            return handle_general_exception(e)
    
    return wrapper
```

## 性能优化建议

### 1. 系统级优化

- **资源分配**：合理分配CPU、内存、GPU资源
- **并发控制**：控制并发请求数量，避免资源竞争
- **缓存策略**：启用智能缓存，提高重复请求的响应速度
- **负载均衡**：使用负载均衡算法，均匀分发请求

### 2. 应用级优化

- **批处理**：对于大量图片，使用批处理模式
- **异步处理**：使用异步调用，提高并发处理能力
- **结果复用**：缓存和复用OCR识别结果
- **预处理优化**：优化图像预处理流程

### 3. 配置优化

- **canvas_size**：根据精度要求调整图像处理尺寸
- **model_cache_size**：根据内存情况调整模型缓存
- **实例数量**：根据并发需求调整实例数量
- **超时设置**：合理设置请求超时时间

## 监控和运维

### 1. 关键监控指标

- **服务可用性**：服务是否正常运行
- **响应时间**：平均响应时间和P99响应时间
- **吞吐量**：每秒处理请求数
- **错误率**：错误请求占总请求的比例
- **资源使用率**：CPU、内存、GPU使用情况
- **缓存命中率**：缓存命中率统计

### 2. 告警规则

- **服务不可用**：立即告警
- **响应时间过长**：超过3秒告警
- **错误率过高**：超过5%告警
- **资源使用率过高**：超过90%告警
- **缓存命中率过低**：低于50%告警


## 版本兼容性

### 1. API版本管理

- **版本标识**：API接口包含版本信息
- **向后兼容**：新版本保持向后兼容
- **废弃通知**：提前通知API废弃计划

### 2. 配置兼容性

- **配置迁移**：提供配置文件迁移工具
- **默认值处理**：新增配置项提供合理默认值
- **验证机制**：启动时验证配置兼容性

---

**重要提醒**：

1. **统一入口**：所有OCR相关功能必须通过OCR实例池服务（端口8900）访问
2. **统一组件**：必须使用统一的关键字匹配器和日志服务
3. **规范遵循**：严格遵循本文档的调用规范和最佳实践
4. **监控重要**：定期监控服务状态和性能指标
5. **文档更新**：服务架构变更时及时更新本文档

**版本**: 1.0  
**更新日期**: 2025-08-31  
**作者**: Mr.Rey Copyright © 2025