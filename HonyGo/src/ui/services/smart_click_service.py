#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HonyGo 智能模拟点击服务
实现多目标点击排序（自下而上、自左而右）和避免重复点击功能
集成OCR识别、关键字匹配和点击动画
@author: Mr.Rey Copyright © 2025
@created: 2025-01-15 00:00:00
@modified: 2025-01-15 00:00:00
@version: 1.0.0
"""

import base64
import hashlib
import io
import os
import time
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
import pyautogui

# 禁用PyAutoGUI的fail-safe机制，避免鼠标移动到边缘时触发异常
pyautogui.FAILSAFE = False
from PIL import Image
from PIL import ImageGrab
from PySide6.QtCore import QObject
from PySide6.QtCore import Signal
from src.core.ocr.services.ocr_pool_manager import get_pool_manager
from src.core.ocr.utils.keyword_matcher import KeywordMatcher
from src.core.ocr.utils.keyword_matcher import MatchStrategy
from src.ui.services.coordinate_service import get_coordinate_service
from src.ui.services.logging_service import get_logger
# 已移除动画相关导入
from src.ui.widgets.keyword_marker import KeywordMarkerWidget
from src.ui.widgets.keyword_marker import hide_keyword_marker
from src.ui.widgets.keyword_marker import show_keyword_marker
# 旧的复杂动画已删除，使用新的简单动画
# 延迟导入避免循环导入
# from src.ui.services.image_reference_service import ImageReferenceService


@dataclass
class ClickTarget:
    """点击目标数据类"""
    text: str
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    confidence: float
    center_x: int
    center_y: int
    similarity: float = 0.0
    source: str = 'ocr'  # 'ocr' 或 'image_reference'


class SmartClickService(QObject):
    """智能模拟点击服务"""
    
    # 信号定义
    click_performed = Signal(int, int, str)  # x, y, button
    multi_click_completed = Signal(int)  # success_count
    multiple_targets_found = Signal(int)  # target_count
    click_sequence_completed = Signal(int)  # clicked_count
    log_message = Signal(str)  # 日志消息信号
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('SmartClickService')
        self.coordinate_service = get_coordinate_service()  # 初始化坐标服务
        self.image_reference_service = None  # 延迟初始化避免循环导入
        self.keyword_matcher = KeywordMatcher()
        
        # 点击历史和统计
        self.click_history: Set[Tuple[int, int]] = set()
        self.click_history_detailed: List[Dict[str, Any]] = []
        self.last_cleanup_time = time.time()
        
        # 配置参数
        self.click_interval = 100  # 毫秒
        self.min_confidence = 0.7
        self.min_similarity = 0.8
        self.marker_enabled = False     # 禁用蓝色标记动画
        self.sort_bottom_to_top = True
        self.sort_left_to_right = True
        
        # 关键词标记管理
        self.active_markers: List[KeywordMarkerWidget] = []
        
        # 点击状态通信
        self._simulation_task_service = None  # 延迟初始化避免循环导入
        
        # 鼠标初始化配置
        self.mouse_initialization_enabled = True  # 启用鼠标初始化
        self.initialization_position = 'bottom_right'  # 初始化位置：'bottom_right', 'top_left', 'center'
        
        self.logger.info("智能点击服务初始化完成")
    
    def set_simulation_task_service(self, simulation_task_service):
        """
        设置模拟任务服务引用（用于点击状态通信）
        
        Args:
            simulation_task_service: 模拟任务服务实例
        """
        self._simulation_task_service = simulation_task_service
        self.logger.debug("已设置模拟任务服务引用")
    
    def _notify_click_start(self):
        """
        通知模拟任务服务点击操作开始
        """
        try:
            if self._simulation_task_service and hasattr(self._simulation_task_service, '_set_click_in_progress'):
                self._simulation_task_service._set_click_in_progress(True)
                self.logger.debug("已通知模拟任务服务：点击操作开始")
        except Exception as e:
            self.logger.warning(f"通知点击开始失败: {e}")
    
    def _notify_click_end(self):
        """
        通知模拟任务服务点击操作结束
        """
        try:
            if self._simulation_task_service and hasattr(self._simulation_task_service, '_set_click_in_progress'):
                self._simulation_task_service._set_click_in_progress(False)
                self.logger.debug("已通知模拟任务服务：点击操作结束")
        except Exception as e:
            self.logger.warning(f"通知点击结束失败: {e}")
    
    def click_at_position(self, x: int, y: int, button: str = 'left') -> bool:
        """
        在指定位置执行点击操作（兼容性方法）
        
        Args:
            x: X坐标（逻辑坐标）
            y: Y坐标（逻辑坐标）
            button: 鼠标按键 ('left', 'right', 'middle')
            
        Returns:
            bool: 点击是否成功
        """
        try:
            # 转换逻辑坐标为物理坐标进行点击
            click_x, click_y = self.coordinate_service.logical_to_physical(x, y)
            
            # 执行点击
            if button == 'right':
                pyautogui.rightClick(click_x, click_y)
            elif button == 'middle':
                pyautogui.middleClick(click_x, click_y)
            else:
                pyautogui.click(click_x, click_y)
            
            # 发送点击信号（使用原始逻辑坐标）
            self.click_performed.emit(x, y, button)
            
            self.logger.info(f"点击操作成功完成: {button}键点击位置({x}, {y}) -> 物理坐标({click_x}, {click_y})")
            return True
            
        except Exception as e:
            self.logger.error(f"点击操作失败: 位置({x}, {y}), 按键={button}, 错误: {e}")
            return False
    
    def configure_click_behavior(self, click_interval: int = None, 
                               min_confidence: float = None, 
                               min_similarity: float = None,
                               animation_enabled: bool = None,
                               marker_enabled: bool = None,
                               simple_indicator_enabled: bool = None,
                               sort_bottom_to_top: bool = None,
                               sort_left_to_right: bool = None,
                               mouse_initialization_enabled: bool = None,
                               initialization_position: str = None) -> None:
        """
        配置点击行为参数
        
        Args:
            click_interval: 点击间隔时间（毫秒）
            min_confidence: 最小置信度阈值
            min_similarity: 最小相似度阈值
            animation_enabled: 是否启用原有复杂点击动画（已弃用）
            marker_enabled: 是否启用蓝色关键词标记（已弃用）
            simple_indicator_enabled: 是否启用新的简单点击指示器
            sort_bottom_to_top: 是否自下而上排序
            sort_left_to_right: 是否自左而右排序
        """
        try:
            if click_interval is not None:
                self.click_interval = max(50, click_interval)  # 最小50ms间隔
                self.logger.info(f"设置点击间隔: {self.click_interval}ms")
            
            if min_confidence is not None:
                self.min_confidence = max(0.0, min(1.0, min_confidence))  # 限制在0-1范围
                self.logger.info(f"设置最小置信度: {self.min_confidence}")
            
            if min_similarity is not None:
                self.min_similarity = max(0.0, min(1.0, min_similarity))  # 限制在0-1范围
                self.logger.info(f"设置最小相似度: {self.min_similarity}")
            
            if marker_enabled is not None:
                self.marker_enabled = marker_enabled
                self.logger.info(f"设置蓝色关键词标记: {'启用' if self.marker_enabled else '禁用'}（已弃用）")
            
            if sort_bottom_to_top is not None:
                self.sort_bottom_to_top = sort_bottom_to_top
                self.logger.info(f"设置自下而上排序: {'启用' if self.sort_bottom_to_top else '禁用'}")
            
            if sort_left_to_right is not None:
                self.sort_left_to_right = sort_left_to_right
                self.logger.info(f"设置自左而右排序: {'启用' if self.sort_left_to_right else '禁用'}")
            
            if mouse_initialization_enabled is not None:
                self.mouse_initialization_enabled = mouse_initialization_enabled
                self.logger.info(f"设置鼠标初始化: {'启用' if self.mouse_initialization_enabled else '禁用'}")
            
            if initialization_position is not None:
                if initialization_position in ['bottom_right', 'top_left', 'center']:
                    self.initialization_position = initialization_position
                    self.logger.info(f"设置初始化位置: {initialization_position}")
                else:
                    self.logger.warning(f"无效的初始化位置: {initialization_position}，保持原设置")
            
            self.logger.info("点击行为配置更新完成")
            
        except Exception as e:
            self.logger.error(f"配置点击行为时发生异常: {e}")
    
    def configure_keyword_marker(self, enabled: bool = True) -> None:
        """
        配置关键词标记功能
        
        Args:
            enabled: 是否启用关键词标记功能
        """
        try:
            self.marker_enabled = enabled
            self.logger.info(f"关键词标记功能: {'启用' if enabled else '禁用'}")
            
            if not enabled:
                # 如果禁用标记功能，隐藏所有现有标记
                self.hide_all_markers()
                
        except Exception as e:
            self.logger.error(f"配置关键词标记功能时发生异常: {e}")
    
    # 已移除动画配置方法
    
    # 已移除动画持续时间计算方法
    
    def _get_image_reference_service(self):
        """获取图片参照服务实例（延迟导入避免循环导入）"""
        if self.image_reference_service is None:
            from src.ui.services.image_reference_service import ImageReferenceService
            self.image_reference_service = ImageReferenceService()
        return self.image_reference_service
    
    def perform_click(self, x: int, y: int, button: str = 'left') -> bool:
        """
        执行单次点击操作（内部方法，期望接收物理坐标）
        
        Args:
            x: X坐标（物理坐标，用于实际点击）
            y: Y坐标（物理坐标，用于实际点击）
            button: 鼠标按键 ('left', 'right', 'middle')
            
        Returns:
            bool: 点击是否成功
        """
        try:
            # 使用传入的坐标进行点击（调用方已经转换过）
            click_x, click_y = x, y
            
            # 通知模拟任务服务点击操作开始（避免鼠标移动检测误判）
            self._notify_click_start()
            
            try:
                # 执行点击 - 直接使用pyautogui，因为传入的已经是物理坐标
                # 避免coordinate_service的二次坐标转换
                if button == 'right':
                    pyautogui.rightClick(click_x, click_y)
                elif button == 'middle':
                    pyautogui.middleClick(click_x, click_y)
                else:
                    pyautogui.click(click_x, click_y)
                
                # 已移除点击动画显示
                
                self.logger.debug(f"点击坐标: ({click_x}, {click_y})")
                
                # 发送点击信号（使用原始坐标）
                self.click_performed.emit(x, y, button)
                
                self.logger.info(f"点击操作成功完成: {button}键点击位置({x}, {y})")
                return True
                
            finally:
                # 通知模拟任务服务点击操作结束
                self._notify_click_end()
            
        except Exception as e:
            self.logger.error(f"点击操作失败: 位置({x}, {y}), 按键={button}, 错误: {e}")
            return False
    
    def perform_multi_click(self, positions: List[Tuple[int, int]], button: str = 'left',
                          click_interval: int = 100) -> int:
        """
        执行多目标点击
        
        Args:
            positions: 点击位置列表
            button: 鼠标按键
            click_interval: 点击间隔（毫秒）
            
        Returns:
            int: 成功点击的数量
        """
        success_count = 0
        
        # 按照配置排序位置
        sorted_positions = self._sort_positions(positions)
        
        for i, (x, y) in enumerate(sorted_positions):
            try:
                if self.perform_click(x, y, button):
                    success_count += 1
                
                # 点击间隔
                if i < len(sorted_positions) - 1:  # 不是最后一个
                    time.sleep(click_interval / 1000.0)
                    
            except Exception as e:
                self.logger.error(f"多目标点击失败: ({x}, {y}), 错误: {e}")
        
        # 发送完成信号
        self.multi_click_completed.emit(success_count)
        
        self.logger.info(f"多目标点击完成: 成功 {success_count}/{len(positions)} 个目标")
        return success_count
    
    def _sort_positions(self, positions: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        排序点击位置（自下而上、自左而右）
        
        Args:
            positions: 位置列表
            
        Returns:
            List[Tuple[int, int]]: 排序后的位置列表
        """
        try:
            # 多级排序：首先按Y坐标（下到上或上到下），然后按X坐标（左到右或右到左）
            sorted_positions = sorted(positions, key=lambda pos: (
                -pos[1] if self.sort_bottom_to_top else pos[1],  # Y坐标
                pos[0] if self.sort_left_to_right else -pos[0]   # X坐标
            ))
            
            return sorted_positions
            
        except Exception as e:
            self.logger.error(f"位置排序失败: {e}")
            return positions
    
    def _sort_targets(self, targets: List[ClickTarget]) -> List[ClickTarget]:
        """
        排序点击目标（自下而上、自左而右）
        
        Args:
            targets: 目标列表
            
        Returns:
            List[ClickTarget]: 排序后的目标列表
        """
        try:
            # 多级排序：首先按Y坐标（下到上或上到下），然后按X坐标（左到右或右到左）
            sorted_targets = sorted(targets, key=lambda target: (
                -target.center_y if self.sort_bottom_to_top else target.center_y,  # Y坐标
                target.center_x if self.sort_left_to_right else -target.center_x   # X坐标
            ))
            
            return sorted_targets
            
        except Exception as e:
            self.logger.error(f"目标排序失败: {e}")
            return targets
    
    def _execute_click_sequence(self, targets: List[ClickTarget], monitor_frequency: float = None) -> Dict[str, Any]:
        """
        执行点击序列
        
        Args:
            targets: 目标列表
            monitor_frequency: 监控频率（秒），用于计算最优动画时间
            
        Returns:
            Dict[str, Any]: 点击结果
        """
        successful_clicks = []
        failed_clicks = []
        skipped_clicks = []
        
        for i, target in enumerate(targets):
            try:
                # 执行点击（使用逻辑坐标，click_at_position内部进行坐标转换）
                if self.click_at_position(
                    target.center_x, target.center_y, 
                    button='left'
                ):
                    successful_clicks.append({
                        'target': target,
                        'position': (target.center_x, target.center_y),  # 记录原始逻辑坐标
                        'text': target.text,
                        'confidence': target.confidence
                    })
                    
                    # 隐藏对应位置的标记（使用逻辑坐标）
                    if self.marker_enabled:
                        self.hide_marker_at_position(target.center_x, target.center_y)
                else:
                    failed_clicks.append({
                        'target': target,
                        'position': (target.center_x, target.center_y),  # 逻辑坐标
                        'text': target.text,
                        'error': 'Click execution failed'
                    })
                
                # 点击间隔
                if i < len(targets) - 1:
                    time.sleep(self.click_interval / 1000.0)
                    
            except Exception as e:
                failed_clicks.append({
                    'target': target,
                    'position': (target.center_x, target.center_y),
                    'text': target.text,
                    'error': str(e)
                })
        
        # 点击序列完成后初始化鼠标位置
        self._initialize_mouse_position()
        
        return {
            'successful_clicks': successful_clicks,
            'failed_clicks': failed_clicks,
            'skipped_clicks': skipped_clicks
        }
    
    def clear_click_history(self):
        """清理点击历史"""
        self.click_history.clear()
        self.click_history_detailed.clear()
        self.last_cleanup_time = time.time()
        self.logger.debug("点击历史已清理")
    
    def get_click_statistics(self) -> Dict[str, Any]:
        """获取点击统计信息"""
        total_clicks = len(self.click_history_detailed)
        unique_clicks = len(self.click_history)
        duplicate_clicks = max(0, total_clicks - unique_clicks)
        
        return {
            'total_clicks': total_clicks,
            'unique_clicks': unique_clicks,
            'duplicate_clicks': duplicate_clicks,
            'success_rate': 100.0 if total_clicks == 0 else (unique_clicks / total_clicks) * 100,
            'average_interval': self.click_interval,
            'click_history_count': len(self.click_history),
            'last_cleanup_time': self.last_cleanup_time,
            'min_confidence': self.min_confidence,
            'min_similarity': self.min_similarity,
            'sort_bottom_to_top': self.sort_bottom_to_top,
            'sort_left_to_right': self.sort_left_to_right
        }
    
    def _show_keyword_markers(self, targets: List[ClickTarget]):
        """显示关键词匹配蓝色标记"""
        try:
            # 先隐藏之前的标记
            self.hide_all_markers()
            
            for target in targets:
                x, y, width, height = target.bbox
                center_x = x + width // 2
                center_y = y + height // 2
                
                # 显示蓝色标记
                marker = show_keyword_marker(center_x, center_y, width, height)
                if marker:
                    self.active_markers.append(marker)
                    self.logger.debug(f"显示关键词蓝色标记: '{target.text}' at ({center_x}, {center_y})")
            
            self.logger.info(f"已显示 {len(self.active_markers)} 个关键词蓝色标记")
            
        except Exception as e:
            self.logger.error(f"显示关键词标记失败: {e}")
    
    def hide_all_markers(self):
        """隐藏所有关键词标记"""
        try:
            for marker in self.active_markers:
                hide_keyword_marker(marker)
            
            self.active_markers.clear()
            self.logger.debug("已隐藏所有关键词标记")
            
        except Exception as e:
            self.logger.error(f"隐藏关键词标记失败: {e}")
    
    def hide_marker_at_position(self, x: int, y: int):
        """隐藏指定位置的关键词标记"""
        try:
            markers_to_remove = []
            for marker in self.active_markers:
                # 检查标记是否在指定位置附近（容差范围内）
                marker_center_x = marker.x() + marker.width() // 2
                marker_center_y = marker.y() + marker.height() // 2
                
                # 使用50像素的容差范围
                if abs(marker_center_x - x) <= 50 and abs(marker_center_y - y) <= 50:
                    hide_keyword_marker(marker)
                    markers_to_remove.append(marker)
                    self.logger.debug(f"隐藏位置({x}, {y})附近的关键词标记")
            
            # 从活动列表中移除
            for marker in markers_to_remove:
                if marker in self.active_markers:
                    self.active_markers.remove(marker)
                    
        except Exception as e:
            self.logger.error(f"隐藏指定位置标记失败: {e}")
    
    def _initialize_mouse_position(self):
        """
        将鼠标移动到屏幕左上角最顶端进行初始化，避免干扰下次图像匹配
        
        @author: Mr.Rey Copyright © 2025
        @created: 2025-01-04 23:00:00
        @modified: 2025-01-04 23:30:00
        @version: 1.1.0
        """
        if not self.mouse_initialization_enabled:
            return
        
        try:
            # 始终移动到屏幕左上角最顶端，避免触发PyAutoGUI故障保护机制
            target_x = 0
            target_y = 0
            
            # 使用坐标服务转换为物理坐标
            physical_x, physical_y = self.coordinate_service.logical_to_physical(target_x, target_y)
            
            # 移动鼠标到目标位置
            pyautogui.moveTo(physical_x, physical_y, duration=0.2)
            
            self.logger.info(f"鼠标已初始化到屏幕左上角: 逻辑坐标({target_x}, {target_y}), 物理坐标({physical_x}, {physical_y})")
            
        except Exception as e:
            self.logger.error(f"鼠标初始化失败: {e}")
    
    def _execute_image_reference_clicks(self, targets: List[ClickTarget], start_time: float, monitor_frequency: float = None) -> Dict[str, Any]:
        """执行图片参照专用的点击流程"""
        try:
            self.logger.info(f"图片参照模式: 找到 {len(targets)} 个匹配目标")
            self.multiple_targets_found.emit(len(targets))
            
            # 图片参照模式直接点击，不需要复杂的排序和过滤
            # 按置信度排序，优先点击最匹配的目标
            sorted_targets = sorted(targets, key=lambda t: t.confidence, reverse=True)
            
            # 显示关键词匹配蓝色标记
            if self.marker_enabled:
                self._show_keyword_markers(sorted_targets)
                # 等待1秒让用户看到蓝色标记（图片参照模式缩短等待时间）
                self.logger.info("显示蓝色标记，等待1秒后开始点击")
                time.sleep(1.0)
            
            # 执行点击序列（传递监控频率参数）
            click_results = self._execute_click_sequence(sorted_targets, monitor_frequency)
            
            # 点击完成后初始化鼠标位置
            self._initialize_mouse_position()
            
            total_time = time.time() - start_time
            
            result = {
                'success': True,
                'total_targets': len(targets),
                'unique_targets': len(sorted_targets),
                'clicked_targets': len(click_results['successful_clicks']),
                'failed_clicks': len(click_results['failed_clicks']),
                'skipped_clicks': len(click_results['skipped_clicks']),
                'total_time': total_time,
                'click_details': click_results,
                'algorithm_type': 'image_reference'
            }
            
            self.logger.info(
                f"图片参照点击完成: 总目标={len(targets)}, "
                f"成功点击={len(click_results['successful_clicks'])}, "
                f"失败={len(click_results['failed_clicks'])}, "
                f"耗时={total_time:.3f}s"
            )
            
            self.click_sequence_completed.emit(len(click_results['successful_clicks']))
            return result
            
        except Exception as e:
            self.logger.error(f"图片参照点击执行异常: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_ocr_clicks(self, targets: List[ClickTarget], start_time: float, max_targets: int) -> Dict[str, Any]:
        """执行OCR专用的点击流程"""
        try:
            self.logger.info(f"OCR模式: 找到 {len(targets)} 个匹配目标")
            self.multiple_targets_found.emit(len(targets))
            
            # OCR模式使用完整的处理流程
            # 不再过滤重复目标，允许重复点击
            unique_targets = targets
            
            # 限制目标数量
            if len(unique_targets) > max_targets:
                unique_targets = unique_targets[:max_targets]
                self.logger.info(f"限制目标数量为 {max_targets} 个")
            
            # 排序目标（自下而上、自左而右）
            sorted_targets = self._sort_targets(unique_targets)
            
            # 显示关键词匹配蓝色标记
            if self.marker_enabled:
                self._show_keyword_markers(sorted_targets)
                # 等待2秒让用户看到蓝色标记
                self.logger.info("显示蓝色标记，等待2秒后开始点击")
                time.sleep(2.0)
            
            # 执行点击序列
            click_results = self._execute_click_sequence(sorted_targets)
            
            # 点击完成后初始化鼠标位置
            self._initialize_mouse_position()
            
            total_time = time.time() - start_time
            
            result = {
                'success': True,
                'total_targets': len(targets),
                'unique_targets': len(unique_targets),
                'clicked_targets': len(click_results['successful_clicks']),
                'failed_clicks': len(click_results['failed_clicks']),
                'skipped_clicks': len(click_results['skipped_clicks']),
                'total_time': total_time,
                'click_details': click_results,
                'algorithm_type': 'ocr'
            }
            
            self.logger.info(
                f"OCR点击完成: 总目标={len(targets)}, "
                f"成功点击={len(click_results['successful_clicks'])}, "
                f"失败={len(click_results['failed_clicks'])}, "
                f"跳过={len(click_results['skipped_clicks'])}, "
                f"耗时={total_time:.3f}s"
            )
            
            self.click_sequence_completed.emit(len(click_results['successful_clicks']))
            return result
            
        except Exception as e:
            self.logger.error(f"OCR点击执行异常: {e}")
            return {'success': False, 'error': str(e)}
    
    def smart_click_targets(self, target_keyword: str, monitor_area: Optional[Dict[str, int]] = None,
                          max_targets: int = 5, strategy: MatchStrategy = MatchStrategy.CONTAINS,
                          use_precise_positioning: bool = True) -> Dict[str, Any]:
        """
        基于OCR池的智能目标点击
        
        Args:
            target_keyword: 目标关键词
            monitor_area: 监控区域配置字典 {'x': int, 'y': int, 'width': int, 'height': int}
            max_targets: 最大目标数量
            strategy: 匹配策略
            use_precise_positioning: 是否启用精确定位
            
        Returns:
            Dict: 点击结果
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"开始OCR池智能目标点击: {target_keyword}")
            
            # 获取OCR池管理器
            pool_manager = get_pool_manager()
            if not pool_manager:
                return {'success': False, 'error': 'OCR池管理器未初始化'}
            
            # 截取屏幕
            if monitor_area:
                # 将字典格式转换为ImageGrab.grab需要的bbox元组格式
                bbox = (monitor_area['x'], monitor_area['y'], 
                       monitor_area['x'] + monitor_area['width'], 
                       monitor_area['y'] + monitor_area['height'])
                screenshot = ImageGrab.grab(bbox=bbox)
            else:
                screenshot = ImageGrab.grab()
            
            # 转换为base64
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # 调用OCR池进行识别
            self.logger.info(f"OCR池识别，精确定位: {use_precise_positioning}")
            ocr_result = pool_manager.process_ocr_request(
                image_data=image_base64,
                request_type="recognize",
                keywords=[target_keyword],
                enable_precise_positioning=use_precise_positioning
            )
            if not ocr_result.get('success'):
                return {'success': False, 'error': f"OCR识别失败: {ocr_result.get('error', '未知错误')}"}
            
            # 获取OCR结果
            ocr_data = ocr_result.get('data', [])
            if not ocr_data:
                self.logger.info("OCR未识别到任何文本")
                return {
                    'success': True,
                    'total_targets': 0,
                    'clicked_targets': 0,
                    'click_details': {'successful_clicks': [], 'failed_clicks': [], 'skipped_clicks': []}
                }
            
            # 优先使用精确定位结果
            precise_positions = []
            if isinstance(ocr_data, dict) and 'precise_positions' in ocr_data:
                precise_positions = ocr_data['precise_positions']
                # 使用原始OCR结果进行关键词匹配
                ocr_data = ocr_data.get('original_result', ocr_data.get('processed_result', []))
            
            # 使用关键词匹配器查找目标
            keyword_matcher = KeywordMatcher()
            matches = keyword_matcher.find_matches(ocr_data, target_keyword, strategy)
            
            if not matches and not precise_positions:
                self.logger.info(f"未找到匹配关键词 '{target_keyword}' 的目标")
                return {
                    'success': True,
                    'total_targets': 0,
                    'clicked_targets': 0,
                    'click_details': {'successful_clicks': [], 'failed_clicks': [], 'skipped_clicks': []}
                }
            
            # 转换为ClickTarget对象，优先使用精确定位结果
            targets = []
            
            # 1. 首先添加精确定位的目标
            for precise_pos in precise_positions[:max_targets]:
                center_x = precise_pos['center_x']
                center_y = precise_pos['center_y']
                
                # 如果有监控区域偏移，需要调整坐标
                if monitor_area:
                    offset_x = int(monitor_area.get('x', 0))
                    offset_y = int(monitor_area.get('y', 0))
                    center_x += offset_x
                    center_y += offset_y
                
                target = ClickTarget(
                    text=precise_pos['text'],
                    bbox=precise_pos['bbox'],
                    confidence=float(precise_pos['confidence']),
                    center_x=center_x,
                    center_y=center_y,
                    similarity=float(precise_pos['confidence']),
                    source='ocr_precise'
                )
                targets.append(target)
                self.logger.info(f"添加精确定位目标: '{precise_pos['text']}' -> ({center_x}, {center_y})")
            
            # 2. 如果精确定位结果不足，补充常规匹配结果
            if len(targets) < max_targets and matches:
                remaining_slots = max_targets - len(targets)
                
                for match in matches[:remaining_slots]:
                    bbox = match.get('bbox', [0, 0, 0, 0])
                    
                    # 使用KeywordMatcher的bbox解析方法来处理不同格式的bbox
                    parsed_bbox = keyword_matcher._parse_bbox(bbox)
                    if parsed_bbox is None:
                        self.logger.warning(f"bbox数据解析失败: {bbox}")
                        continue
                    
                    x, y, w, h = parsed_bbox
                    
                    center_x = x + w // 2
                    center_y = y + h // 2
                    
                    # 如果有监控区域偏移，需要调整坐标
                    if monitor_area:
                        offset_x = int(monitor_area.get('x', 0))
                        offset_y = int(monitor_area.get('y', 0))
                        center_x += offset_x
                        center_y += offset_y
                    
                    # 检查是否与精确定位结果重复（避免重复点击同一位置）
                    is_duplicate = False
                    for existing_target in targets:
                        if abs(existing_target.center_x - center_x) < 10 and abs(existing_target.center_y - center_y) < 10:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        target = ClickTarget(
                            text=match.get('text', ''),
                            bbox=(x, y, w, h),
                            confidence=float(match.get('confidence', 0.0)),
                            center_x=center_x,
                            center_y=center_y,
                            similarity=float(match.get('similarity', 0.0)),
                            source='ocr_standard'
                        )
                        targets.append(target)
                        self.logger.info(f"添加标准OCR目标: '{match.get('text', '')}' -> ({center_x}, {center_y})")
            
            if not targets:
                return {
                    'success': True,
                    'total_targets': 0,
                    'clicked_targets': 0,
                    'click_details': {'successful_clicks': [], 'failed_clicks': [], 'skipped_clicks': []}
                }
            
            # 执行点击序列
            return self._execute_ocr_clicks(targets, start_time, max_targets)
            
        except Exception as e:
            self.logger.error(f"OCR池智能目标点击异常: {e}")
            return {'success': False, 'error': str(e)}
    
    def smart_click_by_image(self, reference_image_path: str, monitor_area: Optional[Dict[str, int]] = None, 
                           max_targets: int = 5, similarity_threshold: float = 0.7, 
                           use_precise_matching: bool = True, monitor_frequency: float = None) -> Dict[str, Any]:
        """
        基于图片参照的智能点击
        
        Args:
            reference_image_path: 参照图片路径
            monitor_area: 监控区域配置
            max_targets: 最大目标数量
            similarity_threshold: 相似度阈值
            use_precise_matching: 是否启用精确匹配
            monitor_frequency: 监控频率（秒），用于计算最优动画时间
            
        Returns:
            Dict: 点击结果
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"开始图片参照智能点击: {reference_image_path}, 精确匹配: {use_precise_matching}")
            
            # 加载参照图片
            if not self._get_image_reference_service().load_reference_image(reference_image_path):
                return {'success': False, 'error': '加载参照图片失败'}
            
            # 执行图片匹配
            # 转换monitor_area格式
            screen_region = None
            if monitor_area:
                screen_region = (monitor_area.get('x', 0), monitor_area.get('y', 0), 
                               monitor_area.get('width', 1920), monitor_area.get('height', 1080))
            
            # 使用较低的阈值获取所有可能的匹配项，然后在服务层面进行过滤
            image_service = self._get_image_reference_service()
            original_threshold = image_service._config.confidence_threshold
            # 设置一个很低的阈值以获取所有匹配项
            image_service._config.confidence_threshold = 0.01
            
            try:
                matches = image_service.find_matches(
                    screen_region=screen_region,
                    target_keyword=reference_image_path,
                    max_matches=max_targets * 2,  # 获取更多匹配项用于过滤
                    use_precise_matching=use_precise_matching
                )
            finally:
                # 恢复原始阈值
                image_service._config.confidence_threshold = original_threshold
            
            # 在服务层面按用户指定的阈值过滤匹配项
            self.logger.info(f"开始服务层过滤，原始匹配项数: {len(matches)}, 阈值: {similarity_threshold}")
            filtered_matches = []
            for i, match in enumerate(matches):
                confidence = match.get('confidence', 0)
                self.logger.info(f"匹配项{i+1}: 置信度={confidence:.6f}, 阈值={similarity_threshold}")
                if confidence >= similarity_threshold:
                    filtered_matches.append(match)
                    self.logger.info(f"匹配项{i+1}通过过滤，置信度{confidence:.6f} >= 阈值{similarity_threshold}")
                else:
                    self.logger.info(f"匹配项{i+1}被过滤，置信度{confidence:.6f} < 阈值{similarity_threshold}")
            
            matches = filtered_matches[:max_targets]  # 限制最终结果数量
            self.logger.info(f"服务层过滤完成，最终匹配项数: {len(matches)}")
            
            if not matches:
                self.logger.info("未找到匹配的图片区域")
                return {
                    'success': True,
                    'total_targets': 0,
                    'clicked_targets': 0,
                    'click_details': {'successful_clicks': [], 'failed_clicks': [], 'skipped_clicks': []}
                }
            
            # 转换为ClickTarget格式
            targets = []
            self.logger.info(f"开始处理 {len(matches)} 个匹配项，阈值: {similarity_threshold}")
            
            for i, match in enumerate(matches):
                confidence = match['confidence']
                self.logger.info(f"匹配项 {i+1}: 置信度={confidence:.6f}, 阈值={similarity_threshold:.6f}, 满足条件: {confidence >= similarity_threshold}")
                
                if confidence >= similarity_threshold:
                    # 根据匹配方法设置源标识
                    source = match.get('method', 'image_reference')
                    precision_level = match.get('precision_level', 'standard')
                    
                    # 图像匹配结果的position字段已经是逻辑坐标中心点，直接使用
                    target = ClickTarget(
                        text=f"图片匹配_{len(targets)+1}_{precision_level}",
                        bbox=match['bbox'],
                        confidence=match['confidence'],
                        center_x=match['position'][0],  # 逻辑坐标中心点X
                        center_y=match['position'][1],  # 逻辑坐标中心点Y
                        similarity=match['similarity'],
                        source=f"{source}_{precision_level}"
                    )
                    targets.append(target)
                    self.logger.info(f"添加图片匹配目标: {target.text} -> ({target.center_x}, {target.center_y}), 方法: {source}, 精度: {precision_level}")
                else:
                    self.logger.info(f"匹配项 {i+1} 置信度不足，跳过: {confidence:.6f} < {similarity_threshold:.6f}")
            
            if not targets:
                self.logger.info(f"未找到相似度大于{similarity_threshold}的匹配目标")
                return {
                    'success': True,
                    'total_targets': len(matches),
                    'clicked_targets': 0,
                    'click_details': {'successful_clicks': [], 'failed_clicks': [], 'skipped_clicks': []}
                }
            
            # 执行图片参照点击流程
            return self._execute_image_reference_clicks(targets, start_time, monitor_frequency)
            
        except Exception as e:
            self.logger.error(f"图片参照智能点击异常: {e}")
            return {'success': False, 'error': str(e)}
    
    def cleanup(self):
        """
        清理资源
        """
        try:
            self.logger.info("开始清理智能点击服务资源")
            
            # 清理关键词标记
            self.hide_all_markers()
            
            # 清理点击历史
            self.clear_click_history()
            
            # 已移除动画清理
            
            # 清理关键字匹配器缓存
            if hasattr(self, 'keyword_matcher'):
                self.keyword_matcher.clear_cache()
            
            self.logger.info("智能点击服务资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理智能点击服务资源时发生异常: {e}")


# 全局服务实例
_smart_click_service = None


def get_smart_click_service() -> SmartClickService:
    """获取智能点击服务实例"""
    global _smart_click_service
    if _smart_click_service is None:
        _smart_click_service = SmartClickService()
    return _smart_click_service