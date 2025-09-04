# HonyGo 增强信号处理系统使用指南

## 概述

HonyGo 增强信号处理系统提供了跨平台的信号处理能力，支持优先级管理、进程间通信（IPC）和外部控制工具。

## 主要特性

### 1. 跨平台兼容性

- **Windows 平台**：支持 SIGINT、SIGTERM、SIGBREAK 和控制台事件处理
- **Unix/Linux 平台**：支持 SIGINT、SIGTERM、SIGHUP、SIGQUIT、SIGUSR1、SIGUSR2
- **自动平台检测**：根据操作系统自动选择合适的信号处理方式

### 2. 优先级管理

#### 预定义优先级级别

```python
SIGNAL_PRIORITIES = {
    'critical': 0,    # 关键服务（数据库、核心服务）
    'high': 10,       # 重要服务（OCR池、监控服务）
    'medium': 20,     # 一般服务（定时任务、缓存）
    'low': 30         # 可选服务（日志清理、统计）
}
```

#### 使用方法

```python
from src.core.services.signal_handler_service import register_shutdown_callback

# 使用预定义级别
register_shutdown_callback(my_callback, priority='critical')

# 使用自定义数值（数字越小优先级越高）
register_shutdown_callback(my_callback, priority='high', priority_value=5)
```

### 3. 进程间通信（IPC）

#### IPC 配置

```python
IPC_CONFIG = {
    'pipe_name': 'honygo_signal_pipe',
    'signal_file': 'honygo_signal.json',
    'check_interval': 1.0  # 秒
}
```

#### 启用 IPC

```python
from src.core.services.signal_handler_service import get_signal_handler_service

service = get_signal_handler_service()
service.enable_ipc()  # 启用IPC监听
```

#### 发送 IPC 信号

```python
# 发送关闭信号
service.send_ipc_signal('shutdown', '系统维护')

# 发送重启信号
service.send_ipc_signal('restart', '配置更新')

# 发送自定义信号
service.send_ipc_signal('custom_signal', '自定义操作')
```

## 命令行工具

### 安装位置

- Python 脚本：`tools/honygo_signal_cli.py`
- Windows 批处理：`tools/honygo.bat`
- Linux/Unix 脚本：`tools/honygo.sh`

### 基本用法

#### 1. 列出进程

```bash
# Windows
tools\honygo.bat list

# Linux/Unix
./tools/honygo.sh list

# 直接使用Python
python tools/honygo_signal_cli.py list
```

#### 2. 关闭进程

```bash
# 优雅关闭
tools\honygo.bat shutdown

# 强制关闭（30秒超时）
tools\honygo.bat shutdown --force

# 自定义超时时间
tools\honygo.bat shutdown --timeout 60
```

#### 3. 重启进程

```bash
tools\honygo.bat restart
```

#### 4. 发送自定义信号

```bash
# 发送测试信号
tools\honygo.bat signal test "测试信号"

# 发送维护信号
tools\honygo.bat signal maintenance "系统维护开始"
```

#### 5. 监控信号文件

```bash
# 默认1秒间隔监控
tools\honygo.bat monitor

# 自定义监控间隔
tools\honygo.bat monitor --interval 0.5
```

#### 6. 强制终止进程

```bash
# 终止指定PID的进程
tools\honygo.bat kill 1234
```

## 编程接口

### 基本使用

```python
from HonyGo.core.services.signal_handler_service import (
    get_signal_handler_service,
    register_shutdown_callback,
    register_emergency_callback
)

# 获取服务实例
service = get_signal_handler_service()

# 注册关闭回调
def my_shutdown_handler():
    print("正在关闭服务...")
    # 执行清理操作
    return True

register_shutdown_callback(my_shutdown_handler, priority='high')

# 注册紧急回调
def my_emergency_handler():
    print("执行紧急清理...")
    # 执行紧急操作

register_emergency_callback(my_emergency_handler)

# 启用IPC
service.enable_ipc()

# 等待关闭信号
service.wait_for_shutdown()
```

### 优雅关闭混入类

```python
from HonyGo.core.services.signal_handler_service import GracefulShutdownMixin

class MyService(GracefulShutdownMixin):
    def __init__(self):
        super().__init__()
        self.setup_signal_handlers()
    
    def cleanup(self):
        print("清理MyService资源")
        # 执行清理操作
        return True

# 使用
service = MyService()
# 服务会自动处理信号并调用cleanup方法
```

## 配置选项

### 信号处理配置

```python
# 在服务初始化时配置
service = SignalHandlerService()
service.set_shutdown_timeout(60)  # 设置关闭超时时间
```

### IPC 配置

```python
# 自定义IPC配置
service.enable_ipc(
    signal_dir='custom/signal/dir',
    check_interval=0.5
)
```

## 最佳实践

### 1. 优先级设置

- **critical (0)**：数据库连接、核心业务逻辑
- **high (10)**：OCR池、监控服务、缓存服务
- **medium (20)**：定时任务、日志服务
- **low (30)**：统计收集、临时文件清理

### 2. 回调函数设计

```python
def good_shutdown_callback():
    try:
        # 执行清理操作
        cleanup_resources()
        return True  # 返回True表示成功
    except Exception as e:
        logger.error(f"关闭回调失败: {e}")
        return False  # 返回False表示失败
```

### 3. 错误处理

```python
def robust_callback():
    try:
        # 主要清理逻辑
        primary_cleanup()
    except Exception as e:
        logger.error(f"主要清理失败: {e}")
        try:
            # 备用清理逻辑
            fallback_cleanup()
        except Exception as e2:
            logger.critical(f"备用清理也失败: {e2}")
            return False
    return True
```

### 4. 服务集成

```python
class MyApplicationService:
    def __init__(self):
        self.signal_service = get_signal_handler_service()
        self.setup_signal_handling()
    
    def setup_signal_handling(self):
        # 注册关闭回调
        self.signal_service.add_shutdown_callback(
            self.shutdown,
            priority='high',
            priority_value=5
        )
        
        # 启用IPC
        self.signal_service.enable_ipc()
    
    def shutdown(self):
        logger.info("MyApplicationService 正在关闭")
        # 执行服务特定的清理
        return True
```

## 故障排除

### 常见问题

1. **信号未被捕获**
   - 检查信号是否在支持列表中
   - 确认服务已正确初始化
   - 查看日志中的错误信息

2. **IPC 不工作**
   - 检查信号文件目录权限
   - 确认 IPC 已启用
   - 查看进程是否有文件访问权限

3. **回调执行失败**
   - 检查回调函数是否抛出异常
   - 确认回调函数返回值正确
   - 查看超时设置是否合理

### 调试技巧

```python
# 启用详细日志
import logging
logging.getLogger('HonyGo.core.services.signal_handler_service').setLevel(logging.DEBUG)

# 检查服务状态
service = get_signal_handler_service()
print(f"是否正在关闭: {service.is_shutting_down()}")
print(f"注册的回调数量: {len(service._shutdown_callbacks)}")
```

## 更新日志

### v2.0.0 (2025-01-XX)

- 新增跨平台信号处理支持
- 实现优先级管理系统
- 添加进程间通信（IPC）功能
- 提供命令行控制工具
- 增强Windows平台兼容性
- 添加优雅关闭混入类

---

