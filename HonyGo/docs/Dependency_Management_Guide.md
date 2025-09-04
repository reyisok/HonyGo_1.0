# HonyGo 依赖管理指南

## 概述

HonyGo项目提供了完整的依赖管理解决方案，包括依赖分析、优化和自动安装工具。本指南将帮助您了解如何管理项目依赖。

## 依赖文件结构

### requirements.txt
生产环境依赖文件，包含项目运行所需的核心依赖包。

### requirements-dev.txt
开发环境依赖文件，包含开发和测试所需的额外依赖包。

## 依赖管理工具

### 1. 依赖分析器 (dependency_analyzer.py)

用于分析项目的实际依赖使用情况。

```bash
# 运行依赖分析
python tools/dependency_analyzer.py
```

**功能:**
- 解析requirements.txt中定义的包
- 扫描项目代码中实际使用的包
- 识别未使用的依赖
- 识别缺失的依赖
- 生成详细的分析报告

### 2. 依赖管理器 (dependency_manager.py)

高级依赖管理工具，提供自动检测和安装功能。

```bash
# 检查缺失的依赖
python tools/dependency_manager.py --check

# 检查缺失的依赖（包含开发依赖）
python tools/dependency_manager.py --check --dev

# 安装缺失的依赖
python tools/dependency_manager.py --install

# 自动检测并安装缺失的依赖
python tools/dependency_manager.py --auto

# 自动检测并安装缺失的依赖（包含开发依赖）
python tools/dependency_manager.py --auto --dev
```

**功能:**
- 检测缺失的依赖包
- 自动安装缺失的依赖
- 验证依赖版本兼容性
- 生成依赖安装报告
- 支持开发依赖管理

### 3. 快速安装脚本 (install_dependencies.py)

简化的依赖安装工具，用于快速安装项目依赖。

```bash
# 安装生产依赖
python tools/install_dependencies.py

# 安装生产依赖和开发依赖
python tools/install_dependencies.py --dev

# 仅安装开发依赖
python tools/install_dependencies.py --only-dev
```

**功能:**
- 快速安装requirements.txt中的依赖
- 支持开发依赖安装
- 简单易用的命令行界面

## 依赖优化说明

### 已移除的依赖

基于代码分析，以下依赖已从requirements.txt中移除（未在代码中使用）：

- `coloredlogs` - 日志着色库（未使用）
- `nvidia-ml-py` - NVIDIA GPU监控库（未使用）
- `pynput` - 输入设备控制库（未使用）
- `pytest` - 测试框架（移至开发依赖）
- `pytest-qt` - Qt测试工具（移至开发依赖）
- `pyyaml` - YAML配置文件处理（未使用）
- `torchvision` - 深度学习视觉库（未使用）

### 新增的依赖

基于代码分析，以下依赖已添加到requirements.txt中：

- `keyboard>=1.13.0` - 键盘事件处理
- `watchdog>=3.0.0` - 文件系统监控

### 开发依赖

以下依赖已移至requirements-dev.txt：

- `pytest>=7.4.0` - 测试框架
- `pytest-qt>=4.2.0` - Qt测试工具
- `coloredlogs>=15.0` - 日志着色（开发用）
- `pyyaml>=6.0` - YAML配置文件处理（开发用）
- `pynput>=1.7.6` - 输入设备控制（开发测试用）
- `nvidia-ml-py>=12.535.0` - GPU监控（开发调试用）
- `torchvision>=0.15.0` - 深度学习视觉（开发测试用）

## 使用建议

### 新环境部署

1. **仅生产环境:**
   ```bash
   python tools/install_dependencies.py
   ```

2. **开发环境:**
   ```bash
   python tools/install_dependencies.py --dev
   ```

### 依赖检查和维护

1. **定期运行依赖分析:**
   ```bash
   python tools/dependency_analyzer.py
   ```

2. **检查缺失依赖:**
   ```bash
   python tools/dependency_manager.py --check
   ```

3. **自动修复依赖问题:**
   ```bash
   python tools/dependency_manager.py --auto
   ```

### 故障排除

#### 依赖安装失败

1. 检查网络连接
2. 更新pip版本: `python -m pip install --upgrade pip`
3. 使用国内镜像源:
   ```bash
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
   ```

#### 版本冲突

1. 创建新的虚拟环境
2. 使用依赖管理器检查版本兼容性
3. 查看安装报告中的详细信息

