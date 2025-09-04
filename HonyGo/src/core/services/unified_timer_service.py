#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一定时器服务桥接模块
将ui.services.unified_timer_service中的功能重新导出

@author: Mr.Rey Copyright © 2025
@created 2024-07-03 15:30
@modified 2024-07-03 15:30
@version 1.0
"""

# 从ui.services导入统一定时器服务
from src.ui.services.unified_timer_service import TimerTask
from src.ui.services.unified_timer_service import UnifiedTimerService
from src.ui.services.unified_timer_service import get_timer_service

# 重新导出所有内容
__all__ = ['UnifiedTimerService', 'get_timer_service', 'TimerTask']