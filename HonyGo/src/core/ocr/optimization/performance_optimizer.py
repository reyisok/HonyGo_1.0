#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR性能优化服务模块

@author: Mr.Rey Copyright © 2025
@description: 统一管理OCR性能优化功能，包括智能区域预测、图像预处理、结果缓存等
@version: 1.0.0
@created: 2025-01-31
@modified: 2025-01-31
"""

import base64
import hashlib
import io
import json
import os
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image

from src.config.ocr_logging_config import OCRLoggerMixin, log_ocr_operation
from src.config.ocr_pool_validator import parameter_validator
from src.config.optimization_config_manager import OptimizationConfigManager
from src.core.ocr.optimization.image_preprocessor import ImagePreprocessor as FullImagePreprocessor
from src.core.ocr.optimization.ocr_cache_manager import OCRCacheManager
from src.core.ocr.optimization.smart_region_predictor import SmartRegionPredictor
from src.core.ocr.services.ocr_pool_manager import get_pool_manager
from src.core.ocr.utils.ocr_logger import get_logger


class OptimizationStrategy(Enum):
    """优化策略枚举"""
    SPEED = "speed"  # 速度优先
    ACCURACY = "accuracy"  # 准确度优先
    BALANCED = "balanced"  # 平衡模式
    CUSTOM = "custom"  # 自定义模式


class ProcessingStage(Enum):
    """处理阶段枚举"""
    PREPROCESSING = "preprocessing"
    REGION_PREDICTION = "region_prediction"
    OCR_RECOGNITION = "ocr_recognition"
    RESULT_CACHING = "result_caching"
    POST_PROCESSING = "post_processing"


@dataclass
class OptimizationResult:
    """优化结果数据类"""
    image_hash: str
    preprocessed_image: Optional[np.ndarray] = None
    predicted_regions: Optional[List[Dict[str, Any]]] = None
    ocr_results: Optional[List[Dict[str, Any]]] = None
    processing_time: float = 0.0
    cache_hit: bool = False
    optimization_applied: List[str] = None
    
    def __post_init__(self):
        if self.optimization_applied is None:
            self.optimization_applied = []


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_processing_time: float = 0.0
    preprocessing_time: float = 0.0
    region_prediction_time: float = 0.0
    ocr_recognition_time: float = 0.0
    post_processing_time: float = 0.0
    
    @property
    def cache_hit_rate(self) -> float:
        """缓存命中率"""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


class PerformanceOptimizer(OCRLoggerMixin):
    """OCR性能优化器
    
    统一管理OCR性能优化功能，包括：
    - 智能区域预测
    - 图像预处理
    - 结果缓存
    - 性能监控
    """
    
    def __init__(self, config_manager: Optional[OptimizationConfigManager] = None):
        """初始化性能优化器
        
        Args:
            config_manager: 优化配置管理器，如果为None则使用默认配置
        """
        super().__init__()
        
        # 配置管理
        self.config_manager = config_manager or OptimizationConfigManager()
        
        # 从统一配置中提取性能优化配置
        try:
            optimization_config = self.config_manager.get_optimization_config()
            self.performance_config = optimization_config.get('performance_optimizer', {
                'strategy': 'balanced',
                'enable_preprocessing': True,
                'enable_region_prediction': True,
                'enable_result_caching': True,
                'enable_parallel_processing': False,
                'max_workers': 4,
                'timeout_seconds': 30,
                'quality_threshold': 0.8,
                'performance_monitoring': {
                    'enable_metrics': True,
                    'metrics_interval': 60,
                    'log_performance': True
                }
            })
        except Exception as e:
            self.log_error(f"加载性能优化配置失败，使用默认配置: {e}")
            self.performance_config = {
                'strategy': 'balanced',
                'enable_preprocessing': True,
                'enable_region_prediction': True,
                'enable_result_caching': True,
                'enable_parallel_processing': False,
                'max_workers': 4,
                'timeout_seconds': 30,
                'quality_threshold': 0.8,
                'performance_monitoring': {
                    'enable_metrics': True,
                    'metrics_interval': 60,
                    'log_performance': True
                }
            }
        
        # 初始化组件
        self._initialize_components()
        
        # 性能指标
        self.metrics = PerformanceMetrics()
        
        self.log_info("性能优化器初始化完成")
    
    def _initialize_components(self):
        """初始化优化组件"""
        try:
            # 图像预处理器
            if self.performance_config.get('enable_preprocessing', True):
                self.image_preprocessor = FullImagePreprocessor(self.config_manager)
                self.log_info("图像预处理器初始化完成")
            else:
                self.image_preprocessor = None
                self.log_info("图像预处理器已禁用")
            
            # 智能区域预测器
            if self.performance_config.get('enable_region_prediction', True):
                self.region_predictor = SmartRegionPredictor(self.config_manager)
                self.log_info("智能区域预测器初始化完成")
            else:
                self.region_predictor = None
                self.log_info("智能区域预测器已禁用")
            
            # 结果缓存管理器
            if self.performance_config.get('enable_result_caching', True):
                self.result_cache = OCRCacheManager(self.config_manager)
                self.log_info("结果缓存管理器初始化完成")
            else:
                self.result_cache = None
                self.log_info("结果缓存已禁用")
                
        except Exception as e:
            self.log_error(f"初始化优化组件失败: {e}")
            raise
    
    @log_ocr_operation("性能优化识别")
    @parameter_validator
    def optimize_ocr_recognition(self, 
                               image_data: Union[str, bytes, np.ndarray], 
                               target_text: Optional[str] = None,
                               strategy: Optional[OptimizationStrategy] = None) -> Optional[List[Dict[str, Any]]]:
        """执行优化的OCR识别
        
        Args:
            image_data: 图像数据（base64字符串、字节数据或numpy数组）
            target_text: 目标文本（可选）
            strategy: 优化策略（可选）
            
        Returns:
            OCR识别结果列表
        """
        start_time = time.time()
        
        try:
            # 更新请求计数
            self.metrics.total_requests += 1
            
            # 预处理图像数据
            optimization_result = self._preprocess_image(image_data)
            if not optimization_result:
                return None
            
            # 检查缓存
            if self.result_cache:
                cached_result = self.result_cache.get_cached_result(
                    optimization_result.image_hash, target_text
                )
                if cached_result:
                    self.metrics.cache_hits += 1
                    optimization_result.cache_hit = True
                    optimization_result.ocr_results = cached_result
                    self.log_info(f"缓存命中，返回缓存结果")
                    return cached_result
                else:
                    self.metrics.cache_misses += 1
            
            # 智能区域预测
            if self.region_predictor and optimization_result.preprocessed_image is not None:
                region_start = time.time()
                predicted_regions = self.region_predictor.predict_text_regions(
                    optimization_result.preprocessed_image
                )
                self.metrics.region_prediction_time += time.time() - region_start
                optimization_result.predicted_regions = predicted_regions
                optimization_result.optimization_applied.append("region_prediction")
            
            # 准备OCR识别的图像数据
            image_base64 = self._prepare_image_for_ocr(optimization_result)
            if not image_base64:
                return None
            
            # 执行OCR识别
            ocr_start = time.time()
            ocr_results = self._perform_ocr_recognition(image_base64, target_text)
            self.metrics.ocr_recognition_time += time.time() - ocr_start
            
            if ocr_results:
                optimization_result.ocr_results = ocr_results
                
                # 缓存结果
                if self.result_cache:
                    self.result_cache.cache_result(
                        optimization_result.image_hash,
                        target_text,
                        ocr_results
                    )
                
                # 更新性能指标
                total_time = time.time() - start_time
                optimization_result.processing_time = total_time
                self._update_performance_metrics(total_time)
                
                self.log_info(f"OCR优化识别完成，耗时: {total_time:.3f}秒，结果数量: {len(ocr_results)}")
                return ocr_results
            else:
                self.log_warning("OCR识别未返回结果")
                return None
                
        except Exception as e:
            self.log_error(f"OCR优化识别失败: {e}")
            return None
    
    def _preprocess_image(self, image_data: Union[str, bytes, np.ndarray]) -> Optional[OptimizationResult]:
        """预处理图像数据
        
        Args:
            image_data: 图像数据
            
        Returns:
            优化结果对象
        """
        try:
            # 转换图像数据为numpy数组
            if isinstance(image_data, str):
                # base64字符串
                image_bytes = base64.b64decode(image_data)
                image_array = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
            elif isinstance(image_data, bytes):
                # 字节数据
                image_array = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
            elif isinstance(image_data, np.ndarray):
                # numpy数组
                image_array = image_data.copy()
            else:
                self.log_error(f"不支持的图像数据类型: {type(image_data)}")
                return None
            
            if image_array is None:
                self.log_error("图像数据解码失败")
                return None
            
            # 计算图像哈希
            image_hash = self._calculate_image_hash(image_array)
            
            # 创建优化结果对象
            result = OptimizationResult(image_hash=image_hash)
            
            # 图像预处理
            if self.image_preprocessor:
                preprocess_start = time.time()
                preprocessed = self.image_preprocessor.preprocess(image_array)
                self.metrics.preprocessing_time += time.time() - preprocess_start
                
                if preprocessed is not None:
                    result.preprocessed_image = preprocessed
                    result.optimization_applied.append("preprocessing")
                else:
                    result.preprocessed_image = image_array
            else:
                result.preprocessed_image = image_array
            
            return result
            
        except Exception as e:
            self.log_error(f"图像预处理失败: {e}")
            return None
    
    def _calculate_image_hash(self, image: np.ndarray) -> str:
        """计算图像哈希值
        
        Args:
            image: 图像数组
            
        Returns:
            图像哈希值
        """
        try:
            # 使用图像内容计算MD5哈希
            image_bytes = cv2.imencode('.jpg', image)[1].tobytes()
            return hashlib.md5(image_bytes).hexdigest()
        except Exception as e:
            self.log_error(f"计算图像哈希失败: {e}")
            return str(hash(image.tobytes()))
    
    def _prepare_image_for_ocr(self, optimization_result: OptimizationResult) -> Optional[str]:
        """为OCR识别准备图像数据
        
        Args:
            optimization_result: 优化结果对象
            
        Returns:
            base64编码的图像数据
        """
        try:
            if optimization_result.preprocessed_image is None:
                return None
            
            # 将图像编码为base64
            _, buffer = cv2.imencode('.jpg', optimization_result.preprocessed_image)
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return image_base64
            
        except Exception as e:
            self.log_error(f"准备OCR图像数据失败: {e}")
            return None
    
    def _perform_ocr_recognition(self, image_base64: str, target_text: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """执行OCR识别
        
        Args:
            image_base64: base64编码的图像数据
            target_text: 目标文本
            
        Returns:
            OCR识别结果
        """
        try:
            # 获取OCR池管理器
            try:
                pool_manager = get_pool_manager()
            except ImportError:
                self.log_error("无法导入OCR池管理器")
                return None
            
            # 直接调用OCR池管理器进行识别
            ocr_results = pool_manager.process_ocr_request(
                image_data=image_base64,
                request_type="recognize",
                keywords=[target_text] if target_text else []
            )
            
            return ocr_results
            
        except Exception as e:
            self.log_error(f"OCR识别失败: {e}")
            return None
    
    def _update_performance_metrics(self, processing_time: float):
        """更新性能指标
        
        Args:
            processing_time: 处理时间
        """
        try:
            # 更新平均处理时间
            total_time = self.metrics.average_processing_time * (self.metrics.total_requests - 1)
            self.metrics.average_processing_time = (total_time + processing_time) / self.metrics.total_requests
            
            # 记录性能日志
            if self.performance_config.get('performance_monitoring', {}).get('log_performance', True):
                self.log_info(f"性能指标更新 - 平均处理时间: {self.metrics.average_processing_time:.3f}秒, "
                            f"缓存命中率: {self.metrics.cache_hit_rate:.2%}")
                
        except Exception as e:
            self.log_warning(f"更新性能指标失败: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息
        
        Returns:
            性能统计信息字典
        """
        try:
            stats = {
                'total_requests': self.metrics.total_requests,
                'cache_hits': self.metrics.cache_hits,
                'cache_misses': self.metrics.cache_misses,
                'cache_hit_rate': self.metrics.cache_hit_rate,
                'average_processing_time': self.metrics.average_processing_time,
                'preprocessing_time': self.metrics.preprocessing_time,
                'region_prediction_time': self.metrics.region_prediction_time,
                'ocr_recognition_time': self.metrics.ocr_recognition_time,
                'post_processing_time': self.metrics.post_processing_time
            }
            
            # 添加组件统计信息
            if self.result_cache and hasattr(self.result_cache, 'get_stats'):
                stats['cache_stats'] = self.result_cache.get_stats()
            
            if self.region_predictor and hasattr(self.region_predictor, 'get_stats'):
                stats['region_predictor_stats'] = self.region_predictor.get_stats()
            
            if self.image_preprocessor and hasattr(self.image_preprocessor, 'get_stats'):
                stats['preprocessor_stats'] = self.image_preprocessor.get_stats()
            
            return stats
            
        except Exception as e:
            self.log_warning(f"获取性能统计信息失败: {e}")
            return {}
    
    def reset_metrics(self):
        """重置性能指标"""
        try:
            self.metrics = PerformanceMetrics()
            self.log_info("性能指标已重置")
        except Exception as e:
            self.log_error(f"重置性能指标失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.result_cache:
                self.result_cache.cleanup()
            
            if self.region_predictor and hasattr(self.region_predictor, 'cleanup'):
                self.region_predictor.cleanup()
            
            if self.image_preprocessor and hasattr(self.image_preprocessor, 'cleanup'):
                self.image_preprocessor.cleanup()
            
            self.log_info("性能优化器资源清理完成")
            
        except Exception as e:
            self.log_error(f"清理资源失败: {e}")