#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合OCR优化服务
整合截图优化和关键字优化，提供统一的OCR优化接口
@author: Mr.Rey Copyright © 2025
"""

from typing import (
    Any,
    Dict,
    List,
    Tuple,
    Union
)
import time

from dataclasses import dataclass
from enum import Enum

from src.config.ocr_logging_config import OCRLoggerMixin
from src.config.ocr_pool_validator import parameter_validator
from src.config.optimization_config_manager import OptimizationConfigManager
from src.core.ocr.services.keyword_ocr_optimizer import OCRTextResult, get_keyword_optimizer
from src.core.ocr.services.screenshot_ocr_optimizer import get_screenshot_optimizer
from src.ui.services.logging_service import get_logger
















class OptimizationMode(Enum):
    """
    优化模式枚举
    """
    SCREENSHOT_ONLY = "screenshot_only"          # 仅截图优化
    KEYWORD_ONLY = "keyword_only"                # 仅关键字优化
    COMPREHENSIVE = "comprehensive"              # 综合优化
    PERFORMANCE = "performance"                  # 性能优先
    ACCURACY = "accuracy"                        # 准确度优先


@dataclass
class OptimizationResult:
    """
    优化结果数据类
    """
    optimized_image: Union[str, bytes, Any] = None
    ocr_params: Dict[str, Any] = None
    processed_results: List[OCRTextResult] = None
    optimization_time: float = 0.0
    optimization_mode: OptimizationMode = OptimizationMode.COMPREHENSIVE
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.ocr_params is None:
            self.ocr_params = {}
        if self.processed_results is None:
            self.processed_results = []
        if self.performance_metrics is None:
            self.performance_metrics = {}


class ComprehensiveOCROptimizer(OCRLoggerMixin):
    """
    综合OCR优化器
    整合截图优化和关键字优化，提供统一的OCR优化接口
    """
    
    def __init__(self):
        # 初始化父类OCRLoggerMixin
        super().__init__()
        
        # 手动初始化_logger属性（防止多重继承问题）
        self._logger = None
        
        # 初始化OCR专用日志记录器（通过OCRLoggerMixin自动处理）
        
        # 保持向后兼容的日志记录器
        self._legacy_logger = get_logger("ComprehensiveOCROptimizer", "Application")
        self.config_manager = OptimizationConfigManager()
        self.config = self.config_manager.get_config()
        
        # 获取子优化器
        self.screenshot_optimizer = get_screenshot_optimizer()
        self.keyword_optimizer = get_keyword_optimizer()
        
        # 性能统计
        self.optimization_stats = {
            'total_optimizations': 0,
            'screenshot_optimizations': 0,
            'keyword_optimizations': 0,
            'average_optimization_time': 0.0,
            'success_rate': 1.0
        }
        
        self.log_info("综合OCR优化器初始化完成")
    
    @parameter_validator
    def optimize_for_screenshot_keyword_matching(self, 
                                               image_data: Union[str, bytes, Any],
                                               target_keywords: List[str] = None,
                                               mode: OptimizationMode = OptimizationMode.COMPREHENSIVE) -> OptimizationResult:
        """
        针对全屏截图+关键字匹配场景进行综合优化
        
        Args:
            image_data: 图像数据
            target_keywords: 目标关键字列表
            mode: 优化模式
            
        Returns:
            优化结果
        """
        start_time = time.time()
        
        try:
            self.log_info(f"开始综合OCR优化，模式: {mode.value}")
            
            result = OptimizationResult(optimization_mode=mode)
            
            # 1. 截图预处理优化
            if mode in [OptimizationMode.SCREENSHOT_ONLY, OptimizationMode.COMPREHENSIVE, 
                       OptimizationMode.ACCURACY]:
                optimized_image, ocr_params = self.screenshot_optimizer.optimize_screenshot_for_ocr(image_data)
                result.optimized_image = optimized_image
                result.ocr_params = ocr_params
                self.optimization_stats['screenshot_optimizations'] += 1
                self.log_debug("截图预处理优化完成")
            else:
                result.optimized_image = image_data
                result.ocr_params = self._get_basic_ocr_params()
            
            # 2. 根据模式调整OCR参数
            self._adjust_params_by_mode(result.ocr_params, mode)
            
            # 记录优化时间和统计
            optimization_time = time.time() - start_time
            result.optimization_time = optimization_time
            
            # 更新统计信息
            self._update_optimization_stats(optimization_time, True)
            
            # 记录性能指标
            result.performance_metrics = {
                'preprocessing_time': optimization_time,
                'image_size_reduction': self._calculate_size_reduction(image_data, result.optimized_image),
                'optimization_mode': mode.value,
                'target_keywords_count': len(target_keywords) if target_keywords else 0
            }
            
            self.log_performance("综合OCR优化", optimization_time, mode=mode.value)
            return result
            
        except Exception as e:
            optimization_time = time.time() - start_time
            self._update_optimization_stats(optimization_time, False)
            self.log_error(f"综合OCR优化失败: {e}")
            
            # 返回基础结果
            return OptimizationResult(
                optimized_image=image_data,
                ocr_params=self._get_basic_ocr_params(),
                optimization_time=optimization_time,
                optimization_mode=mode
            )
    
    @parameter_validator
    def post_process_ocr_results(self, 
                               ocr_results: List[Dict[str, Any]], 
                               target_keywords: List[str] = None,
                               mode: OptimizationMode = OptimizationMode.COMPREHENSIVE) -> List[OCRTextResult]:
        """
        后处理OCR结果
        
        Args:
            ocr_results: OCR原始结果
            target_keywords: 目标关键字列表
            mode: 优化模式
            
        Returns:
            处理后的OCR结果列表
        """
        try:
            self.log_debug(f"开始OCR结果后处理，模式: {mode.value}")
            
            # 关键字优化处理
            if mode in [OptimizationMode.KEYWORD_ONLY, OptimizationMode.COMPREHENSIVE, 
                       OptimizationMode.ACCURACY]:
                processed_results = self.keyword_optimizer.optimize_ocr_results_for_keywords(
                    ocr_results, target_keywords
                )
                self.optimization_stats['keyword_optimizations'] += 1
                self.log_debug("关键字优化处理完成")
            else:
                # 基础处理
                processed_results = self._basic_process_results(ocr_results)
            
            # 根据模式进行额外处理
            if mode == OptimizationMode.PERFORMANCE:
                processed_results = self._optimize_for_performance(processed_results)
            elif mode == OptimizationMode.ACCURACY:
                processed_results = self._optimize_for_accuracy(processed_results, target_keywords)
            
            self.log_debug(f"OCR结果后处理完成，处理了{len(processed_results)}个文本块")
            return processed_results
            
        except Exception as e:
            self.log_error(f"OCR结果后处理失败: {e}")
            return self._basic_process_results(ocr_results)
    
    @parameter_validator
    def get_optimized_ocr_params(self, 
                               mode: OptimizationMode = OptimizationMode.COMPREHENSIVE,
                               target_keywords: List[str] = None) -> Dict[str, Any]:
        """
        获取优化的OCR参数
        
        Args:
            mode: 优化模式
            target_keywords: 目标关键字列表
            
        Returns:
            优化的OCR参数字典
        """
        try:
            # 获取基础参数
            if mode in [OptimizationMode.SCREENSHOT_ONLY, OptimizationMode.COMPREHENSIVE]:
                params = self.screenshot_optimizer._get_screenshot_ocr_params()
            else:
                params = self._get_basic_ocr_params()
            
            # 根据模式调整参数
            self._adjust_params_by_mode(params, mode)
            
            # 根据关键字调整参数
            if target_keywords:
                self._adjust_params_for_keywords(params, target_keywords)
            
            return params
            
        except Exception as e:
            self.log_error(f"获取优化OCR参数失败: {e}")
            return self._get_basic_ocr_params()
    
    def _adjust_params_by_mode(self, params: Dict[str, Any], mode: OptimizationMode):
        """
        根据优化模式调整参数
        
        Args:
            params: OCR参数字典
            mode: 优化模式
        """
        try:
            if mode == OptimizationMode.PERFORMANCE:
                # 性能优先：降低精度，提高速度
                params.update({
                    'text_threshold': 0.8,
                    'low_text': 0.5,
                    'canvas_size': 1920,
                    'mag_ratio': 1.5,
                    'batch_size': max(params.get('batch_size', 1), 4),
                    'decoder': 'greedy',
                    'beamWidth': 3
                })
            
            elif mode == OptimizationMode.ACCURACY:
                # 准确度优先：提高精度，可能降低速度
                params.update({
                    'text_threshold': 0.5,
                    'low_text': 0.2,
                    'canvas_size': 3840,
                    'mag_ratio': 2.0,
                    'batch_size': 1,
                    'decoder': 'beamsearch',
                    'beamWidth': 12,
                    'min_size': 10,
                    'add_margin': 0.2
                })
            
            elif mode == OptimizationMode.COMPREHENSIVE:
                # 综合模式：平衡性能和准确度
                params.update({
                    'text_threshold': 0.6,
                    'low_text': 0.3,
                    'canvas_size': 2560,
                    'mag_ratio': 1.8,
                    'batch_size': 2,
                    'decoder': 'beamsearch',
                    'beamWidth': 8
                })
            
        except Exception as e:
            self.log_warning(f"参数模式调整失败: {e}")
    
    def _adjust_params_for_keywords(self, params: Dict[str, Any], keywords: List[str]):
        """
        根据关键字调整参数
        
        Args:
            params: OCR参数字典
            keywords: 关键字列表
        """
        try:
            # 如果关键字包含数字，调整数字识别参数
            has_numbers = any(any(c.isdigit() for c in keyword) for keyword in keywords)
            if has_numbers:
                params['text_threshold'] = min(params.get('text_threshold', 0.6), 0.5)
                params['min_size'] = min(params.get('min_size', 15), 12)
            
            # 如果关键字包含中文，调整中文识别参数
            has_chinese = any(any('\u4e00' <= c <= '\u9fff' for c in keyword) for keyword in keywords)
            if has_chinese:
                params['canvas_size'] = max(params.get('canvas_size', 2560), 2560)
                params['mag_ratio'] = max(params.get('mag_ratio', 1.8), 1.8)
            
            # 如果关键字很短，调整小文本检测参数
            has_short_keywords = any(len(keyword) <= 3 for keyword in keywords)
            if has_short_keywords:
                params['min_size'] = min(params.get('min_size', 15), 10)
                params['text_threshold'] = min(params.get('text_threshold', 0.6), 0.4)
            
        except Exception as e:
            self.log_warning(f"关键字参数调整失败: {e}")
    
    def _get_basic_ocr_params(self) -> Dict[str, Any]:
        """
        获取基础OCR参数
        
        Returns:
            基础OCR参数字典
        """
        try:
            # 从配置中获取基础参数
            if hasattr(self.config, 'easyocr_optimizations'):
                ocr_config = self.config.easyocr_optimizations
                return {
                    'text_threshold': ocr_config.text_threshold,
                    'low_text': ocr_config.low_text,
                    'link_threshold': ocr_config.link_threshold,
                    'canvas_size': ocr_config.canvas_size,
                    'mag_ratio': ocr_config.mag_ratio,
                    'min_size': ocr_config.min_size,
                    'decoder': ocr_config.decoder,
                    'beamWidth': ocr_config.beamWidth,
                    'batch_size': 1,
                    'detail': 1,
                    'paragraph': False
                }
            else:
                # 默认参数
                return {
                    'text_threshold': 0.7,
                    'low_text': 0.4,
                    'link_threshold': 0.4,
                    'canvas_size': 2560,
                    'mag_ratio': 1.5,
                    'min_size': 20,
                    'decoder': 'greedy',
                    'beamWidth': 5,
                    'batch_size': 1,
                    'detail': 1,
                    'paragraph': False
                }
        except Exception as e:
            self.log_warning(f"获取基础OCR参数失败: {e}")
            return {}
    
    def _basic_process_results(self, ocr_results: List[Dict[str, Any]]) -> List[OCRTextResult]:
        """
        基础处理OCR结果
        
        Args:
            ocr_results: OCR原始结果
            
        Returns:
            处理后的结果列表
        """
        try:
            processed_results = []
            
            for result in ocr_results:
                # 提取基本信息
                if isinstance(result, list) and len(result) >= 2:
                    bbox = result[0] if len(result[0]) == 4 else self._extract_bbox(result[0])
                    text = result[1]
                    confidence = result[2] if len(result) > 2 else 1.0
                elif isinstance(result, dict):
                    bbox = result.get('bbox', (0, 0, 0, 0))
                    text = result.get('text', '')
                    confidence = result.get('confidence', 1.0)
                else:
                    continue
                
                # 创建结果对象
                ocr_text_result = OCRTextResult(
                    text=text,
                    confidence=confidence,
                    bbox=bbox,
                    processed_text=text.strip()
                )
                
                processed_results.append(ocr_text_result)
            
            return processed_results
            
        except Exception as e:
            self.log_error(f"基础处理OCR结果失败: {e}")
            return []
    
    def _optimize_for_performance(self, results: List[OCRTextResult]) -> List[OCRTextResult]:
        """
        性能优化处理
        
        Args:
            results: OCR结果列表
            
        Returns:
            优化后的结果列表
        """
        try:
            # 过滤低置信度结果
            filtered_results = [r for r in results if r.confidence >= 0.6]
            
            # 限制结果数量
            max_results = self.config.performance.max_workers * 10
            if len(filtered_results) > max_results:
                # 按置信度排序，取前N个
                filtered_results.sort(key=lambda r: r.confidence, reverse=True)
                filtered_results = filtered_results[:max_results]
            
            return filtered_results
            
        except Exception as e:
            self.log_warning(f"性能优化处理失败: {e}")
            return results
    
    def _optimize_for_accuracy(self, results: List[OCRTextResult], keywords: List[str] = None) -> List[OCRTextResult]:
        """
        准确度优化处理
        
        Args:
            results: OCR结果列表
            keywords: 关键字列表
            
        Returns:
            优化后的结果列表
        """
        try:
            # 保留所有结果，包括低置信度的
            optimized_results = results.copy()
            
            # 如果有关键字，优先处理包含关键字的结果
            if keywords:
                keyword_results = [r for r in optimized_results if r.keyword_matches]
                non_keyword_results = [r for r in optimized_results if not r.keyword_matches]
                
                # 重新排序：关键字结果在前
                optimized_results = keyword_results + non_keyword_results
            
            return optimized_results
            
        except Exception as e:
            self.log_warning(f"准确度优化处理失败: {e}")
            return results
    
    def _calculate_size_reduction(self, original_data: Any, optimized_data: Any) -> float:
        """
        计算图像尺寸缩减比例
        
        Args:
            original_data: 原始图像数据
            optimized_data: 优化后图像数据
            
        Returns:
            缩减比例（0-1之间）
        """
        try:
            # 简单估算：基于数据长度
            if isinstance(original_data, str) and isinstance(optimized_data, str):
                original_size = len(original_data)
                optimized_size = len(optimized_data)
                if original_size > 0:
                    return 1.0 - (optimized_size / original_size)
            
            return 0.0
            
        except Exception as e:
            self.log_warning(f"尺寸缩减计算失败: {e}")
            return 0.0
    
    def _extract_bbox(self, bbox_data) -> Tuple[int, int, int, int]:
        """
        从各种格式的边界框数据中提取坐标
        
        Args:
            bbox_data: 边界框数据
            
        Returns:
            标准化的边界框坐标 (x1, y1, x2, y2)
        """
        try:
            if isinstance(bbox_data, (list, tuple)):
                if len(bbox_data) == 4:
                    return tuple(map(int, bbox_data))
                elif len(bbox_data) > 4:
                    # 可能是多点格式，取最小和最大坐标
                    x_coords = [point[0] for point in bbox_data if len(point) >= 2]
                    y_coords = [point[1] for point in bbox_data if len(point) >= 2]
                    if x_coords and y_coords:
                        return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
            
            return (0, 0, 0, 0)
            
        except Exception as e:
            self.log_warning(f"边界框提取失败: {e}")
            return (0, 0, 0, 0)
    
    def _update_optimization_stats(self, optimization_time: float, success: bool):
        """
        更新优化统计信息
        
        Args:
            optimization_time: 优化耗时
            success: 是否成功
        """
        try:
            self.optimization_stats['total_optimizations'] += 1
            
            # 更新平均优化时间
            total_count = self.optimization_stats['total_optimizations']
            current_avg = self.optimization_stats['average_optimization_time']
            new_avg = (current_avg * (total_count - 1) + optimization_time) / total_count
            self.optimization_stats['average_optimization_time'] = new_avg
            
            # 更新成功率
            if success:
                success_count = self.optimization_stats['success_rate'] * (total_count - 1) + 1
            else:
                success_count = self.optimization_stats['success_rate'] * (total_count - 1)
            
            self.optimization_stats['success_rate'] = success_count / total_count
            
        except Exception as e:
            self.log_warning(f"统计信息更新失败: {e}")
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """
        获取优化统计信息
        
        Returns:
            统计信息字典
        """
        return self.optimization_stats.copy()
    
    def reset_optimization_stats(self):
        """
        重置优化统计信息
        """
        self.optimization_stats = {
            'total_optimizations': 0,
            'screenshot_optimizations': 0,
            'keyword_optimizations': 0,
            'average_optimization_time': 0.0,
            'success_rate': 1.0
        }
        self.log_info("优化统计信息已重置")


# 全局实例
_comprehensive_optimizer_instance = None


def get_comprehensive_optimizer() -> ComprehensiveOCROptimizer:
    """
    获取综合OCR优化器实例（单例模式）
    
    Returns:
        ComprehensiveOCROptimizer实例
    """
    global _comprehensive_optimizer_instance
    if _comprehensive_optimizer_instance is None:
        _comprehensive_optimizer_instance = ComprehensiveOCROptimizer()
    return _comprehensive_optimizer_instance