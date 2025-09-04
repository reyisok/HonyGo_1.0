#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HonyGo核心模块

包含项目的核心业务逻辑和服务：
- OCR相关功能和服务
- 系统服务（进程监控、信号处理、supervisor管理）
- 数据管理和缓存

@author: Mr.Rey Copyright © 2025
"""

__version__ = "1.0.0"
__author__ = "Mr.Rey"

# 导入核心服务

# from src.services.supervisor_manager_service import SupervisorManagerService  # 已移除未使用的服务

# OCR模块通过相对导入或按需导入
# from . import ocr  # 如需要可以使用相对导入

__all__ = [
    'ProcessMonitorService',
    'SignalHandlerService', 
    # 'SupervisorManagerService',  # 已移除未使用的服务
    # 'ocr'  # 移除以避免循环导入
]