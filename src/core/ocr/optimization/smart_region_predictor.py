#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能区域预测模块

@author: Mr.Rey Copyright © 2025
@description: 基于历史成功位置、窗口布局和启发式规则预测OCR目标区域，避免全屏OCR
@version: 1.0.0
@created: 2025-01-31
@modified: 2025-01-31
"""

import json
import math
import os
import shutil
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from src.config.ocr_logging_config import OCRLoggerMixin
from src.config.optimization_config_manager import OptimizationConfigManager
from src.core.ocr.utils.ocr_logger import get_logger


class PredictionSource(Enum):
    """预测来源枚举"""
    HISTORY = "history"  # 历史记录
    WINDOW_LAYOUT = "window_layout"  # 窗口布局
    HEURISTIC = "heuristic"  # 启发式规则
    TEMPLATE_MATCHING = "template_matching"  # 模板匹配
    EDGE_DETECTION = "edge_detection"  # 边缘检测


class RegionType(Enum):
    """区域类型枚举"""
    BUTTON = "button"  # 按钮
    TEXT_FIELD = "text_field"  # 文本字段
    LABEL = "label"  # 标签
    MENU = "menu"  # 菜单
    DIALOG = "dialog"  # 对话框
    UNKNOWN = "unknown"  # 未知


@dataclass
class RegionPrediction:
    """区域预测结果数据类"""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    source: str
    region_type: str = "unknown"
    target_text: Optional[str] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    @property
    def center(self) -> Tuple[int, int]:
        """获取区域中心点"""
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def area(self) -> int:
        """获取区域面积"""
        return self.width * self.height
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'confidence': self.confidence,
            'source': self.source,
            'region_type': self.region_type,
            'target_text': self.target_text,
            'timestamp': self.timestamp
        }


@dataclass
class HistoryRecord:
    """历史记录数据类"""
    target_text: str
    x: int
    y: int
    width: int
    height: int
    success_count: int = 1
    total_attempts: int = 1
    last_success: float = 0.0
    
    def __post_init__(self):
        if self.last_success == 0.0:
            self.last_success = time.time()
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        return self.success_count / max(1, self.total_attempts)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'target_text': self.target_text,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'success_count': self.success_count,
            'total_attempts': self.total_attempts,
            'last_success': self.last_success
        }


class SmartRegionPredictor(OCRLoggerMixin):
    """智能区域预测器
    
    基于多种策略预测OCR目标区域：
    - 历史成功位置记录
    - 窗口布局分析
    - 启发式规则
    - 模板匹配
    - 边缘检测
    """
    
    def __init__(self, config_manager: Optional[OptimizationConfigManager] = None):
        """初始化智能区域预测器
        
        Args:
            config_manager: 优化配置管理器，如果为None则使用默认配置
        """
        super().__init__()
        
        # 配置管理
        self.config_manager = config_manager or OptimizationConfigManager()
        
        # 从统一配置中提取区域预测配置
        try:
            optimization_config = self.config_manager.get_optimization_config()
            self.predictor_config = optimization_config.get('smart_region_predictor', {
                'enable_history': True,
                'enable_window_layout': True,
                'enable_heuristic': True,
                'enable_template_matching': False,
                'enable_edge_detection': False,
                'max_regions': 5,
                'min_confidence': 0.1,
                'history_weight': 0.8,
                'window_layout_weight': 0.4,
                'heuristic_weight': 0.6,
                'template_weight': 0.7,
                'edge_weight': 0.3,
                'history_file': 'region_prediction_history.json',
                'max_history_records': 1000,
                'cleanup_interval_days': 30
            })
        except Exception as e:
            self.log_error(f"加载区域预测配置失败，使用默认配置: {e}")
            self.predictor_config = {
                'enable_history': True,
                'enable_window_layout': True,
                'enable_heuristic': True,
                'enable_template_matching': False,
                'enable_edge_detection': False,
                'max_regions': 5,
                'min_confidence': 0.1,
                'history_weight': 0.8,
                'window_layout_weight': 0.4,
                'heuristic_weight': 0.6,
                'template_weight': 0.7,
                'edge_weight': 0.3,
                'history_file': 'region_prediction_history.json',
                'max_history_records': 1000,
                'cleanup_interval_days': 30
            }
        
        # 初始化历史记录
        self.history_path = self._get_history_file_path()
        self.history_records: List[HistoryRecord] = []
        self._load_history()
        
        # 统计信息
        self.stats = {
            'predictions': 0,
            'hits': 0,
            'history_predictions': 0,
            'layout_predictions': 0,
            'heuristic_predictions': 0,
            'template_predictions': 0,
            'edge_predictions': 0
        }
        
        self.log_info("智能区域预测器初始化完成")
    
    def _get_history_file_path(self) -> str:
        """获取历史记录文件路径"""
        try:
            # 优先使用环境变量中的项目根目录路径
            import os
            project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
            if project_root_env:
                project_root = Path(project_root_env)
            else:
                # 备用方案：从当前文件路径计算
                project_root = Path(__file__).parent.parent.parent.parent
            
            # 使用项目数据目录
            data_dir = project_root / "data" / "ocr"
            data_dir.mkdir(parents=True, exist_ok=True)
            return str(data_dir / self.predictor_config['history_file'])
        except Exception as e:
            self.log_error(f"获取历史记录文件路径失败: {e}")
            # 回退到当前目录
            return self.predictor_config['history_file']
    
    def _load_history(self):
        """加载历史记录"""
        try:
            if os.path.exists(self.history_path):
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history_records = [
                        HistoryRecord(**record) for record in data
                    ]
                self.log_info(f"加载历史记录: {len(self.history_records)}条")
            else:
                self.history_records = []
                self.log_info("未找到历史记录文件，使用空记录")
        except Exception as e:
            self.log_error(f"加载历史记录失败: {e}")
            self.history_records = []
    
    def _save_history(self):
        """保存历史记录"""
        try:
            # 清理过期记录
            self._cleanup_history()
            
            # 保存到文件
            data = [record.to_dict() for record in self.history_records]
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.log_debug(f"保存历史记录: {len(self.history_records)}条")
        except Exception as e:
            self.log_error(f"保存历史记录失败: {e}")
    
    def _cleanup_history(self):
        """清理过期历史记录"""
        try:
            current_time = time.time()
            cleanup_threshold = current_time - (self.predictor_config['cleanup_interval_days'] * 24 * 3600)
            
            # 移除过期记录
            original_count = len(self.history_records)
            self.history_records = [
                record for record in self.history_records
                if record.last_success > cleanup_threshold
            ]
            
            # 限制记录数量
            max_records = self.predictor_config['max_history_records']
            if len(self.history_records) > max_records:
                # 按成功率和最近使用时间排序，保留最好的记录
                self.history_records.sort(
                    key=lambda r: (r.success_rate, r.last_success),
                    reverse=True
                )
                self.history_records = self.history_records[:max_records]
            
            cleaned_count = original_count - len(self.history_records)
            if cleaned_count > 0:
                self.log_info(f"清理历史记录: 移除{cleaned_count}条过期记录")
                
        except Exception as e:
            self.log_error(f"清理历史记录失败: {e}")
    
    def predict_text_regions(self, 
                           image: np.ndarray, 
                           target_text: Optional[str] = None) -> List[RegionPrediction]:
        """预测文本区域
        
        Args:
            image: 输入图像
            target_text: 目标文本（可选）
            
        Returns:
            预测的区域列表
        """
        try:
            self.stats['predictions'] += 1
            regions = []
            
            # 基于历史记录预测
            if self.predictor_config.get('enable_history', True) and target_text:
                history_regions = self._predict_from_history(target_text)
                regions.extend(history_regions)
                self.stats['history_predictions'] += len(history_regions)
            
            # 基于窗口布局预测
            if self.predictor_config.get('enable_window_layout', True):
                layout_regions = self._predict_from_layout(image)
                regions.extend(layout_regions)
                self.stats['layout_predictions'] += len(layout_regions)
            
            # 启发式预测
            if self.predictor_config.get('enable_heuristic', True) and target_text:
                heuristic_regions = self._predict_heuristic(image, target_text)
                regions.extend(heuristic_regions)
                self.stats['heuristic_predictions'] += len(heuristic_regions)
            
            # 模板匹配预测
            if self.predictor_config.get('enable_template_matching', False) and target_text:
                template_regions = self._predict_from_template(image, target_text)
                regions.extend(template_regions)
                self.stats['template_predictions'] += len(template_regions)
            
            # 边缘检测预测
            if self.predictor_config.get('enable_edge_detection', False):
                edge_regions = self._predict_from_edges(image)
                regions.extend(edge_regions)
                self.stats['edge_predictions'] += len(edge_regions)
            
            # 过滤和排序
            filtered_regions = self._filter_and_sort_regions(regions)
            
            self.log_info(f"预测文本区域: {len(filtered_regions)}个区域，目标文本: {target_text or 'None'}")
            return filtered_regions
            
        except Exception as e:
            self.log_error(f"预测文本区域失败: {e}")
            return []
    
    def _predict_from_history(self, target_text: str) -> List[RegionPrediction]:
        """基于历史记录预测
        
        Args:
            target_text: 目标文本
            
        Returns:
            预测区域列表
        """
        regions = []
        
        try:
            for record in self.history_records:
                if record.target_text == target_text:
                    confidence = record.success_rate * self.predictor_config['history_weight']
                    
                    # 考虑时间衰减
                    time_factor = self._calculate_time_decay(record.last_success)
                    confidence *= time_factor
                    
                    regions.append(RegionPrediction(
                        x=record.x,
                        y=record.y,
                        width=record.width,
                        height=record.height,
                        confidence=confidence,
                        source=PredictionSource.HISTORY.value,
                        target_text=target_text
                    ))
            
            self.log_debug(f"历史记录预测: {len(regions)}个区域")
            
        except Exception as e:
            self.log_error(f"历史记录预测失败: {e}")
        
        return regions
    
    def _predict_from_layout(self, image: np.ndarray) -> List[RegionPrediction]:
        """基于窗口布局预测
        
        Args:
            image: 输入图像
            
        Returns:
            预测区域列表
        """
        regions = []
        
        try:
            h, w = image.shape[:2]
            base_confidence = self.predictor_config['window_layout_weight']
            
            # 常见的UI区域布局
            layout_regions = [
                # 顶部区域（标题栏、菜单栏）
                (int(w*0.1), int(h*0.05), int(w*0.8), int(h*0.15), RegionType.LABEL.value),
                # 底部区域（状态栏、按钮栏）
                (int(w*0.1), int(h*0.8), int(w*0.8), int(h*0.15), RegionType.BUTTON.value),
                # 中心区域（主要内容）
                (int(w*0.2), int(h*0.3), int(w*0.6), int(h*0.4), RegionType.TEXT_FIELD.value),
                # 右下角（确认按钮）
                (int(w*0.6), int(h*0.7), int(w*0.3), int(h*0.2), RegionType.BUTTON.value),
                # 左上角（返回按钮）
                (int(w*0.05), int(h*0.05), int(w*0.2), int(h*0.1), RegionType.BUTTON.value)
            ]
            
            for x, y, width, height, region_type in layout_regions:
                # 确保区域在图像范围内
                x = max(0, min(x, w - 1))
                y = max(0, min(y, h - 1))
                width = min(width, w - x)
                height = min(height, h - y)
                
                if width > 0 and height > 0:
                    regions.append(RegionPrediction(
                        x=x, y=y, width=width, height=height,
                        confidence=base_confidence * 0.5,  # 布局预测置信度较低
                        source=PredictionSource.WINDOW_LAYOUT.value,
                        region_type=region_type
                    ))
            
            self.log_debug(f"窗口布局预测: {len(regions)}个区域")
            
        except Exception as e:
            self.log_error(f"窗口布局预测失败: {e}")
        
        return regions
    
    def _predict_heuristic(self, image: np.ndarray, target_text: str) -> List[RegionPrediction]:
        """启发式预测
        
        Args:
            image: 输入图像
            target_text: 目标文本
            
        Returns:
            预测区域列表
        """
        regions = []
        
        try:
            h, w = image.shape[:2]
            base_confidence = self.predictor_config['heuristic_weight']
            
            # 基于目标文本特征的启发式规则
            target_lower = target_text.lower()
            
            # 按钮类文本
            button_keywords = ['继续', 'continue', '确定', 'ok', '取消', 'cancel', '提交', 'submit', '登录', 'login']
            if any(keyword in target_lower for keyword in button_keywords):
                # 按钮通常在底部或右下角
                regions.extend([
                    RegionPrediction(
                        x=int(w*0.6), y=int(h*0.7), width=int(w*0.3), height=int(h*0.2),
                        confidence=base_confidence * 0.8,
                        source=PredictionSource.HEURISTIC.value,
                        region_type=RegionType.BUTTON.value,
                        target_text=target_text
                    ),
                    RegionPrediction(
                        x=int(w*0.3), y=int(h*0.8), width=int(w*0.4), height=int(h*0.15),
                        confidence=base_confidence * 0.6,
                        source=PredictionSource.HEURISTIC.value,
                        region_type=RegionType.BUTTON.value,
                        target_text=target_text
                    )
                ])
            
            # 标题类文本
            title_keywords = ['标题', 'title', '名称', 'name', '主题', 'subject']
            if any(keyword in target_lower for keyword in title_keywords):
                # 标题通常在顶部
                regions.append(RegionPrediction(
                    x=int(w*0.1), y=int(h*0.05), width=int(w*0.8), height=int(h*0.2),
                    confidence=base_confidence * 0.7,
                    source=PredictionSource.HEURISTIC.value,
                    region_type=RegionType.LABEL.value,
                    target_text=target_text
                ))
            
            # 输入框类文本
            input_keywords = ['输入', 'input', '密码', 'password', '用户名', 'username', '搜索', 'search']
            if any(keyword in target_lower for keyword in input_keywords):
                # 输入框通常在中间区域
                regions.append(RegionPrediction(
                    x=int(w*0.2), y=int(h*0.3), width=int(w*0.6), height=int(h*0.4),
                    confidence=base_confidence * 0.6,
                    source=PredictionSource.HEURISTIC.value,
                    region_type=RegionType.TEXT_FIELD.value,
                    target_text=target_text
                ))
            
            self.log_debug(f"启发式预测: {len(regions)}个区域")
            
        except Exception as e:
            self.log_error(f"启发式预测失败: {e}")
        
        return regions
    
    def _predict_from_template(self, image: np.ndarray, target_text: str) -> List[RegionPrediction]:
        """基于模板匹配预测（预留接口）
        
        Args:
            image: 输入图像
            target_text: 目标文本
            
        Returns:
            预测区域列表
        """
        # TODO: 实现模板匹配预测
        return []
    
    def _predict_from_edges(self, image: np.ndarray) -> List[RegionPrediction]:
        """基于边缘检测预测（预留接口）
        
        Args:
            image: 输入图像
            
        Returns:
            预测区域列表
        """
        # TODO: 实现边缘检测预测
        return []
    
    def _calculate_time_decay(self, last_success: float) -> float:
        """计算时间衰减因子
        
        Args:
            last_success: 最后成功时间
            
        Returns:
            时间衰减因子（0-1之间）
        """
        try:
            current_time = time.time()
            time_diff = current_time - last_success
            
            # 使用指数衰减，半衰期为7天
            half_life = 7 * 24 * 3600  # 7天
            decay_factor = math.exp(-time_diff * math.log(2) / half_life)
            
            return max(0.1, decay_factor)  # 最小保持10%的权重
            
        except Exception as e:
            self.log_error(f"计算时间衰减失败: {e}")
            return 0.5
    
    def _filter_and_sort_regions(self, regions: List[RegionPrediction]) -> List[RegionPrediction]:
        """过滤和排序区域
        
        Args:
            regions: 原始区域列表
            
        Returns:
            过滤和排序后的区域列表
        """
        try:
            # 过滤低置信度区域
            min_confidence = self.predictor_config['min_confidence']
            filtered = [r for r in regions if r.confidence >= min_confidence]
            
            # 去重（合并重叠区域）
            filtered = self._merge_overlapping_regions(filtered)
            
            # 按置信度排序
            filtered.sort(key=lambda r: r.confidence, reverse=True)
            
            # 限制数量
            max_regions = self.predictor_config['max_regions']
            return filtered[:max_regions]
            
        except Exception as e:
            self.log_error(f"过滤和排序区域失败: {e}")
            return regions
    
    def _merge_overlapping_regions(self, regions: List[RegionPrediction]) -> List[RegionPrediction]:
        """合并重叠区域
        
        Args:
            regions: 区域列表
            
        Returns:
            合并后的区域列表
        """
        if not regions:
            return regions
        
        try:
            merged = []
            
            for region in regions:
                merged_with_existing = False
                
                for i, existing in enumerate(merged):
                    if self._calculate_overlap_ratio(region, existing) > 0.5:
                        # 合并区域，保留置信度更高的属性
                        if region.confidence > existing.confidence:
                            merged[i] = region
                        merged_with_existing = True
                        break
                
                if not merged_with_existing:
                    merged.append(region)
            
            return merged
            
        except Exception as e:
            self.log_error(f"合并重叠区域失败: {e}")
            return regions
    
    def _calculate_overlap_ratio(self, region1: RegionPrediction, region2: RegionPrediction) -> float:
        """计算两个区域的重叠比例
        
        Args:
            region1: 区域1
            region2: 区域2
            
        Returns:
            重叠比例（0-1之间）
        """
        try:
            # 计算交集
            x1 = max(region1.x, region2.x)
            y1 = max(region1.y, region2.y)
            x2 = min(region1.x + region1.width, region2.x + region2.width)
            y2 = min(region1.y + region1.height, region2.y + region2.height)
            
            if x2 <= x1 or y2 <= y1:
                return 0.0
            
            intersection = (x2 - x1) * (y2 - y1)
            union = region1.area + region2.area - intersection
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            self.log_error(f"计算重叠比例失败: {e}")
            return 0.0
    
    def record_success(self, region: RegionPrediction, target_text: str):
        """记录成功的预测
        
        Args:
            region: 成功的区域
            target_text: 目标文本
        """
        try:
            self.stats['hits'] += 1
            
            # 查找现有记录
            existing_record = None
            for record in self.history_records:
                if (record.target_text == target_text and
                    abs(record.x - region.x) < 50 and
                    abs(record.y - region.y) < 50):
                    existing_record = record
                    break
            
            if existing_record:
                # 更新现有记录
                existing_record.success_count += 1
                existing_record.total_attempts += 1
                existing_record.last_success = time.time()
            else:
                # 创建新记录
                new_record = HistoryRecord(
                    target_text=target_text,
                    x=region.x,
                    y=region.y,
                    width=region.width,
                    height=region.height
                )
                self.history_records.append(new_record)
            
            # 保存历史记录
            self._save_history()
            
            self.log_info(f"记录成功预测: {target_text} at ({region.x}, {region.y})")
            
        except Exception as e:
            self.log_error(f"记录成功预测失败: {e}")
    
    def record_failure(self, target_text: str):
        """记录失败的预测
        
        Args:
            target_text: 目标文本
        """
        try:
            # 更新相关记录的尝试次数
            for record in self.history_records:
                if record.target_text == target_text:
                    record.total_attempts += 1
            
            # 保存历史记录
            self._save_history()
            
            self.log_debug(f"记录失败预测: {target_text}")
            
        except Exception as e:
            self.log_error(f"记录失败预测失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            统计信息字典
        """
        try:
            hit_rate = self.stats['hits'] / max(1, self.stats['predictions'])
            
            return {
                'predictions': self.stats['predictions'],
                'hits': self.stats['hits'],
                'hit_rate': hit_rate,
                'history_predictions': self.stats['history_predictions'],
                'layout_predictions': self.stats['layout_predictions'],
                'heuristic_predictions': self.stats['heuristic_predictions'],
                'template_predictions': self.stats['template_predictions'],
                'edge_predictions': self.stats['edge_predictions'],
                'history_records': len(self.history_records)
            }
            
        except Exception as e:
            self.log_error(f"获取统计信息失败: {e}")
            return {}
    
    def export_history(self, file_path: str) -> bool:
        """导出历史记录
        
        Args:
            file_path: 导出文件路径
            
        Returns:
            是否成功
        """
        try:
            shutil.copy2(self.history_path, file_path)
            self.log_info(f"历史记录已导出到: {file_path}")
            return True
        except Exception as e:
            self.log_error(f"导出历史记录失败: {e}")
            return False
    
    def import_history(self, file_path: str) -> bool:
        """导入历史记录
        
        Args:
            file_path: 导入文件路径
            
        Returns:
            是否成功
        """
        try:
            shutil.copy2(file_path, self.history_path)
            self._load_history()
            self.log_info(f"历史记录已从 {file_path} 导入")
            return True
        except Exception as e:
            self.log_error(f"导入历史记录失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        try:
            self._save_history()
            self.log_info("智能区域预测器资源清理完成")
        except Exception as e:
            self.log_error(f"清理资源失败: {e}")


if __name__ == '__main__':
    # 测试代码
    predictor = SmartRegionPredictor()
    
    # 创建测试图像
    test_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    # 预测区域
    regions = predictor.predict_text_regions(test_image, "继续")
    
    from src.ui.services.logging_service import get_logger
    logger = get_logger("SmartRegionPredictorTest", "OCR")
    
    logger.info(f"Predicted {len(regions)} regions:")
    for i, region in enumerate(regions):
        logger.info(f"  {i+1}. {region.source}: ({region.x}, {region.y}, {region.width}, {region.height}) confidence={region.confidence:.3f}")
    
    logger.info(f"Stats: {predictor.get_stats()}")