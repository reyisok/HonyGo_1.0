#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROI (Region of Interest) 服务
实现智能屏幕区域预选和用户可配置的感兴趣区域设置

@author: Mr.Rey Copyright © 2025
"""

from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional
)
import json
import os
import time

from PySide6.QtCore import QObject, QRect, Signal
from PySide6.QtWidgets import QApplication

from src.ui.services.logging_service import get_logger
















class ROIService(QObject):
    """
    ROI服务类，负责管理感兴趣区域的配置和优化
    """
    
    # 信号定义
    roi_updated = Signal(dict)  # ROI更新信号
    roi_selected = Signal(QRect)  # ROI选择信号
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        
        # 优先使用环境变量中的项目根目录路径，确保路径一致性
        project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
        if project_root_env:
            project_root = Path(project_root_env)
        else:
            # 备用方案：从 src/ui/services 向上到项目根目录
            project_root = Path(__file__).parent.parent.parent
        
        self.config_file = project_root / "src" / "config" / "roi_config.json"
        self.roi_regions: List[Dict[str, Any]] = []
        self.active_roi: Optional[QRect] = None
        self.screen_cache: Dict[str, Any] = {}
        self.roi_history: List[Dict[str, Any]] = []
        
        # 初始化服务
        self._load_roi_config()
        self.logger.info("ROI服务初始化完成")
    
    def _load_roi_config(self) -> bool:
        """
        加载ROI配置文件
        
        Returns:
            bool: 加载是否成功
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.roi_regions = config.get('roi_regions', [])
                    self.roi_history = config.get('roi_history', [])
                    self.logger.info(f"ROI配置加载成功，共{len(self.roi_regions)}个区域")
            else:
                # 创建默认配置
                self._create_default_config()
                self.logger.info("创建默认ROI配置")
            return True
        except Exception as e:
            self.logger.error(f"ROI配置加载失败: {e}")
            return False
    
    def _create_default_config(self):
        """
        创建默认ROI配置
        """
        # 获取屏幕尺寸
        app = QApplication.instance()
        if not app:
            self.logger.warning("QApplication实例不存在，使用默认屏幕尺寸")
            width, height = 1920, 1080
        else:
            screen = app.primaryScreen()
            if screen:
                screen_rect = screen.geometry()
                width, height = screen_rect.width(), screen_rect.height()
            else:
                self.logger.warning("未检测到屏幕，使用默认屏幕尺寸")
                width, height = 1920, 1080
            
            # 创建默认区域：全屏、中心区域、底部区域
            self.roi_regions = [
                {
                    "name": "全屏区域",
                    "x": 0,
                    "y": 0,
                    "width": width,
                    "height": height,
                    "priority": 1,
                    "enabled": True,
                    "description": "完整屏幕区域"
                },
                {
                    "name": "中心区域",
                    "x": width // 4,
                    "y": height // 4,
                    "width": width // 2,
                    "height": height // 2,
                    "priority": 2,
                    "enabled": True,
                    "description": "屏幕中心区域，常见UI元素位置"
                },
                {
                    "name": "底部区域",
                    "x": 0,
                    "y": height * 3 // 4,
                    "width": width,
                    "height": height // 4,
                    "priority": 3,
                    "enabled": True,
                    "description": "屏幕底部区域，任务栏和按钮位置"
                }
            ]
            self._save_roi_config()
    
    def _save_roi_config(self) -> bool:
        """
        保存ROI配置到文件
        
        Returns:
            bool: 保存是否成功
        """
        try:
            # 确保配置目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config = {
                "roi_regions": self.roi_regions,
                "roi_history": self.roi_history,
                "last_updated": time.time()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.logger.info("ROI配置保存成功")
            return True
        except Exception as e:
            self.logger.error(f"ROI配置保存失败: {e}")
            return False
    
    def add_roi_region(self, name: str, x: int, y: int, width: int, height: int, 
                      priority: int = 1, description: str = "") -> bool:
        """
        添加新的ROI区域
        
        Args:
            name: 区域名称
            x: X坐标
            y: Y坐标
            width: 宽度
            height: 高度
            priority: 优先级（数字越小优先级越高）
            description: 描述
            
        Returns:
            bool: 添加是否成功
        """
        try:
            roi_region = {
                "name": name,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "priority": priority,
                "enabled": True,
                "description": description,
                "created_time": time.time()
            }
            
            self.roi_regions.append(roi_region)
            self.roi_regions.sort(key=lambda r: r['priority'])
            
            if self._save_roi_config():
                self.roi_updated.emit(roi_region)
                self.logger.info(f"ROI区域添加成功: {name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"ROI区域添加失败: {e}")
            return False
    
    def remove_roi_region(self, name: str) -> bool:
        """
        删除ROI区域
        
        Args:
            name: 区域名称
            
        Returns:
            bool: 删除是否成功
        """
        try:
            original_count = len(self.roi_regions)
            self.roi_regions = [r for r in self.roi_regions if r['name'] != name]
            
            if len(self.roi_regions) < original_count:
                if self._save_roi_config():
                    self.logger.info(f"ROI区域删除成功: {name}")
                    return True
            
            self.logger.warning(f"ROI区域未找到: {name}")
            return False
        except Exception as e:
            self.logger.error(f"ROI区域删除失败: {e}")
            return False
    
    def get_optimal_roi(self, target_keyword: str = "") -> Optional[QRect]:
        """
        根据历史数据和关键词获取最优ROI区域
        
        Args:
            target_keyword: 目标关键词
            
        Returns:
            QRect: 最优ROI区域，如果没有则返回None
        """
        try:
            # 根据历史数据分析最优区域
            if target_keyword and self.roi_history:
                # 查找该关键词的历史成功区域
                keyword_history = [
                    h for h in self.roi_history 
                    if h.get('keyword') == target_keyword and h.get('success')
                ]
                
                if keyword_history:
                    # 选择最近成功的区域
                    latest_success = max(keyword_history, key=lambda h: h.get('timestamp', 0))
                    roi_name = latest_success.get('roi_name')
                    
                    # 查找对应的ROI区域
                    for region in self.roi_regions:
                        if region['name'] == roi_name and region['enabled']:
                            rect = QRect(region['x'], region['y'], region['width'], region['height'])
                            self.logger.info(f"基于历史数据选择ROI: {roi_name}")
                            return rect
            
            # 如果没有历史数据，选择优先级最高的启用区域
            enabled_regions = [r for r in self.roi_regions if r['enabled']]
            if enabled_regions:
                best_region = min(enabled_regions, key=lambda r: r['priority'])
                rect = QRect(best_region['x'], best_region['y'], 
                           best_region['width'], best_region['height'])
                self.logger.info(f"选择优先级最高的ROI: {best_region['name']}")
                return rect
            
            return None
        except Exception as e:
            self.logger.error(f"获取最优ROI失败: {e}")
            return None
    
    def record_roi_result(self, roi_name: str, keyword: str, success: bool, 
                         response_time: float = 0.0):
        """
        记录ROI使用结果
        
        Args:
            roi_name: ROI区域名称
            keyword: 搜索关键词
            success: 是否成功
            response_time: 响应时间
        """
        try:
            result = {
                "roi_name": roi_name,
                "keyword": keyword,
                "success": success,
                "response_time": response_time,
                "timestamp": time.time()
            }
            
            self.roi_history.append(result)
            
            # 保持历史记录在合理范围内（最多1000条）
            if len(self.roi_history) > 1000:
                self.roi_history = self.roi_history[-1000:]
            
            self._save_roi_config()
            self.logger.debug(f"ROI结果记录: {roi_name} - {keyword} - {'成功' if success else '失败'}")
        except Exception as e:
            self.logger.error(f"ROI结果记录失败: {e}")
    
    def get_roi_regions(self) -> List[Dict[str, Any]]:
        """
        获取所有ROI区域
        
        Returns:
            List[Dict]: ROI区域列表
        """
        return self.roi_regions.copy()
    
    def enable_roi_region(self, name: str, enabled: bool = True) -> bool:
        """
        启用或禁用ROI区域
        
        Args:
            name: 区域名称
            enabled: 是否启用
            
        Returns:
            bool: 操作是否成功
        """
        try:
            for region in self.roi_regions:
                if region['name'] == name:
                    region['enabled'] = enabled
                    if self._save_roi_config():
                        self.logger.info(f"ROI区域{'启用' if enabled else '禁用'}: {name}")
                        return True
                    break
            return False
        except Exception as e:
            self.logger.error(f"ROI区域状态更新失败: {e}")
            return False
    
    def get_roi_statistics(self) -> Dict[str, Any]:
        """
        获取ROI使用统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            stats = {
                "total_regions": len(self.roi_regions),
                "enabled_regions": len([r for r in self.roi_regions if r['enabled']]),
                "total_history": len(self.roi_history),
                "success_rate": 0.0,
                "average_response_time": 0.0,
                "most_successful_roi": None
            }
            
            if self.roi_history:
                successful = [h for h in self.roi_history if h.get('success')]
                stats['success_rate'] = len(successful) / len(self.roi_history) * 100
                
                response_times = [h.get('response_time', 0) for h in self.roi_history if h.get('response_time')]
                if response_times:
                    stats['average_response_time'] = sum(response_times) / len(response_times)
                
                # 统计最成功的ROI
                roi_success_count = {}
                for h in successful:
                    roi_name = h.get('roi_name')
                    if roi_name:
                        roi_success_count[roi_name] = roi_success_count.get(roi_name, 0) + 1
                
                if roi_success_count:
                    stats['most_successful_roi'] = max(roi_success_count, key=roi_success_count.get)
            
            return stats
        except Exception as e:
            self.logger.error(f"获取ROI统计信息失败: {e}")
            return {}
    
    def cleanup(self):
        """
        清理服务资源
        """
        try:
            self._save_roi_config()
            self.logger.info("ROI服务清理完成")
        except Exception as e:
            self.logger.error(f"ROI服务清理失败: {e}")