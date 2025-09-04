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