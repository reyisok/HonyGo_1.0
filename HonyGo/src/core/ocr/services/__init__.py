# -*- coding: utf-8 -*-
"""
OCR服务模块

包含OCR相关的核心服务组件：
- EasyOCR服务
- OCR池管理器
- OCR池服务
- 动态扩容管理器

@author: Mr.Rey Copyright © 2025
"""

__version__ = "1.0.0"
__author__ = "Mr.Rey"

# 导入主要服务类
# EasyOCRService已移除导出，仅供OCR池内部使用


__all__ = [
    'OCRPoolManager', 
    'OCRPoolService',
    'DynamicScalingManager'
]