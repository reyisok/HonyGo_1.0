#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HonyGo核心服务模块

提供系统级核心服务：
- 进程监控服务
- 信号处理服务
- Supervisor管理服务

@author: Mr.Rey Copyright © 2025
"""

__version__ = "1.0.0"
__author__ = "Mr.Rey"

# 导入核心服务


__all__ = [
    'ProcessMonitorService',
    'SignalHandlerService',
    # 'SupervisorManagerService'  # 已移除未使用的服务
    'ServiceRegistry',
    'get_service_registry',
    'auto_register_all_services'
]