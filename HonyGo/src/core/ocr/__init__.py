#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR核心模块
统一管理所有OCR相关功能

@author: Mr.Rey Copyright © 2025
"""

# 核心OCR服务
# EasyOCRService已移除导出，仅供OCR池内部使用


__all__ = [
    # 核心服务
    'OCRPoolManager',
    'get_pool_manager',
    'shutdown_pool_manager',
    'OCRPoolService',
    'DynamicScalingManager',
    
    # 优化模块
    'GPUAccelerator',
    'ImagePreprocessor',
    'SmartRegionPredictor',
    'PerformanceOptimizer',
    'OCRCacheManager',
    'OptimizationConfigManager',
    
    # 工具模块
    'KeywordMatcher',
    'MatchStrategy',
    'OCRDownloadInterceptor',
    'get_logger',
    'ocr_logger',
    
    # 监控模块
    'PerformanceMonitor',
    'PerformanceDashboard',
]

# 版本信息
__version__ = '1.0.0'
__author__ = 'Mr.Rey Copyright © 2025'
__description__ = 'HonyGo OCR核心模块 - 统一管理所有OCR相关功能'