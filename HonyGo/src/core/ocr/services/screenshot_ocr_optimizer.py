#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全屏截图OCR优化服务
专门针对全屏截图和关键字匹配场景的OCR优化
@author: Mr.Rey Copyright © 2025
"""

from typing import (
    Any,
    Dict,
    Tuple,
    Union
)
import base64

from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import io

from src.config.optimization_config_manager import OptimizationConfigManager
from src.ui.services.logging_service import get_logger
















class ScreenshotOCROptimizer:
    """
    全屏截图OCR优化器
    专门针对全屏截图场景进行图像预处理和OCR参数优化
    """
    
    def __init__(self):
        self.logger = get_logger("ScreenshotOCROptimizer", "Application")
        self.config_manager = OptimizationConfigManager()
        self.config = self.config_manager.get_config()
        
        # 截图优化配置
        self.screenshot_config = self.config.screenshot_optimization
        self.image_config = self.config.image_preprocessing
        
        self.logger.info("全屏截图OCR优化器初始化完成")
    
    def optimize_screenshot_for_ocr(self, image_data: Union[str, bytes, np.ndarray, Image.Image]) -> Tuple[Union[str, np.ndarray], Dict[str, Any]]:
        """
        优化全屏截图用于OCR识别
        
        Args:
            image_data: 图像数据（base64字符串、字节数据、numpy数组或PIL图像）
            
        Returns:
            优化后的图像数据和优化参数
        """
        try:
            # 转换图像格式
            image = self._convert_to_pil_image(image_data)
            
            # 应用截图专项优化
            optimized_image = self._apply_screenshot_optimizations(image)
            
            # 获取优化的OCR参数
            ocr_params = self._get_screenshot_ocr_params()
            
            # 转换回原始格式
            if isinstance(image_data, str):  # base64
                result_image = self._pil_to_base64(optimized_image)
            elif isinstance(image_data, bytes):
                result_image = self._pil_to_bytes(optimized_image)
            elif isinstance(image_data, np.ndarray):
                result_image = self._pil_to_numpy(optimized_image)
            else:
                result_image = optimized_image
            
            self.logger.debug("全屏截图OCR优化完成")
            return result_image, ocr_params
            
        except Exception as e:
            self.logger.error(f"全屏截图OCR优化失败: {e}")
            return image_data, {}
    
    def _apply_screenshot_optimizations(self, image: Image.Image) -> Image.Image:
        """
        应用截图专项优化
        
        Args:
            image: PIL图像对象
            
        Returns:
            优化后的PIL图像对象
        """
        try:
            # 1. 尺寸优化 - 全屏截图通常很大，需要适当缩放
            if self.screenshot_config.enabled:
                image = self._optimize_screenshot_size(image)
            
            # 2. 区域检测和裁剪
            if self.screenshot_config.region_detection:
                image = self._detect_and_crop_text_regions(image)
            
            # 3. 文本区域聚焦
            if self.screenshot_config.text_area_focus:
                image = self._enhance_text_areas(image)
            
            # 4. 多尺度检测优化
            if self.screenshot_config.multi_scale_detection:
                image = self._prepare_for_multi_scale(image)
            
            # 5. 自适应阈值处理
            if self.screenshot_config.adaptive_threshold:
                image = self._apply_adaptive_threshold(image)
            
            # 6. 噪声过滤
            if self.screenshot_config.noise_filtering:
                image = self._filter_screenshot_noise(image)
            
            return image
            
        except Exception as e:
            self.logger.warning(f"截图优化处理失败: {e}，返回原图")
            return image
    
    def _optimize_screenshot_size(self, image: Image.Image) -> Image.Image:
        """
        优化截图尺寸
        
        Args:
            image: PIL图像对象
            
        Returns:
            尺寸优化后的图像
        """
        try:
            width, height = image.size
            max_width = self.image_config.max_width
            max_height = self.image_config.max_height
            
            # 如果图像过大，按比例缩放
            if width > max_width or height > max_height:
                # 计算缩放比例
                width_ratio = max_width / width
                height_ratio = max_height / height
                scale_ratio = min(width_ratio, height_ratio)
                
                new_width = int(width * scale_ratio)
                new_height = int(height * scale_ratio)
                
                # 使用高质量重采样
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                self.logger.debug(f"截图尺寸优化: {width}x{height} -> {new_width}x{new_height}")
            
            return image
            
        except Exception as e:
            self.logger.warning(f"截图尺寸优化失败: {e}")
            return image
    
    def _detect_and_crop_text_regions(self, image: Image.Image) -> Image.Image:
        """
        检测并裁剪文本区域
        
        Args:
            image: PIL图像对象
            
        Returns:
            裁剪后的图像
        """
        try:
            # 转换为OpenCV格式
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # 使用形态学操作检测文本区域
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
            morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            
            # 查找轮廓
            contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # 找到最大的文本区域
                largest_contour = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest_contour)
                
                # 添加边距
                margin = self.image_config.padding_size
                x = max(0, x - margin)
                y = max(0, y - margin)
                w = min(image.width - x, w + 2 * margin)
                h = min(image.height - y, h + 2 * margin)
                
                # 裁剪图像
                cropped_image = image.crop((x, y, x + w, y + h))
                self.logger.debug(f"检测到文本区域并裁剪: ({x}, {y}, {w}, {h})")
                return cropped_image
            
            return image
            
        except Exception as e:
            self.logger.warning(f"文本区域检测失败: {e}")
            return image
    
    def _enhance_text_areas(self, image: Image.Image) -> Image.Image:
        """
        增强文本区域
        
        Args:
            image: PIL图像对象
            
        Returns:
            增强后的图像
        """
        try:
            # 对比度增强
            if self.image_config.contrast_enhancement:
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.2)
            
            # 锐化处理
            if self.image_config.sharpening:
                image = image.filter(ImageFilter.SHARPEN)
            
            # 亮度调整
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.1)
            
            return image
            
        except Exception as e:
            self.logger.warning(f"文本区域增强失败: {e}")
            return image
    
    def _prepare_for_multi_scale(self, image: Image.Image) -> Image.Image:
        """
        为多尺度检测准备图像
        
        Args:
            image: PIL图像对象
            
        Returns:
            准备好的图像
        """
        try:
            # 确保图像尺寸适合多尺度检测
            width, height = image.size
            
            # 调整到合适的尺寸（能被32整除，适合深度学习模型）
            new_width = ((width + 31) // 32) * 32
            new_height = ((height + 31) // 32) * 32
            
            if new_width != width or new_height != height:
                # 创建新的图像，用白色填充
                new_image = Image.new('RGB', (new_width, new_height), 'white')
                # 将原图像粘贴到中心
                offset_x = (new_width - width) // 2
                offset_y = (new_height - height) // 2
                new_image.paste(image, (offset_x, offset_y))
                image = new_image
                
                self.logger.debug(f"多尺度检测尺寸调整: {width}x{height} -> {new_width}x{new_height}")
            
            return image
            
        except Exception as e:
            self.logger.warning(f"多尺度检测准备失败: {e}")
            return image
    
    def _apply_adaptive_threshold(self, image: Image.Image) -> Image.Image:
        """
        应用自适应阈值处理
        
        Args:
            image: PIL图像对象
            
        Returns:
            处理后的图像
        """
        try:
            # 转换为灰度图
            gray_image = image.convert('L')
            
            # 转换为numpy数组
            gray_array = np.array(gray_image)
            
            # 应用自适应阈值
            adaptive_thresh = cv2.adaptiveThreshold(
                gray_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # 转换回PIL图像
            result_image = Image.fromarray(adaptive_thresh).convert('RGB')
            
            return result_image
            
        except Exception as e:
            self.logger.warning(f"自适应阈值处理失败: {e}")
            return image
    
    def _filter_screenshot_noise(self, image: Image.Image) -> Image.Image:
        """
        过滤截图噪声
        
        Args:
            image: PIL图像对象
            
        Returns:
            去噪后的图像
        """
        try:
            # 高斯模糊去噪（轻微）
            if self.image_config.noise_reduction:
                image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
            
            # 中值滤波去噪
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            return image
            
        except Exception as e:
            self.logger.warning(f"截图去噪失败: {e}")
            return image
    
    def _get_screenshot_ocr_params(self) -> Dict[str, Any]:
        """
        获取针对截图优化的OCR参数
        
        Returns:
            优化的OCR参数字典
        """
        try:
            # 基础参数
            params = {
                'text_threshold': 0.6,  # 降低文本阈值，提高检测敏感度
                'low_text': 0.3,        # 降低低文本阈值
                'link_threshold': 0.3,   # 降低链接阈值
                'canvas_size': 2560,     # 大画布尺寸适合全屏截图
                'mag_ratio': 1.8,        # 提高放大比例
                'min_size': 15,          # 降低最小尺寸，检测小文本
                'decoder': 'beamsearch', # 使用beam search提高准确率
                'beamWidth': 8,          # 增加beam宽度
                'batch_size': 1,         # 截图通常单张处理
                'detail': 1,             # 返回详细信息
                'paragraph': False,      # 不合并段落
                'width_ths': 0.4,        # 降低宽度阈值
                'height_ths': 0.6,       # 调整高度阈值
                'slope_ths': 0.2,        # 增加倾斜容忍度
                'add_margin': 0.15       # 增加边距
            }
            
            # 如果有配置，使用配置中的参数
            if hasattr(self.config, 'easyocr_optimizations'):
                ocr_config = self.config.easyocr_optimizations
                # 覆盖部分参数以适应截图场景
                params.update({
                    'text_threshold': min(ocr_config.text_threshold, 0.6),
                    'low_text': min(ocr_config.low_text, 0.3),
                    'canvas_size': max(ocr_config.canvas_size, 2560),
                    'mag_ratio': max(ocr_config.mag_ratio, 1.8),
                    'decoder': ocr_config.decoder,
                    'beamWidth': max(ocr_config.beamWidth, 8)
                })
            
            self.logger.debug("已生成截图专用OCR参数")
            return params
            
        except Exception as e:
            self.logger.warning(f"生成截图OCR参数失败: {e}")
            return {}
    
    def _convert_to_pil_image(self, image_data: Union[str, bytes, np.ndarray, Image.Image]) -> Image.Image:
        """
        转换各种格式的图像数据为PIL图像
        
        Args:
            image_data: 图像数据
            
        Returns:
            PIL图像对象
        """
        try:
            if isinstance(image_data, Image.Image):
                return image_data
            elif isinstance(image_data, str):  # base64
                # 移除base64前缀
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
                return Image.open(io.BytesIO(image_bytes))
            elif isinstance(image_data, bytes):
                return Image.open(io.BytesIO(image_data))
            elif isinstance(image_data, np.ndarray):
                return Image.fromarray(image_data)
            else:
                raise ValueError(f"不支持的图像数据类型: {type(image_data)}")
                
        except Exception as e:
            self.logger.error(f"图像格式转换失败: {e}")
            raise
    
    def _pil_to_base64(self, image: Image.Image) -> str:
        """
        将PIL图像转换为base64字符串
        
        Args:
            image: PIL图像对象
            
        Returns:
            base64字符串
        """
        try:
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_bytes = buffer.getvalue()
            return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            self.logger.error(f"PIL转base64失败: {e}")
            raise
    
    def _pil_to_bytes(self, image: Image.Image) -> bytes:
        """
        将PIL图像转换为字节数据
        
        Args:
            image: PIL图像对象
            
        Returns:
            字节数据
        """
        try:
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            return buffer.getvalue()
        except Exception as e:
            self.logger.error(f"PIL转bytes失败: {e}")
            raise
    
    def _pil_to_numpy(self, image: Image.Image) -> np.ndarray:
        """
        将PIL图像转换为numpy数组
        
        Args:
            image: PIL图像对象
            
        Returns:
            numpy数组
        """
        try:
            return np.array(image)
        except Exception as e:
            self.logger.error(f"PIL转numpy失败: {e}")
            raise


# 全局实例
_screenshot_optimizer_instance = None


def get_screenshot_optimizer() -> ScreenshotOCROptimizer:
    """
    获取全屏截图OCR优化器实例（单例模式）
    
    Returns:
        ScreenshotOCROptimizer实例
    """
    global _screenshot_optimizer_instance
    if _screenshot_optimizer_instance is None:
        _screenshot_optimizer_instance = ScreenshotOCROptimizer()
    return _screenshot_optimizer_instance