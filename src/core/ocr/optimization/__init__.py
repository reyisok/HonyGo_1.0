# -*- coding: utf-8 -*-
"""
OCR优化模块

包含OCR性能优化相关组件：
- 性能优化器
- GPU加速器
- 图像预处理器
- 智能区域预测器
- OCR缓存管理器

@author: Mr.Rey Copyright © 2025
@created: 2025-01-31
@modified: 2025-01-31
@version: 1.0.0
"""

import logging
from typing import Optional

from src.core.ocr.utils.ocr_logger import get_logger

__version__ = "1.0.0"
__author__ = "Mr.Rey"

# 获取日志记录器
logger = get_logger(__name__)

# 导入主要优化类
try:
    from src.core.ocr.optimization.performance_optimizer import PerformanceOptimizer
    PERFORMANCE_OPTIMIZER_AVAILABLE = True
    logger.info("性能优化器模块导入成功")
except ImportError as e:
    PerformanceOptimizer = None
    PERFORMANCE_OPTIMIZER_AVAILABLE = False
    logger.error(f"性能优化器导入失败: {e}")

try:
    from src.core.ocr.optimization.image_preprocessor import ImagePreprocessor
    IMAGE_PREPROCESSOR_AVAILABLE = True
    logger.info("图像预处理器模块导入成功")
except ImportError as e:
    ImagePreprocessor = None
    IMAGE_PREPROCESSOR_AVAILABLE = False
    logger.error(f"图像预处理器导入失败: {e}")

try:
    from src.core.ocr.optimization.smart_region_predictor import SmartRegionPredictor
    SMART_REGION_PREDICTOR_AVAILABLE = True
    logger.info("智能区域预测器模块导入成功")
except ImportError as e:
    SmartRegionPredictor = None
    SMART_REGION_PREDICTOR_AVAILABLE = False
    logger.error(f"智能区域预测器导入失败: {e}")

try:
    from src.core.ocr.optimization.ocr_cache_manager import OCRCacheManager
    OCR_CACHE_MANAGER_AVAILABLE = True
    logger.info("OCR缓存管理器模块导入成功")
except ImportError as e:
    OCRCacheManager = None
    OCR_CACHE_MANAGER_AVAILABLE = False
    logger.error(f"OCR缓存管理器导入失败: {e}")

try:
    from src.core.ocr.optimization.gpu_accelerator import GPUAccelerator
    GPU_ACCELERATOR_AVAILABLE = True
    logger.info("GPU加速器模块导入成功")
except ImportError as e:
    GPUAccelerator = None
    GPU_ACCELERATOR_AVAILABLE = False
    logger.warning(f"GPU加速器不可用: {e}")
    logger.info("GPU加速功能将被禁用，系统将使用CPU模式运行")

# 构建可用模块列表
__all__ = []

if PERFORMANCE_OPTIMIZER_AVAILABLE:
    __all__.append('PerformanceOptimizer')

if IMAGE_PREPROCESSOR_AVAILABLE:
    __all__.append('ImagePreprocessor')

if SMART_REGION_PREDICTOR_AVAILABLE:
    __all__.append('SmartRegionPredictor')

if OCR_CACHE_MANAGER_AVAILABLE:
    __all__.append('OCRCacheManager')

if GPU_ACCELERATOR_AVAILABLE:
    __all__.append('GPUAccelerator')

# 模块可用性状态
MODULE_STATUS = {
    'performance_optimizer': PERFORMANCE_OPTIMIZER_AVAILABLE,
    'image_preprocessor': IMAGE_PREPROCESSOR_AVAILABLE,
    'smart_region_predictor': SMART_REGION_PREDICTOR_AVAILABLE,
    'ocr_cache_manager': OCR_CACHE_MANAGER_AVAILABLE,
    'gpu_accelerator': GPU_ACCELERATOR_AVAILABLE
}


def get_available_modules():
    """获取可用的优化模块列表
    
    Returns:
        List[str]: 可用模块名称列表
    """
    return [name for name, available in MODULE_STATUS.items() if available]


def is_module_available(module_name: str) -> bool:
    """检查指定模块是否可用
    
    Args:
        module_name: 模块名称
        
    Returns:
        bool: 模块是否可用
    """
    return MODULE_STATUS.get(module_name, False)


def get_optimization_summary():
    """获取优化模块状态摘要
    
    Returns:
        Dict: 模块状态摘要
    """
    available_count = sum(1 for available in MODULE_STATUS.values() if available)
    total_count = len(MODULE_STATUS)
    
    return {
        'total_modules': total_count,
        'available_modules': available_count,
        'unavailable_modules': total_count - available_count,
        'availability_rate': available_count / total_count if total_count > 0 else 0.0,
        'module_status': MODULE_STATUS.copy(),
        'available_module_names': get_available_modules()
    }


# 记录模块初始化状态
summary = get_optimization_summary()
logger.info(f"OCR优化模块初始化完成: {summary['available_modules']}/{summary['total_modules']} 个模块可用")
logger.info(f"可用模块: {', '.join(summary['available_module_names'])}")

if summary['unavailable_modules'] > 0:
    unavailable = [name for name, available in MODULE_STATUS.items() if not available]
    logger.warning(f"不可用模块: {', '.join(unavailable)}")