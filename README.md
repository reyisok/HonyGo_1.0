# HonyGo System - Experimental Automation Tool

## Note

Unverified and unimplemented features in this project:

- OCR pool optimization and performance optimization (planned)
- Verification of simulation tasks under different DPI scaling scenarios
- Sorting issues with multiple simulated clicks
- Image similarity threshold verification and performance optimization (planned)
- Click animation optimization (planned)

## Project Overview

HonyGo System is an experimental automation tool developed with Python and PySide6, integrating OCR text recognition capabilities with intelligent region selection and automated operations. This system is designed specifically for personal learning and experimental purposes, providing a comprehensive platform for automation technology exploration.

## Core Features

- **Intelligent Region Selection**: Advanced screen region selection with OCR recognition
- **OCR Instance Pool**: Dynamic management of multiple OCR instances for improved processing efficiency
- **Automated Operations**: Intelligent mouse clicking based on OCR results
- **Real-time Monitoring**: System performance and OCR service status monitoring
- **Unified Logging**: Comprehensive logging with categorized storage
- **Offline Operation**: Complete offline functionality with local model support
- **Performance Optimization**: Advanced caching and resource management

## Technical Architecture

- **Frontend Interface**: PySide6 (Qt6 Python bindings)
- **OCR Engine**: EasyOCR with local model support
- **Image Processing**: OpenCV, Pillow
- **System Interaction**: PyAutoGUI, Pynput
- **Backend Services**: Flask (OCR pool service)
- **Performance Monitoring**: Real-time metrics and dashboard

## Project Structure

```
HonyGo/
├── src/
│   ├── config/                        # Configuration files
│   ├── core/                          # Core functionality modules
│   │   ├── ocr/                       # OCR-related modules
│   │   └── services/                  # Service modules
│   ├── ui/                            # User interface modules
│   └── data/
│       └── logs/                      # Log files
├── docs/                              # Project documentation
├── tests/                             # Test scripts
├── requirements.txt                   # Python dependencies
├── start_honygo.py                    # Project startup script
└── README.md                          # Project documentation
```

## Installation and Setup

### System Requirements

- Python 3.8 or higher
- Windows 10/11 (primary support)
- At least 4GB RAM (8GB recommended for OCR pool)
- 2GB available disk space for models

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Application

```bash
python start_honygo.py
```

### 3. OCR Pool Service

The OCR pool service starts automatically with the main application, listening on port 8900.

## User Guide

### Basic Operations

1. **Start Application**: Run the main program to open the control interface
2. **Region Selection**: Use the region selector to define screen monitoring areas
3. **OCR Recognition**: Perform text recognition on selected regions
4. **Automated Operations**: Configure and execute automated mouse operations

### OCR Pool Management

- **Instance Monitoring**: View active OCR instances and their status
- **Performance Metrics**: Monitor processing speed and resource usage
- **Dynamic Scaling**: Automatic scaling based on workload
- **Health Checks**: Regular service health monitoring

## Development and Testing

### Running Tests

```bash
# Basic functionality tests
cd tests
python test_basic.py

# OCR functionality tests
python test_ocr_basic.py
```

### Logging System

All logs are stored in categorized directories under `data/logs/`:

- `Application/` - Main application logs
- `OCR/` - OCR service and processing logs
- `System/` - System monitoring and performance logs
- `Error/` - Error and exception logs
- `Tests/` - Test execution logs
- `Performance/` - Performance metrics and monitoring
- `General/` - General system information

## Troubleshooting

### Common Issues

1. **OCR Service Connection Timeout**
   - Check if port 8900 is available
   - Verify OCR service is running
   - Review OCR service logs

2. **Model Loading Errors**
   - Ensure models exist in specified directory
   - Check model file integrity

3. **UI Response Issues**
   - Check system resource usage
   - Review application logs
   - Restart application if necessary

### Log Analysis

```bash
# View application logs
tail -f data/logs/Application/app_*.log

# View OCR service logs
tail -f data/logs/OCR/OCR_Pool_*.log

# View error logs
tail -f data/logs/Error/error_*.log
```

## Contributing

This is an experimental learning project. Contributions, suggestions, and feedback are welcome:

1. **Bug Reports**: Use detailed descriptions and include relevant logs
2. **Feature Requests**: Describe use cases and expected behavior
3. **Code Contributions**: Follow existing code standards and include tests
4. **Documentation**: Help improve documentation and examples

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author Information

@author: Mr.Rey Copyright © 2025

## Open Source Framework Acknowledgments

This project is built upon the following excellent open source frameworks and libraries. We express our sincere gratitude to all contributors:

### Core Frameworks

- **PySide6** (LGPL-3.0) - Qt6 Python bindings for modern GUI interfaces
- **EasyOCR** (Apache-2.0) - Powerful OCR text recognition engine
- **OpenCV** (Apache-2.0) - Computer vision and image processing library
- **PyTorch** (BSD-3-Clause) - Deep learning framework supporting OCR models
- **TensorFlow** (Apache-2.0) - Machine learning platform

### Image Processing

- **Pillow** (HPND) - Python image processing library
- **NumPy** (BSD-3-Clause) - Scientific computing foundation library

### System Interaction

- **PyAutoGUI** (BSD-3-Clause) - Automated GUI operations
- **psutil** (BSD-3-Clause) - System and process monitoring
- **pywin32** (PSF-2.0) - Windows API access
- **keyboard** (MIT) - Keyboard event handling
- **watchdog** (Apache-2.0) - File system monitoring

### Network and API

- **Flask** (BSD-3-Clause) - Lightweight web framework
- **Flask-CORS** (MIT) - Cross-origin resource sharing support
- **requests** (Apache-2.0) - HTTP library
- **urllib3** (MIT) - HTTP client

### System Monitoring

- **pynvml** (BSD-3-Clause) - NVIDIA GPU monitoring
- **GPUtil** (MIT) - GPU usage monitoring

### Utility Libraries

- **schedule** (MIT) - Task scheduling
- **jsonschema** (MIT) - JSON data validation
- **importlib-metadata** (Apache-2.0) - Package metadata access

### Development Tools

- **pytest** (MIT) - Testing framework
- **pytest-qt** (MIT) - Qt application testing support
- **PyYAML** (MIT) - YAML configuration file processing
- **torchvision** (BSD-3-Clause) - Computer vision tools
- **nvidia-ml-py** (BSD-3-Clause) - NVIDIA management library Python bindings

### License Compatibility Analysis

This project uses the MIT license and maintains good compatibility with all used open source frameworks:

- **Fully Compatible**: MIT, BSD-3-Clause, BSD-2-Clause, Apache-2.0, HPND, PSF-2.0 licenses
- **Compatible with Considerations**: LGPL-3.0 (PySide6) - Used as a dynamic link library, does not affect this project's MIT licensing

All dependency library licenses allow use in MIT projects, ensuring the project's open source compliance.

## Acknowledgments

Our sincere gratitude goes to all pioneers who have blazed trails in the technology field. As a beginner, it is by standing on your shoulders and drawing nourishment from the experiences and explorations of predecessors that I have been able to break through limitations in thinking and implement ideas into various functional modules in HonyGo System for learning and practice, giving the joy of technological exploration a vessel.

Special thanks to every user of HonyGo System. As an experimental system limited to personal learning purposes, its core value comes from your experiences and feedback.

Thanks to all contributors of the above open source projects. Without your selfless dedication, there would be no birth of HonyGo System.

Mr. Rey  
By HonyGo System Team (including AI Assistant)

---

# HonyGo System - 自动化操作实验性工具

## Note

本项目未经验证、未实现的功能：

- OCR池优化、及性能优化（计划实现）
- 模拟任务在其他DPI缩放场景下的验证
- 多次模拟点击的排序问题
- 图片相似度阈值验证、及性能优化（计划实现）
- 点击动画优化（计划实现）


## 项目简介

HonyGo System 是一个基于 Python 和 PySide6 开发的自动化操作实验性工具，集成了 OCR 文字识别功能，支持智能区域选择和自动化操作。该系统专为个人学习和实验目的设计，提供了一个全面的自动化技术探索平台。

## 核心功能

- **智能区域选择**: 高级屏幕区域选择与OCR识别
- **OCR实例池**: 动态管理多个OCR实例，提升处理效率
- **自动化操作**: 基于OCR结果的智能鼠标点击
- **实时监控**: 系统性能和OCR服务状态监控
- **统一日志**: 全面的日志记录与分类存储
- **离线运行**: 完整的离线功能，支持本地模型
- **性能优化**: 高级缓存和资源管理

## 技术架构

- **前端界面**: PySide6 (Qt6 Python绑定)
- **OCR引擎**: EasyOCR，支持本地模型
- **图像处理**: OpenCV, Pillow
- **系统交互**: PyAutoGUI, Pynput
- **后端服务**: Flask (OCR池服务)
- **性能监控**: 实时指标和仪表板

## 项目结构

```
HonyGo/
├── src/
│   ├── config/                        # 配置文件
│   ├── core/                          # 核心功能模块
│   │   ├── ocr/                       # OCR相关模块
│   │   └── services/                  # 服务模块
│   ├── ui/                            # 用户界面模块
│   └── data/
│       └── logs/                      # 日志文件
├── docs/                              # 项目文档
├── tests/                             # 测试脚本
├── requirements.txt                   # Python依赖
├── start_honygo.py                    # 项目启动脚本
└── README.md                          # 项目文档
```

## 安装和设置

### 系统要求

- Python 3.8 或更高版本
- Windows 10/11 (主要支持)
- 至少 4GB 内存 (推荐 8GB 用于OCR池)
- 2GB 可用磁盘空间用于模型

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动应用程序

```bash
python start_honygo.py
```

### 3. OCR池服务

OCR池服务会随主应用程序自动启动，监听端口8900。

## 使用指南

### 基本操作

1. **启动应用程序**: 运行主程序打开控制界面
2. **区域选择**: 使用区域选择器定义屏幕监控区域
3. **OCR识别**: 对选定区域执行文字识别
4. **自动化操作**: 配置并执行自动化鼠标操作

### OCR池管理

- **实例监控**: 查看活跃OCR实例及其状态
- **性能指标**: 监控处理速度和资源使用情况
- **动态扩容**: 基于工作负载的自动扩容
- **健康检查**: 定期服务健康监控

## 开发和测试

### 运行测试

```bash
# 基础功能测试
cd tests
python test_basic.py

# OCR功能测试
python test_ocr_basic.py
```

### 日志系统

所有日志存储在 `data/logs/` 目录下的分类目录中：

- `Application/` - 主应用程序日志
- `OCR/` - OCR服务和处理日志
- `System/` - 系统监控和性能日志
- `Error/` - 错误和异常日志
- `Tests/` - 测试执行日志
- `Performance/` - 性能指标和监控
- `General/` - 一般系统信息

## 故障排除

### 常见问题

1. **OCR服务连接超时**
   - 检查端口8900是否可用
   - 验证OCR服务是否运行
   - 查看OCR服务日志

2. **模型加载错误**
   - 确保模型存在于指定目录
   - 检查模型文件完整性

3. **UI响应问题**
   - 检查系统资源使用情况
   - 查看应用程序日志
   - 必要时重启应用程序

### 日志分析

```bash
# 查看应用程序日志
tail -f data/logs/Application/app_*.log

# 查看OCR服务日志
tail -f data/logs/OCR/OCR_Pool_*.log

# 查看错误日志
tail -f data/logs/Error/error_*.log
```

## 贡献

这是一个实验性学习项目。欢迎贡献、建议和反馈：

1. **错误报告**: 使用详细描述并包含相关日志
2. **功能请求**: 描述用例和预期行为
3. **代码贡献**: 遵循现有代码标准并包含测试
4. **文档**: 帮助改进文档和示例

## 许可证

本项目采用MIT许可证 - 详见LICENSE文件。

## 作者信息

@author: Mr.Rey Copyright © 2025

## 开源框架致谢

本项目基于以下优秀的开源框架和库构建，在此向所有贡献者表示诚挚的感谢：

### 核心框架

- **PySide6** (LGPL-3.0) - Qt6 Python绑定，提供现代化GUI界面
- **EasyOCR** (Apache-2.0) - 强大的OCR文字识别引擎
- **OpenCV** (Apache-2.0) - 计算机视觉和图像处理库
- **PyTorch** (BSD-3-Clause) - 深度学习框架，支持OCR模型
- **TensorFlow** (Apache-2.0) - 机器学习平台

### 图像处理

- **Pillow** (HPND) - Python图像处理库
- **NumPy** (BSD-3-Clause) - 科学计算基础库

### 系统交互

- **PyAutoGUI** (BSD-3-Clause) - 自动化GUI操作
- **psutil** (BSD-3-Clause) - 系统和进程监控
- **pywin32** (PSF-2.0) - Windows API访问
- **keyboard** (MIT) - 键盘事件处理
- **watchdog** (Apache-2.0) - 文件系统监控

### 网络和API

- **Flask** (BSD-3-Clause) - 轻量级Web框架
- **Flask-CORS** (MIT) - 跨域资源共享支持
- **requests** (Apache-2.0) - HTTP库
- **urllib3** (MIT) - HTTP客户端

### 系统监控

- **pynvml** (BSD-3-Clause) - NVIDIA GPU监控
- **GPUtil** (MIT) - GPU使用情况监控

### 工具库

- **schedule** (MIT) - 任务调度
- **jsonschema** (MIT) - JSON数据验证
- **importlib-metadata** (Apache-2.0) - 包元数据访问

### 开发工具

- **pytest** (MIT) - 测试框架
- **pytest-qt** (MIT) - Qt应用测试支持
- **PyYAML** (MIT) - YAML配置文件处理
- **torchvision** (BSD-3-Clause) - 计算机视觉工具
- **nvidia-ml-py** (BSD-3-Clause) - NVIDIA管理库Python绑定

### 授权兼容性分析

本项目采用MIT许可证，与所有使用的开源框架保持良好的兼容性：

- **完全兼容**: MIT、BSD-3-Clause、BSD-2-Clause、Apache-2.0、HPND、PSF-2.0许可证
- **兼容但需注意**: LGPL-3.0 (PySide6) - 作为动态链接库使用，不影响本项目的MIT授权

所有依赖库的许可证都允许在MIT项目中使用，确保了项目的开源合规性。

## 致谢

向所有在技术领域披荆斩棘的先驱者致以最诚挚的谢意。作为一名初学者，正是承蒙站在你们的肩膀上，从前人的经验与探索中汲取养分，我才得以突破思路局限，将想法落地为 HonyGo System 中各类用于学习实践的功能模块，让技术探索的乐趣有了承载。

特别感谢每一位使用 HonyGo System 的用户。作为一款仅限个人学习用途的实验性系统，它的核心价值正来源于你们的体验与反馈。

感谢上述所有开源项目的贡献者们，没有你们的无私奉献，就没有 HonyGo System 的诞生。

Mr. Rey  
By HonyGo System 团队（包含 AI 助手）
