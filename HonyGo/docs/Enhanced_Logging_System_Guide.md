# HonyGo 增强日志系统指南

@author: Mr.Rey Copyright © 2025

## 概述

HonyGo 项目采用统一的日志系统架构，提供全面的日志记录、监控和分析功能。本文档详细介绍了增强后的日志系统功能和使用方法。

## 日志系统架构

### 核心组件

1. **统一日志服务** (`logging_service.py`)
   - 提供全局统一的日志记录接口
   - 支持多种日志级别和分类
   - 自动日志轮转和归档

2. **构建日志服务** (`build_logging_service.py`)
   - 项目构建过程的详细日志记录
   - 依赖检查和安装过程监控
   - 环境信息收集和记录
   - 构建报告生成

3. **启动监控服务** (`startup_monitoring_service.py`)
   - 启动过程的阶段性监控
   - 服务初始化状态跟踪
   - 启动性能分析

## 日志分类和存储

### 日志目录结构

```
data/logs/
├── Application/        # 应用程序运行日志
├── Error/             # 错误和异常日志
├── General/           # 通用日志
├── OCR/               # OCR相关日志
├── Performance/       # 性能监控日志
├── System/            # 系统级日志
├── Tests/             # 测试相关日志
└── archive/           # 归档日志
```

### 日志分类说明

- **Application**: 主程序运行时的业务逻辑日志
- **Error**: 所有错误、异常和警告信息
- **General**: 通用操作和状态信息
- **OCR**: OCR服务、池管理、识别过程日志
- **Performance**: 性能指标、耗时统计、资源使用情况
- **System**: 系统环境、进程管理、资源监控日志
- **Tests**: 测试执行、结果验证、调试信息

## 构建日志服务功能

### 环境信息记录

构建日志服务会自动收集和记录以下环境信息：

- Python版本和可执行文件路径
- 操作系统平台和架构信息
- CPU核心数和内存容量
- 磁盘空间使用情况
- 环境变量和路径配置

### 依赖检查和管理

- **依赖包检查**: 验证所有必需依赖包的安装状态
- **版本兼容性**: 检查依赖包版本是否符合要求
- **自动安装**: 自动安装缺失的依赖包
- **缓存管理**: 维护依赖检查结果缓存

### 项目结构验证

- 检查关键目录和文件是否存在
- 验证配置文件的完整性
- 记录缺失的项目组件

### 构建命令执行

- 记录构建命令的详细执行过程
- 监控命令执行时间和资源使用
- 捕获和记录命令输出和错误信息
- 支持超时控制和异常处理

### 构建报告生成

构建日志服务会生成详细的构建报告，包含：

- 构建成功率统计
- 平均构建时间分析
- 依赖安装成功率
- 环境兼容性评估
- 错误和警告汇总

## 启动监控服务功能

### 启动阶段监控

启动监控服务将启动过程划分为以下阶段：

1. **INITIALIZATION**: 初始化阶段
2. **DEPENDENCY_CHECK**: 依赖检查阶段
3. **SERVICE_REGISTRATION**: 服务注册阶段
4. **SERVICE_INITIALIZATION**: 服务初始化阶段
5. **UI_STARTUP**: 界面启动阶段
6. **FINAL_VERIFICATION**: 最终验证阶段

### 阶段详情记录

每个启动阶段都会记录详细信息：

- 阶段开始和结束时间
- 阶段执行耗时
- 关键操作的详细参数
- 成功/失败状态
- 错误信息和异常堆栈

### 性能分析

- 各阶段耗时统计
- 启动瓶颈识别
- 资源使用情况监控
- 历史性能趋势分析

## 日志配置

### 日志级别配置

支持以下日志级别：

- **DEBUG**: 详细的调试信息
- **INFO**: 一般信息记录
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误信息

### 日志格式配置

标准日志格式：
```
[时间戳] [日志级别] [模块名称] [线程ID] - 日志消息
```

### 日志轮转配置

- 单个日志文件最大大小：10MB
- 保留历史日志文件数量：5个
- 自动压缩归档超过30天的日志

## 使用方法

### 基本日志记录

```python
from HonyGo.services.logging_service import get_logger

# 获取日志记录器
logger = get_logger('模块名称')

# 记录不同级别的日志
logger.debug('调试信息')
logger.info('一般信息')
logger.warning('警告信息')
logger.error('错误信息')
logger.critical('严重错误')
```

### 构建日志服务使用

```python
from HonyGo.services.build_logging_service import BuildLoggingService

# 创建构建日志服务实例
build_service = BuildLoggingService(project_root='/path/to/project')

# 记录环境信息
env_info = build_service.log_environment_info()

# 检查依赖
dependencies = build_service.check_all_dependencies()

# 执行构建命令
result = build_service.run_build_command(['python', 'setup.py', 'build'])

# 生成构建报告
report = build_service.generate_build_report()
```

### 启动监控服务使用

```python
from HonyGo.services.startup_monitoring_service import StartupMonitoringService
from HonyGo.services.startup_monitoring_service import StartupPhase

# 创建启动监控服务实例
monitor = StartupMonitoringService()

# 开始监控阶段
monitor.start_phase(StartupPhase.INITIALIZATION)

# 添加阶段详情
monitor.add_phase_detail(
    StartupPhase.INITIALIZATION,
    'config_loading',
    {'config_file': 'app_config.json', 'status': 'success'}
)

# 结束监控阶段
monitor.end_phase(StartupPhase.INITIALIZATION)

# 生成启动报告
report = monitor.generate_startup_report()
```

## 日志分析和监控

### 日志查看工具

项目提供了多种日志查看和分析工具：

1. **实时日志监控**: 在主程序界面查看实时日志
2. **日志文件浏览**: 直接查看分类日志文件
3. **日志搜索**: 基于关键词和时间范围搜索日志
4. **日志统计**: 生成日志统计报告

### 常见问题诊断

通过日志分析可以快速诊断以下问题：

- 启动失败原因分析
- 依赖包安装问题
- 性能瓶颈识别
- 错误模式分析
- 资源使用异常

## 最佳实践

### 日志记录原则

1. **适度记录**: 记录关键操作和状态变化，避免过度记录
2. **结构化信息**: 使用结构化的日志消息格式
3. **敏感信息保护**: 避免记录密码、密钥等敏感信息
4. **性能考虑**: 在高频操作中合理控制日志级别

### 错误处理

1. **异常捕获**: 在异常处理中记录详细的错误信息
2. **上下文信息**: 记录错误发生时的上下文环境
3. **恢复策略**: 记录错误恢复的尝试和结果

### 性能监控

1. **关键路径**: 监控关键业务路径的执行时间
2. **资源使用**: 记录内存、CPU等资源使用情况
3. **瓶颈识别**: 通过日志分析识别性能瓶颈

## 维护和优化

### 日志清理

- 定期清理过期的日志文件
- 压缩和归档历史日志
- 监控日志目录的磁盘使用情况

### 性能优化

- 优化日志写入性能
- 合理配置日志缓冲区
- 避免同步日志写入阻塞主线程

### 配置调优

- 根据实际需求调整日志级别
- 优化日志轮转策略
- 配置合适的日志格式

## 故障排除

### 常见问题

1. **日志文件无法创建**
   - 检查目录权限
   - 确认磁盘空间充足
   - 验证路径配置正确

2. **日志记录缺失**
   - 检查日志级别配置
   - 确认日志记录器初始化
   - 验证日志过滤规则

3. **性能影响**
   - 调整日志级别
   - 优化日志格式
   - 使用异步日志写入

