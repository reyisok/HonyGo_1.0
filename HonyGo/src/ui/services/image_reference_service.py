#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片参照服务模块

提供基于图片相似度匹配的智能点击服务，整合图片匹配算法、
统一坐标转换服务和统一鼠标模拟点击服务。

@author: Mr.Rey Copyright © 2025
@created: 2025-01-13 15:30:00
@modified: 2025-01-13 15:30:00
"""

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal
from src.core.algorithms.image_reference_algorithm import ImageReferenceAlgorithm, MatchMethod, MatchResult
from src.ui.services.coordinate_service import get_coordinate_service
from src.ui.services.logging_service import get_logger
# 延迟导入避免循环导入
# from src.ui.services.smart_click_service import SmartClickService


@dataclass
class ImageReferenceConfig:
    """图片参照配置"""
    reference_image_path: str = ""
    match_method: MatchMethod = MatchMethod.TEMPLATE_MATCHING
    confidence_threshold: float = 0.1  # 进一步降低置信度阈值以确保匹配成功
    monitor_region: Optional[Tuple[int, int, int, int]] = None
    click_interval: float = 0.5
    mouse_button: str = "left"
    enable_click_animation: bool = True
    disable_ocr: bool = False  # 禁用OCR算法，仅使用纯图像匹配


class ImageReferenceService(QObject):
    """图片参照服务
    
    提供基于图片相似度匹配的智能点击服务
    """
    
    # 信号定义
    match_found = Signal(dict)  # 找到匹配项时发出
    click_performed = Signal(dict)  # 执行点击时发出
    error_occurred = Signal(str)  # 发生错误时发出
    
    def __init__(self, config: Optional[ImageReferenceConfig] = None):
        """初始化图片参照服务
        
        Args:
            config: 服务配置
        """
        super().__init__()
        self.logger = get_logger("ImageReferenceService")
        self._config = config or ImageReferenceConfig()
        self._algorithm = ImageReferenceAlgorithm()
        self._coordinate_service = get_coordinate_service()
        self._smart_click_service = None
        self._reference_image = None
        self._is_running = False
        self._last_click_time = 0.0
        
        # 加载参照图片
        if self._config.reference_image_path:
            self.load_reference_image(self._config.reference_image_path)
            
    def _get_smart_click_service(self):
        """获取智能点击服务实例（延迟导入避免循环导入）"""
        if self._smart_click_service is None:
            from src.ui.services.smart_click_service import SmartClickService
            self._smart_click_service = SmartClickService()
        return self._smart_click_service
        
    def load_reference_image(self, image_path: str) -> bool:
        """加载参照图片
        
        Args:
            image_path: 图片路径
            
        Returns:
            bool: 加载是否成功
        """
        try:
            if not os.path.exists(image_path):
                self.logger.error(f"参照图片不存在: {image_path}")
                return False
                
            self._reference_image = cv2.imread(image_path)
            if self._reference_image is None:
                self.logger.error(f"无法加载参照图片: {image_path}")
                return False
                
            self._config.reference_image_path = image_path
            self.logger.info(f"成功加载参照图片: {image_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"加载参照图片失败: {e}")
            return False
            
    def update_config(self, config: ImageReferenceConfig):
        """更新配置
        
        Args:
            config: 新配置
        """
        self._config = config
        if config.reference_image_path and config.reference_image_path != getattr(self._config, 'reference_image_path', ''):
            self.load_reference_image(config.reference_image_path)
            
    def find_matches(self, screen_region: Optional[Tuple[int, int, int, int]] = None, 
                    target_keyword: str = "", max_matches: int = 10, use_precise_matching: bool = True) -> List[Dict[str, Any]]:
        """查找匹配项（支持精确匹配）
        
        Args:
            screen_region: 屏幕区域
            target_keyword: 目标关键字或图片路径
            max_matches: 最大匹配数量
            use_precise_matching: 是否使用精确匹配
            
        Returns:
            List[Dict[str, Any]]: 匹配结果列表
        """
        try:
            # 如果启用精确匹配，优先使用精确图片参照服务
            if use_precise_matching:
                try:
                    from src.ui.services.precise_image_reference_service import get_precise_image_reference_service
                    precise_service = get_precise_image_reference_service()
                    
                    # 如果target_keyword是图片路径，使用精确匹配
                    if target_keyword and os.path.exists(target_keyword):
                        # 根据配置决定是否使用OCR辅助
                        use_ocr_assist = not self._config.disable_ocr
                        
                        if self._config.disable_ocr:
                            self.logger.info("OCR算法已禁用，仅使用纯图像匹配")
                        
                        precise_matches = precise_service.find_precise_matches(
                            reference_image_path=target_keyword,
                            screen_region=screen_region,
                            max_matches=max_matches,
                            use_ocr_assist=use_ocr_assist
                        )
                        
                        if precise_matches:
                            self.logger.info(f"精确图片匹配找到 {len(precise_matches)} 个结果")
                            return precise_matches
                        else:
                            self.logger.info("精确匹配未找到结果，回退到标准匹配")
                    
                except Exception as e:
                    self.logger.warning(f"精确匹配失败，回退到标准匹配: {e}")
            
            # 标准匹配流程
            # 截取屏幕
            screenshot = self._coordinate_service.capture_screen(screen_region)
            if screenshot is None:
                self.logger.error("屏幕截取失败")
                return []
                
            screen_array = np.array(screenshot)
            screen_image = cv2.cvtColor(screen_array, cv2.COLOR_RGB2BGR)
            
            # 如果target_keyword是图片路径，加载参照图片
            if target_keyword and os.path.exists(target_keyword):
                reference_image = cv2.imread(target_keyword)
                if reference_image is None:
                    self.logger.error(f"无法加载参照图片: {target_keyword}")
                    return []
            else:
                # 使用当前配置的参照图片
                if self._reference_image is None:
                    self.logger.warning("未设置参照图片")
                    return []
                reference_image = self._reference_image
                
            # 执行匹配
            matches = self._algorithm.find_image_matches(
                screen_image=screen_image,
                reference_image=reference_image,
                method=self._config.match_method,
                min_confidence=self._config.confidence_threshold
            )
            
            # 转换为SmartClickService期望的格式
            result_matches = []
            for match in matches[:max_matches]:
                result_match = {
                    'confidence': match.confidence,
                    'similarity': match.confidence,  # 图片匹配中confidence即为similarity
                    'bbox': match.bounding_box if match.bounding_box else (
                        match.position[0] - 10, match.position[1] - 10, 20, 20
                    ),
                    'position': match.position,
                    'method': 'standard_template',
                    'precision_level': 'standard'
                }
                result_matches.append(result_match)
                
            self.logger.info(f"标准图片匹配找到 {len(result_matches)} 个结果")
            return result_matches
            
        except Exception as e:
            self.logger.error(f"图片匹配失败: {e}")
            return []
            
    def click_matches(self, matches: List[MatchResult]) -> Dict[str, Any]:
        """点击匹配项
        
        Args:
            matches: 匹配结果列表
            
        Returns:
            Dict[str, Any]: 点击结果统计
        """
        click_results = {
            'total_matches': len(matches),
            'successful_clicks': 0,
            'failed_clicks': 0,
            'click_positions': [],
            'errors': []
        }
        
        try:
            for i, match in enumerate(matches):
                # 检查点击间隔
                current_time = time.time()
                if current_time - self._last_click_time < self._config.click_interval:
                    time.sleep(self._config.click_interval - (current_time - self._last_click_time))
                    
                # 执行点击（直接使用逻辑坐标，click_at_position内部会进行转换）
                click_success = self._get_smart_click_service().click_at_position(
                    x=match.position[0],  # 逻辑坐标
                    y=match.position[1],  # 逻辑坐标
                    button=self._config.mouse_button
                )
                
                if click_success:
                    click_results['successful_clicks'] += 1
                    click_results['click_positions'].append({
                        'original': match.position,
                        'logical': match.position,  # 逻辑坐标
                        'confidence': match.confidence
                    })
                    
                    self.logger.info(
                        f"点击成功 [{i+1}/{len(matches)}]: "
                        f"逻辑坐标{match.position}, 置信度: {match.confidence:.3f}"
                    )
                    
                    # 发送点击执行信号
                    self.click_performed.emit({
                        'position': match.position,  # 逻辑坐标
                        'confidence': match.confidence,
                        'success': True
                    })
                    
                else:
                    error_msg = f"点击失败: {match.position}"
                    self.logger.error(error_msg)
                    click_results['failed_clicks'] += 1
                    click_results['errors'].append(error_msg)
                    
                    self.click_performed.emit({
                        'position': match.position,  # 逻辑坐标
                        'confidence': match.confidence,
                        'success': False
                    })
                    
                self._last_click_time = time.time()
                
        except Exception as e:
            error_msg = f"点击匹配项失败: {e}"
            self.logger.error(error_msg)
            click_results['errors'].append(error_msg)
            self.error_occurred.emit(error_msg)
            
        return click_results
        
    def execute_single_match(self, screen_region: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        """执行单次匹配和点击
        
        Args:
            screen_region: 屏幕区域，None表示全屏
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            # 使用配置中的监控区域（如果未指定）
            if screen_region is None:
                screen_region = self._config.monitor_region
                
            # 查找匹配项
            matches = self.find_matches(screen_region)
            
            if not matches:
                result = {
                    'success': False,
                    'message': '未找到匹配项',
                    'matches_found': 0,
                    'clicks_performed': 0
                }
                self.logger.info("未找到匹配项")
                return result
                
            # 点击匹配项
            click_results = self.click_matches(matches)
            
            result = {
                'success': click_results['successful_clicks'] > 0,
                'message': f"找到 {click_results['total_matches']} 个匹配项，成功点击 {click_results['successful_clicks']} 个",
                'matches_found': click_results['total_matches'],
                'clicks_performed': click_results['successful_clicks'],
                'click_details': click_results
            }
            
            self.logger.info(result['message'])
            return result
            
        except Exception as e:
            error_msg = f"执行单次匹配失败: {e}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return {
                'success': False,
                'message': error_msg,
                'matches_found': 0,
                'clicks_performed': 0
            }
            
    def start_continuous_monitoring(self, interval: float = 1.0) -> bool:
        """开始持续监控
        
        Args:
            interval: 监控间隔(秒)
            
        Returns:
            bool: 启动是否成功
        """
        try:
            if self._is_running:
                self.logger.warning("图片参照服务已在运行")
                return False
                
            if self._reference_image is None:
                self.logger.error("未加载参照图片，无法启动监控")
                return False
                
            self._is_running = True
            self.logger.info(f"开始图片参照持续监控，间隔: {interval}秒")
            return True
            
        except Exception as e:
            self.logger.error(f"启动持续监控失败: {e}")
            return False
            
    def stop_continuous_monitoring(self) -> bool:
        """停止持续监控
        
        Returns:
            bool: 停止是否成功
        """
        try:
            if not self._is_running:
                self.logger.warning("图片参照服务未在运行")
                return False
                
            self._is_running = False
            self.logger.info("停止图片参照持续监控")
            return True
            
        except Exception as e:
            self.logger.error(f"停止持续监控失败: {e}")
            return False
            
    def is_running(self) -> bool:
        """检查服务是否运行中
        
        Returns:
            bool: 是否运行中
        """
        return self._is_running
        
    def get_config(self) -> ImageReferenceConfig:
        """获取当前配置
        
        Returns:
            ImageReferenceConfig: 当前配置
        """
        return self._config
        
    def get_reference_image_info(self) -> Optional[Dict[str, Any]]:
        """获取参照图片信息
        
        Returns:
            Optional[Dict[str, Any]]: 图片信息，None表示未加载
        """
        if self._reference_image is None:
            return None
            
        return {
            'path': self._config.reference_image_path,
            'shape': self._reference_image.shape,
            'size': os.path.getsize(self._config.reference_image_path) if os.path.exists(self._config.reference_image_path) else 0
        }
        
    def cleanup(self):
        """清理资源"""
        try:
            self.stop_continuous_monitoring()
            self._reference_image = None
            self.logger.info("图片参照服务资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")