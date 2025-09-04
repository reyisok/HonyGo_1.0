#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确图片参照服务模块

基于测试验证的精确图片参照逻辑，提供高精度的图片匹配和点击位置计算。
集成OCR辅助的精确参照图片创建和优化匹配算法。

@author: Mr.Rey Copyright © 2025
@created: 2025-01-15 16:45:00
@modified: 2025-01-15 16:45:00
@version: 1.0.0
"""

import base64
import io
import os
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image, ImageGrab
from src.core.algorithms.image_reference_algorithm import ImageReferenceAlgorithm, MatchMethod
from src.core.ocr.services.precise_ocr_positioning_service import get_precise_ocr_positioning_service
from src.ui.services.coordinate_service import get_coordinate_service
from src.ui.services.logging_service import get_logger


class PreciseImageReferenceService:
    """
    精确图片参照服务
    
    提供基于OCR辅助的精确图片参照匹配和点击位置优化功能
    """
    
    def __init__(self):
        """初始化精确图片参照服务"""
        self.logger = get_logger("PreciseImageReferenceService")
        self._algorithm = ImageReferenceAlgorithm()
        self._coordinate_service = get_coordinate_service()
        self._precise_ocr_service = get_precise_ocr_positioning_service()
        
        # 精确匹配配置
        self.high_precision_threshold = 0.95  # 高精度匹配阈值
        self.standard_threshold = 0.8         # 标准匹配阈值
        self.ocr_assist_threshold = 0.7       # OCR辅助匹配阈值
        self.precise_padding = 10             # 精确参照图片边距
        
        self.logger.info("精确图片参照服务初始化完成")
    
    def create_precise_reference_from_text(self, target_text: str, screen_region: Optional[Tuple[int, int, int, int]] = None, 
                                         output_path: str = None) -> Optional[str]:
        """
        基于目标文字创建精确的参照图片
        
        Args:
            target_text: 目标文字
            screen_region: 屏幕区域 (x, y, width, height)
            output_path: 输出路径（可选）
            
        Returns:
            Optional[str]: 创建的精确参照图片路径
        """
        try:
            self.logger.info(f"开始基于文字创建精确参照图片: '{target_text}'")
            
            # 截取屏幕
            if screen_region:
                bbox = (screen_region[0], screen_region[1], 
                       screen_region[0] + screen_region[2], 
                       screen_region[1] + screen_region[3])
                screenshot = ImageGrab.grab(bbox=bbox)
            else:
                screenshot = ImageGrab.grab()
            
            # 转换为bytes
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            image_data = buffer.getvalue()
            
            # 生成输出路径
            if output_path is None:
                # 使用项目根目录下的tests目录
                from src.config.path_config import get_project_root
                project_root = get_project_root()
                output_path = os.path.join(project_root, "tests", f"{target_text}_reference_precise.png")
            
            # 使用OCR精确定位服务创建精确参照图片
            precise_path = self._precise_ocr_service.create_precise_reference_image(
                image_data=image_data,
                target_text=target_text,
                output_path=output_path,
                padding=self.precise_padding
            )
            
            if precise_path:
                self.logger.info(f"精确参照图片创建成功: {precise_path}")
                return precise_path
            else:
                self.logger.error(f"精确参照图片创建失败: '{target_text}'")
                return None
                
        except Exception as e:
            self.logger.error(f"基于文字创建精确参照图片失败: {e}")
            return None
    
    def find_precise_matches(self, reference_image_path: str, screen_region: Optional[Tuple[int, int, int, int]] = None, 
                           max_matches: int = 10, use_ocr_assist: bool = True) -> List[Dict[str, Any]]:
        """
        查找精确匹配项
        
        Args:
            reference_image_path: 参照图片路径
            screen_region: 屏幕区域
            max_matches: 最大匹配数量
            use_ocr_assist: 是否使用OCR辅助
            
        Returns:
            List[Dict[str, Any]]: 精确匹配结果列表
        """
        try:
            self.logger.info(f"开始精确图片匹配: {reference_image_path}")
            
            # 检查参照图片是否存在
            if not os.path.exists(reference_image_path):
                self.logger.error(f"参照图片不存在: {reference_image_path}")
                return []
            
            # 截取屏幕
            screenshot = self._coordinate_service.capture_screen(screen_region)
            if screenshot is None:
                self.logger.error("屏幕截取失败")
                return []
            
            # 转换为OpenCV格式
            screen_array = np.array(screenshot)
            screen_image = cv2.cvtColor(screen_array, cv2.COLOR_RGB2BGR)
            
            # 加载参照图片
            reference_image = cv2.imread(reference_image_path)
            if reference_image is None:
                self.logger.error(f"无法加载参照图片: {reference_image_path}")
                return []
            
            # 执行多种匹配方法
            all_matches = []
            
            # 1. 高精度模板匹配
            try:
                template_matches = self._algorithm.find_image_matches(
                    screen_image=screen_image,
                    reference_image=reference_image,
                    method=MatchMethod.TEMPLATE_MATCHING,
                    min_confidence=self.high_precision_threshold
                )
                
                for match in template_matches:
                    match_info = {
                        'confidence': match.confidence,
                        'similarity': match.confidence,
                        'bbox': match.bounding_box if match.bounding_box else (
                            match.position[0] - reference_image.shape[1] // 2,
                            match.position[1] - reference_image.shape[0] // 2,
                            reference_image.shape[1],
                            reference_image.shape[0]
                        ),
                        'position': match.position,
                        'method': 'high_precision_template',
                        'precision_level': 'high'
                    }
                    all_matches.append(match_info)
                    
                self.logger.info(f"高精度模板匹配找到 {len(template_matches)} 个结果")
                
            except Exception as e:
                self.logger.warning(f"高精度模板匹配失败: {e}")
            
            # 2. 如果高精度匹配结果不足，使用标准匹配
            if len(all_matches) < max_matches:
                try:
                    standard_matches = self._algorithm.find_image_matches(
                        screen_image=screen_image,
                        reference_image=reference_image,
                        method=MatchMethod.TEMPLATE_MATCHING,
                        min_confidence=self.standard_threshold
                    )
                    
                    for match in standard_matches:
                        # 避免重复添加高精度已找到的匹配项
                        position_key = (match.position[0], match.position[1])
                        existing_positions = [(m['position'][0], m['position'][1]) for m in all_matches]
                        
                        if position_key not in existing_positions:
                            match_info = {
                                'confidence': match.confidence,
                                'similarity': match.confidence,
                                'bbox': match.bounding_box if match.bounding_box else (
                                    match.position[0] - reference_image.shape[1] // 2,
                                    match.position[1] - reference_image.shape[0] // 2,
                                    reference_image.shape[1],
                                    reference_image.shape[0]
                                ),
                                'position': match.position,
                                'method': 'standard_template',
                                'precision_level': 'standard'
                            }
                            all_matches.append(match_info)
                    
                    self.logger.info(f"标准模板匹配额外找到 {len(standard_matches)} 个结果")
                    
                except Exception as e:
                    self.logger.warning(f"标准模板匹配失败: {e}")
            
            # 3. OCR辅助匹配（如果启用且结果仍不足）
            if use_ocr_assist and len(all_matches) < max_matches:
                try:
                    self.logger.info("启用OCR辅助匹配")
                    
                    # 将屏幕截图转换为base64
                    buffer = io.BytesIO()
                    screenshot.save(buffer, format='PNG')
                    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    
                    # 尝试从参照图片文件名推断目标文字
                    filename = os.path.basename(reference_image_path)
                    target_text = filename.split('_')[0] if '_' in filename else filename.split('.')[0]
                    
                    # 使用OCR精确定位
                    precise_position = self._precise_ocr_service.find_precise_text_position(
                        image_data=image_base64,
                        target_text=target_text
                    )
                    
                    if precise_position:
                        ocr_match = {
                            'confidence': precise_position['confidence'],
                            'similarity': precise_position['confidence'],
                            'bbox': precise_position['bbox'],
                            'position': (precise_position['center_x'], precise_position['center_y']),
                            'method': 'ocr_assisted',
                            'precision_level': 'ocr_precise',
                            'text': precise_position['text']
                        }
                        all_matches.append(ocr_match)
                        self.logger.info(f"OCR辅助匹配找到目标: '{precise_position['text']}'")
                    
                except Exception as e:
                    self.logger.warning(f"OCR辅助匹配失败: {e}")
            
            # 按置信度排序并限制数量
            all_matches.sort(key=lambda x: x['confidence'], reverse=True)
            result_matches = all_matches[:max_matches]
            
            self.logger.info(
                f"精确图片匹配完成: 总共找到 {len(result_matches)} 个匹配项, "
                f"高精度: {len([m for m in result_matches if m.get('precision_level') == 'high'])}, "
                f"标准: {len([m for m in result_matches if m.get('precision_level') == 'standard'])}, "
                f"OCR辅助: {len([m for m in result_matches if m.get('precision_level') == 'ocr_precise'])}"
            )
            
            return result_matches
            
        except Exception as e:
            self.logger.error(f"精确图片匹配失败: {e}")
            return []
    
    def execute_precise_click(self, reference_image_path: str, screen_region: Optional[Tuple[int, int, int, int]] = None, 
                            max_targets: int = 1, use_ocr_assist: bool = True) -> Dict[str, Any]:
        """
        执行精确图片参照点击
        
        Args:
            reference_image_path: 参照图片路径
            screen_region: 屏幕区域
            max_targets: 最大目标数量
            use_ocr_assist: 是否使用OCR辅助
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            self.logger.info(f"开始执行精确图片参照点击: {reference_image_path}")
            
            # 查找精确匹配项
            matches = self.find_precise_matches(
                reference_image_path=reference_image_path,
                screen_region=screen_region,
                max_matches=max_targets,
                use_ocr_assist=use_ocr_assist
            )
            
            if not matches:
                return {
                    'success': True,
                    'total_matches': 0,
                    'clicked_targets': 0,
                    'message': '未找到匹配的图片区域'
                }
            
            # 执行点击
            successful_clicks = 0
            failed_clicks = 0
            click_details = []
            
            for i, match in enumerate(matches):
                try:
                    # 获取点击位置（逻辑坐标）
                    click_x, click_y = match['position']
                    
                    # 执行点击（直接使用逻辑坐标，click_at_position内部会进行转换）
                    from src.ui.services.smart_click_service import get_smart_click_service
                    smart_click_service = get_smart_click_service()
                    
                    click_success = smart_click_service.click_at_position(
                        x=click_x,  # 逻辑坐标
                        y=click_y,  # 逻辑坐标
                        button="left"
                    )
                    
                    if click_success:
                        successful_clicks += 1
                        click_details.append({
                            'position': (click_x, click_y),  # 逻辑坐标
                            'confidence': match['confidence'],
                            'method': match.get('method', 'unknown'),
                            'precision_level': match.get('precision_level', 'unknown'),
                            'success': True
                        })
                        
                        self.logger.info(
                            f"精确点击成功 [{i+1}/{len(matches)}]: "
                            f"位置({click_x}, {click_y}), "
                            f"置信度: {match['confidence']:.3f}, "
                            f"方法: {match.get('method', 'unknown')}"
                        )
                    else:
                        failed_clicks += 1
                        click_details.append({
                            'position': converted_coords,
                            'confidence': match['confidence'],
                            'method': match.get('method', 'unknown'),
                            'precision_level': match.get('precision_level', 'unknown'),
                            'success': False
                        })
                        
                        self.logger.error(f"精确点击失败: {converted_coords}")
                    
                except Exception as e:
                    self.logger.error(f"执行点击时发生异常: {e}")
                    failed_clicks += 1
            
            result = {
                'success': successful_clicks > 0,
                'total_matches': len(matches),
                'clicked_targets': successful_clicks,
                'failed_clicks': failed_clicks,
                'click_details': click_details,
                'message': f"找到 {len(matches)} 个匹配项，成功点击 {successful_clicks} 个"
            }
            
            self.logger.info(
                f"精确图片参照点击完成: 匹配 {len(matches)} 个，"
                f"成功 {successful_clicks} 个，失败 {failed_clicks} 个"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"执行精确图片参照点击失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_matches': 0,
                'clicked_targets': 0
            }
    
    def optimize_reference_image(self, original_path: str, target_text: str = None, 
                               output_path: str = None) -> Optional[str]:
        """
        优化现有的参照图片，提高匹配精度
        
        Args:
            original_path: 原始参照图片路径
            target_text: 目标文字（用于OCR辅助优化）
            output_path: 输出路径（可选）
            
        Returns:
            Optional[str]: 优化后的参照图片路径
        """
        try:
            self.logger.info(f"开始优化参照图片: {original_path}")
            
            if not os.path.exists(original_path):
                self.logger.error(f"原始参照图片不存在: {original_path}")
                return None
            
            # 如果提供了目标文字，使用OCR辅助优化
            if target_text:
                # 读取原始图片
                with open(original_path, 'rb') as f:
                    image_data = f.read()
                
                # 生成优化后的输出路径
                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(original_path))[0]
                    output_dir = os.path.dirname(original_path)
                    output_path = os.path.join(output_dir, f"{base_name}_optimized.png")
                
                # 使用OCR精确定位创建优化的参照图片
                optimized_path = self._precise_ocr_service.create_precise_reference_image(
                    image_data=image_data,
                    target_text=target_text,
                    output_path=output_path,
                    padding=self.precise_padding
                )
                
                if optimized_path:
                    self.logger.info(f"参照图片OCR优化成功: {optimized_path}")
                    return optimized_path
            
            # 如果没有目标文字或OCR优化失败，进行基本的图像优化
            self.logger.info("执行基本图像优化")
            
            # 读取原始图片
            original_image = cv2.imread(original_path)
            if original_image is None:
                self.logger.error(f"无法读取原始图片: {original_path}")
                return None
            
            # 基本的图像增强处理
            # 1. 去噪
            denoised = cv2.fastNlMeansDenoisingColored(original_image, None, 10, 10, 7, 21)
            
            # 2. 锐化
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            
            # 生成输出路径
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(original_path))[0]
                output_dir = os.path.dirname(original_path)
                output_path = os.path.join(output_dir, f"{base_name}_enhanced.png")
            
            # 保存优化后的图片
            cv2.imwrite(output_path, sharpened)
            
            self.logger.info(f"参照图片基本优化完成: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"优化参照图片失败: {e}")
            return None
    
    def cleanup(self):
        """清理资源"""
        try:
            # 清理OCR精确定位服务
            if self._precise_ocr_service:
                self._precise_ocr_service.cleanup()
            
            self.logger.info("精确图片参照服务资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理精确图片参照服务资源失败: {e}")


# 全局服务实例
_precise_image_reference_service = None


def get_precise_image_reference_service() -> PreciseImageReferenceService:
    """获取精确图片参照服务实例"""
    global _precise_image_reference_service
    if _precise_image_reference_service is None:
        _precise_image_reference_service = PreciseImageReferenceService()
    return _precise_image_reference_service