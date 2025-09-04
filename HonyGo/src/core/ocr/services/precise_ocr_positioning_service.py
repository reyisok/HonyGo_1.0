#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR精确定位服务模块

基于测试验证的OCR精确定位逻辑，提供关键字的精确位置计算和点击坐标优化。
集成EasyOCR识别、关键字匹配和精确位置计算功能。

@author: Mr.Rey Copyright © 2025
@created: 2025-01-15 16:30:00
@modified: 2025-01-15 16:30:00
@version: 1.0.0
"""

import base64
import io
import os
from typing import Any, Dict, List, Optional, Tuple
import cv2
import easyocr
import numpy as np
from PIL import Image, ImageGrab
from src.core.ocr.services.ocr_pool_manager import get_pool_manager
from src.core.ocr.utils.keyword_matcher import KeywordMatcher, MatchStrategy
from src.ui.services.logging_service import get_logger


class PreciseOCRPositioningService:
    """
    OCR精确定位服务
    
    提供基于OCR识别的关键字精确位置计算和点击坐标优化功能
    """
    
    def __init__(self):
        """初始化OCR精确定位服务"""
        self.logger = get_logger("PreciseOCRPositioningService")
        self.keyword_matcher = KeywordMatcher()
        self._ocr_reader = None
        
        # 精确定位配置
        self.precise_padding = 10  # 精确区域的边距
        self.min_text_width = 20   # 最小文字宽度
        self.min_text_height = 10  # 最小文字高度
        
        self.logger.info("OCR精确定位服务初始化完成")
    
    def _get_ocr_reader(self) -> easyocr.Reader:
        """获取OCR读取器实例（延迟初始化）"""
        if self._ocr_reader is None:
            try:
                # 使用中文和英文语言包
                self._ocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
                self.logger.info("OCR读取器初始化完成")
            except Exception as e:
                self.logger.error(f"OCR读取器初始化失败: {e}")
                raise
        return self._ocr_reader
    
    def find_precise_text_position(self, image_data: bytes, target_text: str, 
                                 strategy: MatchStrategy = MatchStrategy.CONTAINS) -> Optional[Dict[str, Any]]:
        """
        使用OCR精确定位目标文字的位置
        
        Args:
            image_data: 图像数据（bytes格式）
            target_text: 目标文字
            strategy: 匹配策略
            
        Returns:
            Optional[Dict[str, Any]]: 精确位置信息，包含center_x, center_y, bbox等
        """
        try:
            self.logger.info(f"开始OCR精确定位文字: '{target_text}'")
            
            # 转换图像数据
            if isinstance(image_data, str):
                # base64格式
                image_bytes = base64.b64decode(image_data)
            else:
                # bytes格式
                image_bytes = image_data
            
            # 使用PIL加载图像
            image = Image.open(io.BytesIO(image_bytes))
            image_array = np.array(image)
            
            # 使用EasyOCR进行识别
            ocr_reader = self._get_ocr_reader()
            ocr_results = ocr_reader.readtext(image_array)
            
            self.logger.info(f"OCR识别到 {len(ocr_results)} 个文本区域")
            
            # 转换OCR结果为标准格式
            formatted_results = []
            for result in ocr_results:
                bbox_points, text, confidence = result
                
                # 计算边界框
                x_coords = [point[0] for point in bbox_points]
                y_coords = [point[1] for point in bbox_points]
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                
                formatted_result = {
                    'text': text,
                    'confidence': confidence,
                    'bbox': [x_min, y_min, x_max - x_min, y_max - y_min]
                }
                formatted_results.append(formatted_result)
                
                self.logger.debug(f"识别文字: '{text}', 置信度: {confidence:.3f}, 位置: {formatted_result['bbox']}")
            
            # 使用关键字匹配器查找目标
            matches = self.keyword_matcher.find_matches(formatted_results, target_text, strategy)
            
            if not matches:
                self.logger.info(f"未找到匹配的文字: '{target_text}'")
                return None
            
            # 选择置信度最高的匹配项
            best_match = max(matches, key=lambda m: m.get('confidence', 0.0))
            
            # 计算精确中心位置
            bbox = best_match.get('bbox', [0, 0, 0, 0])
            parsed_bbox = self.keyword_matcher._parse_bbox(bbox)
            
            if parsed_bbox is None:
                self.logger.error(f"bbox解析失败: {bbox}")
                return None
            
            x, y, w, h = parsed_bbox
            center_x = x + w // 2
            center_y = y + h // 2
            
            precise_position = {
                'text': best_match.get('text', ''),
                'confidence': best_match.get('confidence', 0.0),
                'center_x': center_x,
                'center_y': center_y,
                'bbox': (x, y, w, h),
                'precise_bbox': (x, y, w, h),  # 精确边界框
                'method': 'ocr_precise_positioning'
            }
            
            self.logger.info(
                f"OCR精确定位成功: '{best_match.get('text', '')}', "
                f"置信度: {best_match.get('confidence', 0.0):.3f}, "
                f"中心位置: ({center_x}, {center_y})"
            )
            
            return precise_position
            
        except Exception as e:
            self.logger.error(f"OCR精确定位失败: {e}")
            return None
    
    def create_precise_reference_image(self, image_data: bytes, target_text: str, 
                                     output_path: str, padding: int = None) -> Optional[str]:
        """
        基于OCR精确定位创建精确的参照图片
        
        Args:
            image_data: 原始图像数据
            target_text: 目标文字
            output_path: 输出图片路径
            padding: 边距（可选）
            
        Returns:
            Optional[str]: 创建的参照图片路径，失败返回None
        """
        try:
            # 获取精确位置
            precise_position = self.find_precise_text_position(image_data, target_text)
            if not precise_position:
                self.logger.error(f"无法获取文字 '{target_text}' 的精确位置")
                return None
            
            # 转换图像数据
            if isinstance(image_data, str):
                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data
            
            image = Image.open(io.BytesIO(image_bytes))
            
            # 获取精确边界框
            x, y, w, h = precise_position['precise_bbox']
            
            # 应用边距
            if padding is None:
                padding = self.precise_padding
            
            # 确保裁剪区域在图像范围内
            crop_x = max(0, x - padding)
            crop_y = max(0, y - padding)
            crop_w = min(image.width - crop_x, w + 2 * padding)
            crop_h = min(image.height - crop_y, h + 2 * padding)
            
            # 裁剪精确区域
            crop_box = (crop_x, crop_y, crop_x + crop_w, crop_y + crop_h)
            precise_image = image.crop(crop_box)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存精确参照图片
            precise_image.save(output_path)
            
            self.logger.info(
                f"精确参照图片创建成功: {output_path}, "
                f"尺寸: {precise_image.size}, "
                f"原始区域: ({x}, {y}, {w}, {h}), "
                f"裁剪区域: {crop_box}"
            )
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"创建精确参照图片失败: {e}")
            return None
    
    def enhance_ocr_click_position(self, ocr_result: Dict[str, Any], target_text: str, 
                                 image_data: bytes = None) -> Dict[str, Any]:
        """
        增强OCR点击位置的精确性
        
        Args:
            ocr_result: 原始OCR识别结果
            target_text: 目标文字
            image_data: 图像数据（可选，用于精确定位）
            
        Returns:
            Dict[str, Any]: 增强后的点击位置信息
        """
        try:
            self.logger.info(f"开始增强OCR点击位置精确性: '{target_text}'")
            
            # 如果提供了图像数据，使用精确定位
            if image_data:
                precise_position = self.find_precise_text_position(image_data, target_text)
                if precise_position:
                    self.logger.info("使用OCR精确定位结果")
                    return {
                        'enhanced': True,
                        'method': 'precise_ocr_positioning',
                        'center_x': precise_position['center_x'],
                        'center_y': precise_position['center_y'],
                        'confidence': precise_position['confidence'],
                        'bbox': precise_position['bbox'],
                        'text': precise_position['text']
                    }
            
            # 使用原始OCR结果
            if not ocr_result.get('success') or not ocr_result.get('data'):
                self.logger.warning("OCR结果无效，无法增强点击位置")
                return {'enhanced': False, 'error': 'Invalid OCR result'}
            
            # 查找匹配的文字
            ocr_data = ocr_result.get('data', [])
            matches = self.keyword_matcher.find_matches(ocr_data, target_text)
            
            if not matches:
                self.logger.warning(f"在OCR结果中未找到匹配的文字: '{target_text}'")
                return {'enhanced': False, 'error': 'No matching text found'}
            
            # 选择最佳匹配
            best_match = max(matches, key=lambda m: m.get('confidence', 0.0))
            
            # 解析bbox并计算中心点
            bbox = best_match.get('bbox', [0, 0, 0, 0])
            parsed_bbox = self.keyword_matcher._parse_bbox(bbox)
            
            if parsed_bbox is None:
                self.logger.error(f"bbox解析失败: {bbox}")
                return {'enhanced': False, 'error': 'Failed to parse bbox'}
            
            x, y, w, h = parsed_bbox
            center_x = x + w // 2
            center_y = y + h // 2
            
            self.logger.info(
                f"OCR点击位置增强完成: '{best_match.get('text', '')}', "
                f"中心位置: ({center_x}, {center_y})"
            )
            
            return {
                'enhanced': True,
                'method': 'standard_ocr_enhancement',
                'center_x': center_x,
                'center_y': center_y,
                'confidence': best_match.get('confidence', 0.0),
                'bbox': (x, y, w, h),
                'text': best_match.get('text', '')
            }
            
        except Exception as e:
            self.logger.error(f"增强OCR点击位置失败: {e}")
            return {'enhanced': False, 'error': str(e)}
    
    def cleanup(self):
        """清理资源"""
        try:
            if self._ocr_reader is not None:
                # EasyOCR没有显式的清理方法，设置为None让GC处理
                self._ocr_reader = None
                self.logger.info("OCR读取器资源已清理")
            
            self.logger.info("OCR精确定位服务资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理OCR精确定位服务资源失败: {e}")


# 全局服务实例
_precise_ocr_positioning_service = None


def get_precise_ocr_positioning_service() -> PreciseOCRPositioningService:
    """获取OCR精确定位服务实例"""
    global _precise_ocr_positioning_service
    if _precise_ocr_positioning_service is None:
        _precise_ocr_positioning_service = PreciseOCRPositioningService()
    return _precise_ocr_positioning_service