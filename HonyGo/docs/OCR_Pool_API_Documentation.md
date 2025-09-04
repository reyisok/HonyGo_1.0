# OCR池API文档

## 概述

OCR池API服务提供HTTP RESTful接口，用于访问OCR池服务的各种功能。服务默认运行在 `http://127.0.0.1:8900`。

**版本**: 1.0.0  
**作者**: Mr.Rey Copyright © 2025  
**创建时间**: 2025-01-14  
**服务端口**: 8900  

## 基础信息

### 服务地址
- **基础URL**: `http://127.0.0.1:8900`
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

### 通用响应格式

所有API响应都遵循统一的JSON格式：

```json
{
  "success": true|false,
  "data": {},           // 成功时的数据
  "result": {},         // OCR识别结果
  "error": "错误信息",   // 失败时的错误信息
  "timestamp": 1642147200.123,
  "request_id": "req_1642147200123",
  "processing_time": 1.23  // 处理耗时（秒）
}
```

### 请求ID规则

每个请求都会生成唯一的请求ID，用于日志追踪：
- 健康检查: `health_{timestamp}`
- OCR识别: `req_{timestamp}`
- 批量OCR: `batch_{timestamp}`
- 池状态: `status_{timestamp}`
- 性能指标: `metrics_{timestamp}`
- 错误请求: `{status_code}_{timestamp}`

## API接口详情

### 1. 健康检查

检查OCR API服务和OCR池的健康状态。

**接口信息**
- **URL**: `/health`
- **方法**: `GET`
- **认证**: 无需认证

**请求示例**
```bash
curl -X GET http://127.0.0.1:8900/health
```

**响应示例**
```json
{
  "status": "healthy",
  "timestamp": 1642147200.123,
  "service": "OCR API Server",
  "version": "1.0.0",
  "request_id": "health_1642147200123",
  "pool_status": {
    "total_instances": 3,
    "active_instances": 3,
    "idle_instances": 2,
    "busy_instances": 1,
    "failed_instances": 0,
    "pool_health": "healthy"
  }
}
```

**状态说明**
- `healthy`: 服务正常运行
- `unhealthy`: 服务异常
- `pool_status`: OCR池详细状态信息

### 2. 单张图片OCR识别

对单张图片进行OCR文字识别。

**接口信息**
- **URL**: `/ocr`
- **方法**: `POST`
- **Content-Type**: `application/json`

**请求参数**

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| image_data | string | 是 | - | Base64编码的图片数据 |
| languages | array | 否 | ["ch_sim", "en"] | 识别语言列表 |
| use_gpu | boolean | 否 | false | 是否使用GPU加速 |
| keywords | array | 否 | [] | 关键词过滤列表 |

**支持的语言代码**
- `ch_sim`: 简体中文
- `ch_tra`: 繁体中文
- `en`: 英语
- `ja`: 日语
- `ko`: 韩语
- 更多语言请参考EasyOCR文档

**请求示例**
```bash
curl -X POST http://127.0.0.1:8900/ocr \
  -H "Content-Type: application/json" \
  -d '{
    "image_data": "iVBORw0KGgoAAAANSUhEUgAA...",
    "languages": ["ch_sim", "en"],
    "use_gpu": false,
    "keywords": ["文本", "识别"]
  }'
```

**响应示例**
```json
{
  "success": true,
  "result": [
    {
      "text": "识别到的文本内容",
      "confidence": 0.95,
      "bbox": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]],
      "keywords_matched": ["文本"]
    }
  ],
  "processing_time": 1.23,
  "timestamp": 1642147200.123,
  "request_id": "req_1642147200123"
}
```

**错误响应示例**
```json
{
  "success": false,
  "error": "缺少image_data参数",
  "request_id": "req_1642147200123"
}
```

### 3. 批量图片OCR识别

对多张图片进行批量OCR文字识别。

**接口信息**
- **URL**: `/ocr/batch`
- **方法**: `POST`
- **Content-Type**: `application/json`
- **限制**: 最多支持10张图片

**请求参数**

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| images | array | 是 | - | Base64编码的图片数据数组 |
| languages | array | 否 | ["ch_sim", "en"] | 识别语言列表 |
| use_gpu | boolean | 否 | false | 是否使用GPU加速 |
| keywords | array | 否 | [] | 关键词过滤列表 |

**请求示例**
```bash
curl -X POST http://127.0.0.1:8900/ocr/batch \
  -H "Content-Type: application/json" \
  -d '{
    "images": [
      "iVBORw0KGgoAAAANSUhEUgAA...",
      "iVBORw0KGgoAAAANSUhEUgBB..."
    ],
    "languages": ["ch_sim", "en"],
    "use_gpu": false,
    "keywords": []
  }'
```

**响应示例**
```json
{
  "success": true,
  "results": [
    {
      "index": 0,
      "success": true,
      "result": [
        {
          "text": "第一张图片的文本",
          "confidence": 0.95,
          "bbox": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        }
      ]
    },
    {
      "index": 1,
      "success": false,
      "error": "图片数据格式无效"
    }
  ],
  "summary": {
    "total": 2,
    "success": 1,
    "failed": 1
  },
  "processing_time": 2.45,
  "timestamp": 1642147200.123,
  "request_id": "batch_1642147200123"
}
```

### 4. 获取OCR池状态

获取OCR池的当前运行状态和实例信息。

**接口信息**
- **URL**: `/pool/status`
- **方法**: `GET`
- **认证**: 无需认证

**请求示例**
```bash
curl -X GET http://127.0.0.1:8900/pool/status
```

**响应示例**
```json
{
  "success": true,
  "data": {
    "pool_info": {
      "total_instances": 3,
      "active_instances": 3,
      "idle_instances": 2,
      "busy_instances": 1,
      "failed_instances": 0,
      "pool_health": "healthy",
      "created_at": "2025-01-14T10:30:00Z",
      "uptime_seconds": 3600
    },
    "instances": [
      {
        "instance_id": "ocr_001",
        "status": "idle",
        "pid": 12345,
        "memory_usage_mb": 256.5,
        "cpu_usage_percent": 2.1,
        "requests_processed": 150,
        "last_activity": "2025-01-14T11:25:30Z",
        "languages": ["ch_sim", "en"],
        "gpu_enabled": false
      }
    ],
    "request_stats": {
      "total_requests": 500,
      "successful_requests": 485,
      "failed_requests": 15,
      "average_processing_time": 1.23,
      "requests_per_minute": 8.5
    }
  },
  "timestamp": 1642147200.123,
  "request_id": "status_1642147200123"
}
```

**状态字段说明**
- `pool_health`: `healthy`(健康) | `degraded`(降级) | `unhealthy`(不健康)
- `instance_status`: `idle`(空闲) | `busy`(忙碌) | `failed`(失败) | `starting`(启动中)

### 5. 获取性能指标

获取OCR池的详细性能指标和统计信息。

**接口信息**
- **URL**: `/pool/metrics`
- **方法**: `GET`
- **认证**: 无需认证

**请求示例**
```bash
curl -X GET http://127.0.0.1:8900/pool/metrics
```

**响应示例**
```json
{
  "success": true,
  "data": {
    "system_metrics": {
      "cpu_usage_percent": 15.2,
      "memory_usage_mb": 1024.5,
      "memory_usage_percent": 12.8,
      "disk_usage_percent": 45.3,
      "load_average": [1.2, 1.1, 1.0]
    },
    "pool_metrics": {
      "total_instances": 3,
      "active_instances": 3,
      "average_response_time": 1.23,
      "throughput_per_minute": 8.5,
      "error_rate_percent": 3.0,
      "queue_length": 2
    },
    "performance_stats": {
      "requests_last_hour": 480,
      "requests_last_day": 11520,
      "average_processing_time_hour": 1.15,
      "peak_processing_time": 5.67,
      "success_rate_percent": 97.0
    },
    "resource_usage": {
      "total_memory_mb": 768.2,
      "total_cpu_percent": 8.5,
      "gpu_usage_percent": 0.0,
      "network_io_mb": 12.3
    }
  },
  "timestamp": 1642147200.123,
  "request_id": "metrics_1642147200123"
}
```

## 错误处理

### HTTP状态码

| 状态码 | 说明 | 示例场景 |
|--------|------|----------|
| 200 | 请求成功 | 正常的API调用 |
| 400 | 请求参数错误 | 缺少必需参数、参数格式错误 |
| 404 | 接口不存在 | 访问未定义的API路径 |
| 500 | 服务器内部错误 | OCR处理异常、系统错误 |

### 错误响应格式

```json
{
  "success": false,
  "error": "具体错误信息",
  "request_id": "error_request_id",
  "timestamp": 1642147200.123,
  "available_endpoints": [  // 仅404错误时包含
    "GET /health - 健康检查",
    "POST /ocr - 单张图片OCR识别",
    "POST /ocr/batch - 批量图片OCR识别",
    "GET /pool/status - 获取池状态",
    "GET /pool/metrics - 获取性能指标"
  ]
}
```

### 常见错误信息

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| "请求数据为空" | POST请求没有JSON数据 | 确保请求包含有效的JSON数据 |
| "缺少image_data参数" | OCR请求缺少图片数据 | 添加base64编码的图片数据 |
| "image_data必须是非空字符串" | 图片数据格式错误 | 确保图片数据是有效的base64字符串 |
| "images参数必须是数组" | 批量请求参数格式错误 | 确保images是字符串数组 |
| "批量处理最多支持10张图片" | 批量请求图片数量超限 | 减少图片数量或分批处理 |
| "OCR池管理器未初始化" | OCR池服务未启动 | 检查OCR池服务状态 |
| "OCR识别失败或结果为空" | 图片无法识别或无文字 | 检查图片质量和内容 |

## 使用示例

### Python示例

```python
import requests
import base64
import json

# 服务地址
BASE_URL = "http://127.0.0.1:8900"

def health_check():
    """健康检查"""
    response = requests.get(f"{BASE_URL}/health")
    return response.json()

def ocr_single_image(image_path, languages=["ch_sim", "en"]):
    """单张图片OCR识别"""
    # 读取并编码图片
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    data = {
        "image_data": image_data,
        "languages": languages,
        "use_gpu": False
    }
    
    response = requests.post(f"{BASE_URL}/ocr", json=data)
    return response.json()

def get_pool_status():
    """获取池状态"""
    response = requests.get(f"{BASE_URL}/pool/status")
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 健康检查
    health = health_check()
    print("健康状态:", health)
    
    # OCR识别
    result = ocr_single_image("test_image.png")
    print("OCR结果:", result)
    
    # 池状态
    status = get_pool_status()
    print("池状态:", status)
```

### JavaScript示例

```javascript
const BASE_URL = 'http://127.0.0.1:8900';

// 健康检查
async function healthCheck() {
    const response = await fetch(`${BASE_URL}/health`);
    return await response.json();
}

// 单张图片OCR识别
async function ocrSingleImage(imageBase64, languages = ['ch_sim', 'en']) {
    const data = {
        image_data: imageBase64,
        languages: languages,
        use_gpu: false
    };
    
    const response = await fetch(`${BASE_URL}/ocr`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    
    return await response.json();
}

// 获取池状态
async function getPoolStatus() {
    const response = await fetch(`${BASE_URL}/pool/status`);
    return await response.json();
}

// 使用示例
(async () => {
    try {
        // 健康检查
        const health = await healthCheck();
        console.log('健康状态:', health);
        
        // 获取池状态
        const status = await getPoolStatus();
        console.log('池状态:', status);
    } catch (error) {
        console.error('API调用失败:', error);
    }
})();
```

- 