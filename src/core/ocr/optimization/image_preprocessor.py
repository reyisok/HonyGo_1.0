#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像预处理模块

@author: Mr.Rey Copyright © 2025
@description: 提供图像预处理功能，包括裁剪、降噪、二值化、对比度增强等，减少OCR工作量
@version: 1.0.0
@created: 2025-01-31
@modified: 2025-09-03
"""

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

from src.config.optimization_config_manager import OptimizationConfigManager
from src.core.ocr.utils.ocr_logger import get_logger


class PreprocessingMethod(Enum):
    """预处理方法枚举"""
    RESIZE = "resize"
    DENOISE = "denoise"
    BINARIZATION = "binarization"
    CONTRAST_ENHANCEMENT = "contrast_enhancement"
    BRIGHTNESS_ADJUSTMENT = "brightness_adjustment"
    SHARPENING = "sharpening"
    ROTATION_CORRECTION = "rotation_correction"
    TEXT_REGION_EXTRACTION = "text_region_extraction"
    BACKGROUND_REMOVAL = "background_removal"


class PreprocessingStrategy(Enum):
    """预处理策略枚举"""
    AUTO = "auto"  # 自动选择最佳预处理方法
    FAST = "fast"  # 快速预处理，优先速度
    QUALITY = "quality"  # 高质量预处理，优先效果
    BALANCED = "balanced"  # 平衡速度和质量
    CUSTOM = "custom"  # 自定义预处理流程


@dataclass
class PreprocessingResult:
    """预处理结果数据类"""
    processed_image: np.ndarray
    original_image: np.ndarray
    processing_time: float
    methods_applied: List[str]
    quality_score: float
    metadata: Dict[str, Any]


class ImagePreprocessor:
    """图像预处理器类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化图像预处理器
        
        Args:
            config: 预处理配置字典
        """
        self.logger = get_logger(__name__)
        self.config = config or self._load_unified_config()
        self.logger.info("图像预处理器初始化完成")
    
    def _load_unified_config(self) -> Dict[str, Any]:
        """
        从统一优化配置管理器加载配置
        
        Returns:
            配置字典
        """
        try:
            self.config_manager = OptimizationConfigManager()
            
            # 获取统一优化配置
            unified_config = self.config_manager.get_config()
            
            # 提取图像预处理配置
            image_preprocessing_config = unified_config.image_preprocessing if hasattr(unified_config, 'image_preprocessing') else {}
            
            # 转换为图像预处理器所需的格式
            config = {
                'preprocessing': {
                    'auto_mode': True,
                    'quality_threshold': 0.7,
                    'max_processing_time': 5.0,
                    'preserve_aspect_ratio': True
                },
                'resize': {
                    'enabled': getattr(image_preprocessing_config, 'resize_enabled', True),
                    'max_width': getattr(image_preprocessing_config, 'max_width', 1920),
                    'max_height': getattr(image_preprocessing_config, 'max_height', 1080),
                    'min_width': 100,
                    'min_height': 100,
                    'scale_factor': 1.0,
                    'interpolation': 'INTER_CUBIC'
                },
                'denoise': {
                    'enabled': getattr(image_preprocessing_config, 'noise_reduction', True),
                    'method': 'fastNlMeansDenoising',
                    'h': 10,
                    'template_window_size': 7,
                    'search_window_size': 21
                },
                'binarization': {
                    'enabled': getattr(image_preprocessing_config, 'binarization_enabled', False),
                    'method': 'adaptive_threshold',
                    'threshold_value': 127,
                    'adaptive_method': 'ADAPTIVE_THRESH_GAUSSIAN_C',
                    'threshold_type': 'THRESH_BINARY',
                    'block_size': 11,
                    'c_constant': 2
                },
                'contrast_enhancement': {
                    'enabled': getattr(image_preprocessing_config, 'contrast_enhancement', True),
                    'method': 'clahe',
                    'clip_limit': 2.0,
                    'tile_grid_size': [8, 8],
                    'gamma_correction': 1.0
                },
                'brightness_adjustment': {
                    'enabled': False,
                    'auto_adjust': True,
                    'brightness_factor': 1.0,
                    'target_mean': 128
                },
                'sharpening': {
                    'enabled': False,
                    'method': 'unsharp_mask',
                    'kernel_size': 3,
                    'sigma': 1.0,
                    'amount': 1.0,
                    'threshold': 0
                },
                'rotation_correction': {
                    'enabled': False,
                    'auto_detect': True,
                    'angle_threshold': 0.5,
                    'max_angle': 45
                },
                'text_region_extraction': {
                    'enabled': False,
                    'method': 'mser',
                    'min_area': 100,
                    'max_area': 10000,
                    'padding': 5
                },
                'background_removal': {
                    'enabled': False,
                    'method': 'grabcut',
                    'iterations': 5
                }
            }
            
            self.logger.info("图像预处理配置已从统一优化配置加载")
            return config
            
        except Exception as e:
            self.logger.error(f"加载统一配置失败: {e}，使用默认配置")
            # 返回默认配置
            return {
                'preprocessing': {
                    'auto_mode': True,
                    'quality_threshold': 0.7,
                    'max_processing_time': 5.0,
                    'preserve_aspect_ratio': True
                },
                'resize': {
                    'enabled': True,
                    'max_width': 1920,
                    'max_height': 1080,
                    'min_width': 100,
                    'min_height': 100,
                    'scale_factor': 1.0,
                    'interpolation': 'INTER_CUBIC'
                },
                'denoise': {
                    'enabled': True,
                    'method': 'fastNlMeansDenoising',
                    'h': 10,
                    'template_window_size': 7,
                    'search_window_size': 21
                },
                'binarization': {
                    'enabled': False,
                    'method': 'adaptive_threshold',
                    'threshold_value': 127,
                    'adaptive_method': 'ADAPTIVE_THRESH_GAUSSIAN_C',
                    'threshold_type': 'THRESH_BINARY',
                    'block_size': 11,
                    'c_constant': 2
                },
                'contrast_enhancement': {
                    'enabled': True,
                    'method': 'clahe',
                    'clip_limit': 2.0,
                    'tile_grid_size': [8, 8],
                    'gamma_correction': 1.0
                },
                'brightness_adjustment': {
                    'enabled': False,
                    'auto_adjust': True,
                    'brightness_factor': 1.0,
                    'target_mean': 128
                },
                'sharpening': {
                    'enabled': False,
                    'method': 'unsharp_mask',
                    'kernel_size': 3,
                    'sigma': 1.0,
                    'amount': 1.0,
                    'threshold': 0
                },
                'rotation_correction': {
                    'enabled': False,
                    'auto_detect': True,
                    'angle_threshold': 0.5,
                    'max_angle': 45
                },
                'text_region_extraction': {
                    'enabled': False,
                    'method': 'mser',
                    'min_area': 100,
                    'max_area': 10000,
                    'padding': 5
                },
                'background_removal': {
                    'enabled': False,
                    'method': 'grabcut',
                    'iterations': 5
                }
            }
    
    def preprocess(self, image: Union[np.ndarray, str, Image.Image], 
                  target_text: Optional[str] = None, 
                  custom_methods: Optional[List[str]] = None) -> PreprocessingResult:
        """
        对图像进行预处理
        
        Args:
            image: 输入图像（numpy数组、文件路径或PIL图像）
            target_text: 目标文本（用于优化预处理参数）
            custom_methods: 自定义预处理方法列表
            
        Returns:
            预处理结果
        """
        start_time = time.time()
        
        try:
            # 加载和转换图像
            original_image = self._load_image(image)
            processed_image = original_image.copy()
            methods_applied = []
            metadata = {}
            
            # 应用预处理方法
            if custom_methods:
                for method in custom_methods:
                    if hasattr(self, f'_apply_{method}'):
                        processed_image = getattr(self, f'_apply_{method}')(processed_image)
                        methods_applied.append(method)
            else:
                # 自动模式：根据配置应用预处理方法
                if self.config['resize']['enabled']:
                    processed_image = self._apply_resize(processed_image)
                    methods_applied.append('resize')
                    
                if self.config['denoise']['enabled']:
                    processed_image = self._apply_denoise(processed_image)
                    methods_applied.append('denoise')
                    
                if self.config['contrast_enhancement']['enabled']:
                    processed_image = self._apply_contrast_enhancement(processed_image)
                    methods_applied.append('contrast_enhancement')
                    
                if self.config['binarization']['enabled']:
                    processed_image = self._apply_binarization(processed_image)
                    methods_applied.append('binarization')
            
            processing_time = time.time() - start_time
            quality_score = self._calculate_quality_score(processed_image)
            
            result = PreprocessingResult(
                processed_image=processed_image,
                original_image=original_image,
                processing_time=processing_time,
                methods_applied=methods_applied,
                quality_score=quality_score,
                metadata=metadata
            )
            
            self.logger.info(f"图像预处理完成，耗时: {processing_time:.3f}s，应用方法: {methods_applied}")
            return result
            
        except Exception as e:
            self.logger.error(f"图像预处理失败: {e}")
            raise
    
    def _load_image(self, image: Union[np.ndarray, str, Image.Image]) -> np.ndarray:
        """
        加载图像并转换为numpy数组
        
        Args:
            image: 输入图像
            
        Returns:
            numpy数组格式的图像
        """
        if isinstance(image, np.ndarray):
            return image
        elif isinstance(image, str):
            if not os.path.exists(image):
                raise FileNotFoundError(f"图像文件不存在: {image}")
            return cv2.imread(image)
        elif isinstance(image, Image.Image):
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        else:
            raise ValueError(f"不支持的图像类型: {type(image)}")
    
    def _apply_resize(self, image: np.ndarray) -> np.ndarray:
        """
        应用图像缩放
        
        Args:
            image: 输入图像
            
        Returns:
            缩放后的图像
        """
        config = self.config['resize']
        height, width = image.shape[:2]
        
        # 计算缩放比例
        scale_x = config['max_width'] / width if width > config['max_width'] else 1.0
        scale_y = config['max_height'] / height if height > config['max_height'] else 1.0
        scale = min(scale_x, scale_y)
        
        if scale < 1.0:
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # 选择插值方法
            interpolation = getattr(cv2, config['interpolation'], cv2.INTER_CUBIC)
            
            resized_image = cv2.resize(image, (new_width, new_height), interpolation=interpolation)
            self.logger.debug(f"图像已缩放: {width}x{height} -> {new_width}x{new_height}")
            return resized_image
        
        return image
    
    def _apply_denoise(self, image: np.ndarray) -> np.ndarray:
        """
        应用图像降噪
        
        Args:
            image: 输入图像
            
        Returns:
            降噪后的图像
        """
        config = self.config['denoise']
        
        if len(image.shape) == 3:
            # 彩色图像
            denoised = cv2.fastNlMeansDenoisingColored(
                image,
                None,
                config['h'],
                config['h'],
                config['template_window_size'],
                config['search_window_size']
            )
        else:
            # 灰度图像
            denoised = cv2.fastNlMeansDenoising(
                image,
                None,
                config['h'],
                config['template_window_size'],
                config['search_window_size']
            )
        
        self.logger.debug("图像降噪处理完成")
        return denoised
    
    def _apply_contrast_enhancement(self, image: np.ndarray) -> np.ndarray:
        """
        应用对比度增强
        
        Args:
            image: 输入图像
            
        Returns:
            对比度增强后的图像
        """
        config = self.config['contrast_enhancement']
        
        if len(image.shape) == 3:
            # 转换为LAB色彩空间
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # 对L通道应用CLAHE
            clahe = cv2.createCLAHE(
                clipLimit=config['clip_limit'],
                tileGridSize=tuple(config['tile_grid_size'])
            )
            l = clahe.apply(l)
            
            # 合并通道并转换回BGR
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        else:
            # 灰度图像直接应用CLAHE
            clahe = cv2.createCLAHE(
                clipLimit=config['clip_limit'],
                tileGridSize=tuple(config['tile_grid_size'])
            )
            enhanced = clahe.apply(image)
        
        self.logger.debug("对比度增强处理完成")
        return enhanced
    
    def _apply_binarization(self, image: np.ndarray) -> np.ndarray:
        """
        应用图像二值化
        
        Args:
            image: 输入图像
            
        Returns:
            二值化后的图像
        """
        config = self.config['binarization']
        
        # 转换为灰度图像
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 应用自适应阈值
        adaptive_method = getattr(cv2, config['adaptive_method'], cv2.ADAPTIVE_THRESH_GAUSSIAN_C)
        threshold_type = getattr(cv2, config['threshold_type'], cv2.THRESH_BINARY)
        
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            adaptive_method,
            threshold_type,
            config['block_size'],
            config['c_constant']
        )
        
        self.logger.debug("图像二值化处理完成")
        return binary
    
    def _calculate_quality_score(self, image: np.ndarray) -> float:
        """
        计算图像质量分数
        
        Args:
            image: 输入图像
            
        Returns:
            质量分数（0-1之间）
        """
        try:
            # 转换为灰度图像
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # 计算拉普拉斯方差（清晰度指标）
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 归一化到0-1范围
            quality_score = min(laplacian_var / 1000.0, 1.0)
            
            return quality_score
            
        except Exception as e:
            self.logger.warning(f"质量分数计算失败: {e}")
            return 0.5
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            配置字典
        """
        return self.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        更新配置
        
        Args:
            new_config: 新的配置字典
        """
        self.config.update(new_config)
        self.logger.info("图像预处理配置已更新")


if __name__ == "__main__":
    # 测试代码
    from src.ui.services.logging_service import get_logger
    test_logger = get_logger("ImagePreprocessorTest", "OCR")
    preprocessor = ImagePreprocessor()
    test_logger.info("图像预处理器测试完成")