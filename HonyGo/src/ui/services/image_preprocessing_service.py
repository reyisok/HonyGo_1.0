#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像预处理优化服务
实现图像预处理优化：分辨率降低、二值化、去噪和文字区域增强

@author: Mr.Rey Copyright © 2025
"""

import time
from io import BytesIO
from typing import Any, Dict, Optional, Tuple
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from PySide6.QtCore import QObject, Signal
from src.ui.services.logging_service import get_logger


class ImagePreprocessingService(QObject):
    """
    图像预处理优化服务
    """
    
    # 信号定义
    preprocessing_completed = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("ImagePreprocessingService", "Application")
        
        # 默认配置
        self.config = {
            "max_width": 2560,
            "min_width": 400,
            "resize_factor": 1.0,
            "enable_denoise": True,
            "enable_enhance": True,
            "enable_binarize": False,
            "fast_mode": False
        }
    
    def preprocess_image(self, image: Image.Image, target_text: str = "", fast_mode: bool = False) -> Image.Image:
        """
        预处理图像
        
        Args:
            image: 输入图像
            target_text: 目标文本（用于优化处理策略）
            fast_mode: 是否使用快速模式
            
        Returns:
            Image.Image: 预处理后的图像
        """
        try:
            start_time = time.time()
            
            # 1. 智能缩放
            processed_image = self._smart_resize(image)
            
            # 2. 去噪处理
            if self.config["enable_denoise"]:
                processed_image = self._denoise_image(processed_image, fast_mode)
            
            # 3. 图像增强
            if self.config["enable_enhance"]:
                processed_image = self._enhance_image(processed_image, target_text)
            
            # 4. 二值化处理（根据文本类型决定）
            if self.config["enable_binarize"] or self._should_binarize(target_text):
                processed_image = self._binarize_image(processed_image)
            
            processing_time = time.time() - start_time
            self.logger.debug(f"图像预处理完成，耗时: {processing_time:.3f}秒")
            
            return processed_image
            
        except Exception as e:
            self.logger.error(f"图像预处理失败: {e}", exc_info=True)
            return image
    
    def image_to_bytes(self, image: Image.Image, format: str = "PNG") -> bytes:
        """
        将图像转换为bytes
        
        Args:
            image: PIL图像对象
            format: 图像格式
            
        Returns:
            bytes: 图像字节数据
        """
        try:
            buffer = BytesIO()
            image.save(buffer, format=format, optimize=True)
            return buffer.getvalue()
        except Exception as e:
            self.logger.error(f"图像转换为bytes失败: {e}")
            raise
    
    def _smart_resize(self, image: Image.Image) -> Image.Image:
        """
        智能缩放图像
        
        Args:
            image: 输入图像
            
        Returns:
            Image.Image: 缩放后的图像
        """
        try:
            width, height = image.size
            
            # 如果图像太大，进行缩放
            if width > self.config["max_width"]:
                scale_factor = self.config["max_width"] / width
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
            elif width < self.config["min_width"]:
                # 如果图像太小，进行放大
                scale_factor = self.config["min_width"] / width
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
            else:
                # 应用缩放因子
                new_width = int(width * self.config["resize_factor"])
                new_height = int(height * self.config["resize_factor"])
            
            # 限制最终尺寸
            new_width = max(400, min(new_width, 2560))
            new_height = max(300, min(new_height, 1440))
            
            if (new_width, new_height) != (width, height):
                resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                self.logger.debug(f"图像缩放: {width}x{height} -> {new_width}x{new_height}")
                return resized
            
            return image
        except Exception as e:
            self.logger.error(f"图像缩放失败: {e}")
            return image
    
    def _denoise_image(self, image: Image.Image, fast_mode: bool = False) -> Image.Image:
        """
        图像去噪
        
        Args:
            image: 输入图像
            fast_mode: 是否使用快速模式
            
        Returns:
            Image.Image: 去噪后的图像
        """
        try:
            if fast_mode:
                # 快速模式：简单平滑
                return image.filter(ImageFilter.SMOOTH_MORE)
            else:
                # 标准模式：中值滤波 + 高斯模糊
                denoised = image.filter(ImageFilter.MedianFilter(size=3))
                
                # 轻微高斯模糊
                denoised = denoised.filter(ImageFilter.GaussianBlur(radius=0.5))
                
                return denoised
        except Exception as e:
            self.logger.error(f"图像去噪失败: {e}")
            return image
    
    def _enhance_image(self, image: Image.Image, target_text: str = "") -> Image.Image:
        """
        图像增强
        
        Args:
            image: 输入图像
            target_text: 目标文本
            
        Returns:
            Image.Image: 增强后的图像
        """
        try:
            # 对比度增强
            contrast_enhancer = ImageEnhance.Contrast(image)
            enhanced = contrast_enhancer.enhance(1.2)
            
            # 锐度增强
            sharpness_enhancer = ImageEnhance.Sharpness(enhanced)
            enhanced = sharpness_enhancer.enhance(1.1)
            
            # 根据目标文本调整亮度
            if target_text and any(char.isdigit() for char in target_text):
                # 数字文本需要更高对比度
                brightness_enhancer = ImageEnhance.Brightness(enhanced)
                enhanced = brightness_enhancer.enhance(1.05)
            
            return enhanced
            
        except Exception as e:
            self.logger.error(f"图像增强失败: {e}")
            return image
    
    def _should_binarize(self, target_text: str = "") -> bool:
        """
        判断是否需要二值化
        
        Args:
            target_text: 目标文本
            
        Returns:
            bool: 是否需要二值化
        """
        # 如果目标文本包含数字或特殊字符，建议二值化
        if target_text:
            return any(char.isdigit() or char in "!@#$%^&*()_+-=[]{}|;':,.<>?" for char in target_text)
        return False
    
    def _binarize_image(self, image: Image.Image) -> Image.Image:
        """
        图像二值化
        
        Args:
            image: 输入图像
            
        Returns:
            Image.Image: 二值化后的图像
        """
        try:
            # 转换为灰度图
            if image.mode != 'L':
                gray_image = image.convert('L')
            else:
                gray_image = image
            
            # 转换为numpy数组
            img_array = np.array(gray_image)
            
            # 使用OTSU阈值进行二值化
            _, binary = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 转换回PIL图像
            binary_image = Image.fromarray(binary, mode='L')
            
            return binary_image
            
        except Exception as e:
            self.logger.error(f"图像二值化失败: {e}")
            return image
    
    def update_config(self, config: Dict[str, Any]):
        """
        更新配置
        
        Args:
            config: 新的配置字典
        """
        try:
            self.config.update(config)
            self.logger.info(f"图像预处理配置已更新: {config}")
        except Exception as e:
            self.logger.error(f"更新配置失败: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            Dict[str, Any]: 当前配置
        """
        return self.config.copy()
    
    def optimize_for_text_type(self, text_type: str):
        """
        根据文本类型优化配置
        
        Args:
            text_type: 文本类型 ('number', 'chinese', 'english', 'mixed')
        """
        try:
            if text_type == 'number':
                # 数字识别优化
                self.config.update({
                    "enable_binarize": True,
                    "enable_enhance": True,
                    "resize_factor": 1.2
                })
            elif text_type == 'chinese':
                # 中文识别优化
                self.config.update({
                    "enable_binarize": False,
                    "enable_enhance": True,
                    "resize_factor": 1.0
                })
            elif text_type == 'english':
                # 英文识别优化
                self.config.update({
                    "enable_binarize": False,
                    "enable_enhance": True,
                    "resize_factor": 1.1
                })
            else:
                # 混合文本优化
                self.config.update({
                    "enable_binarize": False,
                    "enable_enhance": True,
                    "resize_factor": 1.0
                })
            
            self.logger.info(f"已为文本类型 '{text_type}' 优化配置")
            
        except Exception as e:
            self.logger.error(f"文本类型优化失败: {e}")
    
    def cleanup(self):
        """
        清理资源
        """
        try:
            self.logger.info("图像预处理服务资源清理完成")
        except Exception as e:
            self.logger.error(f"图像预处理服务清理失败: {e}")