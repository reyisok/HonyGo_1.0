#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能检测服务
实现基于历史数据的智能区域预测和自适应检测策略

@author: Mr.Rey Copyright © 2025
"""

from collections import defaultdict, deque
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple
)
import json
import os
import time

from PySide6.QtCore import QObject, QTimer, Signal
from dataclasses import dataclass, field
import statistics
import threading

from src.ui.services.logging_service import get_logger
from src.ui.services.unified_timer_service import get_timer_service
















@dataclass
class DetectionRecord:
    """
    检测记录数据类
    """
    timestamp: float
    target_text: str
    found_region: Optional[Tuple[int, int, int, int]]  # (x, y, width, height)
    confidence: float
    processing_time: float
    screen_resolution: Tuple[int, int]
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegionPattern:
    """
    区域模式数据类
    """
    region: Tuple[int, int, int, int]  # (x, y, width, height)
    frequency: int
    success_rate: float
    avg_confidence: float
    last_seen: float
    target_texts: List[str]
    avg_processing_time: float


class IntelligentDetectionService(QObject):
    """
    智能检测服务类，负责基于历史数据的智能区域预测和自适应检测策略
    """
    
    # 信号定义
    pattern_discovered = Signal(dict)  # 发现新模式信号
    prediction_made = Signal(dict)  # 预测完成信号
    strategy_updated = Signal(dict)  # 策略更新信号
    performance_improved = Signal(dict)  # 性能改进信号
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        
        # 服务配置
        self.config = {
            "enable_learning": True,           # 启用学习功能
            "min_pattern_frequency": 3,       # 最小模式频率
            "pattern_similarity_threshold": 0.8,  # 模式相似度阈值
            "max_history_size": 1000,         # 最大历史记录数
            "prediction_confidence_threshold": 0.7,  # 预测置信度阈值
            "adaptive_interval_enabled": True,  # 启用自适应间隔
            "base_detection_interval": 1000,   # 基础检测间隔（毫秒）
            "max_detection_interval": 5000,    # 最大检测间隔（毫秒）
            "min_detection_interval": 200,     # 最小检测间隔（毫秒）
            "learning_rate": 0.1,              # 学习率
            "pattern_decay_time": 86400        # 模式衰减时间（秒，24小时）
        }
        
        # 历史检测记录
        self.detection_history: deque = deque(maxlen=self.config["max_history_size"])
        
        # 区域模式库
        self.region_patterns: Dict[str, RegionPattern] = {}
        
        # 目标文字统计
        self.text_statistics = defaultdict(lambda: {
            "total_detections": 0,
            "successful_detections": 0,
            "avg_processing_time": 0.0,
            "preferred_regions": [],
            "detection_intervals": deque(maxlen=50),
            "last_detection_time": 0.0
        })
        
        # 屏幕区域热力图
        self.heatmap_data = defaultdict(int)
        
        # 自适应检测间隔
        self.adaptive_intervals = defaultdict(lambda: self.config["base_detection_interval"])
        
        # 预测缓存
        self.prediction_cache: Dict[str, Dict[str, Any]] = {}
        
        # 性能指标
        self.performance_metrics = {
            "prediction_accuracy": 0.0,
            "avg_prediction_time": 0.0,
            "pattern_discovery_rate": 0.0,
            "adaptive_improvement": 0.0,
            "total_predictions": 0,
            "correct_predictions": 0
        }
        
        # 持久化文件
        # 优先使用环境变量中的项目根目录路径，确保路径一致性
        project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
        if project_root_env:
            project_root = Path(project_root_env)
        else:
            # 备用方案：从 src/ui/services 向上到项目根目录
            project_root = Path(__file__).parent.parent.parent
        
        self.data_file = project_root / "src" / "config" / "intelligent_detection_data.json"
        
        # 获取统一定时器服务
        self.timer_service = get_timer_service()
        
        # 创建分析定时器（保留QTimer作为备用）
        if threading.current_thread() == threading.main_thread():
            self.analysis_timer = QTimer()
            self.analysis_timer.timeout.connect(self._analyze_patterns)
        else:
            self.analysis_timer = None
        
        # 定时器任务ID
        self.analysis_task_id = f"intelligent_detection_analysis_{id(self)}"
        
        # 初始化服务
        self._load_historical_data()
        # 不自动启动模式分析定时器，改为按需启动
        
        self.logger.info("智能检测服务初始化完成")
    
    def _load_historical_data(self):
        """
        加载历史数据
        """
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 加载区域模式
                patterns_data = data.get('region_patterns', {})
                for key, pattern_dict in patterns_data.items():
                    self.region_patterns[key] = RegionPattern(
                        region=tuple(pattern_dict['region']),
                        frequency=pattern_dict['frequency'],
                        success_rate=pattern_dict['success_rate'],
                        avg_confidence=pattern_dict['avg_confidence'],
                        last_seen=pattern_dict['last_seen'],
                        target_texts=pattern_dict['target_texts'],
                        avg_processing_time=pattern_dict['avg_processing_time']
                    )
                
                # 加载文字统计
                text_stats = data.get('text_statistics', {})
                for text, stats in text_stats.items():
                    # 将detection_intervals从列表转换回deque
                    if 'detection_intervals' in stats:
                        stats['detection_intervals'] = deque(stats['detection_intervals'], maxlen=50)
                    self.text_statistics[text].update(stats)
                
                # 加载热力图数据
                self.heatmap_data.update(data.get('heatmap_data', {}))
                
                # 加载自适应间隔
                self.adaptive_intervals.update(data.get('adaptive_intervals', {}))
                
                # 加载性能指标
                self.performance_metrics.update(data.get('performance_metrics', {}))
                
                self.logger.info(f"历史数据加载完成，模式数量: {len(self.region_patterns)}")
        except Exception as e:
            self.logger.error(f"历史数据加载失败: {e}")
    
    def _save_historical_data(self):
        """
        保存历史数据
        """
        try:
            # 确保配置目录存在
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 准备保存数据
            data = {
                "region_patterns": {
                    key: {
                        "region": pattern.region,
                        "frequency": pattern.frequency,
                        "success_rate": pattern.success_rate,
                        "avg_confidence": pattern.avg_confidence,
                        "last_seen": pattern.last_seen,
                        "target_texts": pattern.target_texts,
                        "avg_processing_time": pattern.avg_processing_time
                    }
                    for key, pattern in self.region_patterns.items()
                },
                "text_statistics": {
                    key: {
                        **{k: v for k, v in stats.items() if k != "detection_intervals"},
                        "detection_intervals": list(stats["detection_intervals"])
                    }
                    for key, stats in self.text_statistics.items()
                },
                "heatmap_data": dict(self.heatmap_data),
                "adaptive_intervals": dict(self.adaptive_intervals),
                "performance_metrics": self.performance_metrics,
                "last_updated": time.time()
            }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug("历史数据保存成功")
        except Exception as e:
            self.logger.error(f"历史数据保存失败: {e}")
    
    def _start_pattern_analysis(self):
        """
        启动模式分析
        """
        try:
            # 使用统一定时器服务启动分析任务
            self.timer_service.add_task(
                task_id=self.analysis_task_id,
                service_name="IntelligentDetection",
                function=self._analyze_patterns,
                interval=30,  # 30秒
                task_type="interval",
                metadata={"service": "intelligent_detection"}
            )
            
            # 备用：启动QTimer（以防统一定时器服务异常）
            if not self.analysis_timer.isActive():
                # 每30秒分析一次模式
                self.analysis_timer.start(30000)
                self.logger.info("模式分析定时器已启动")
            else:
                self.logger.info("模式分析定时器已在运行")
        except Exception as e:
            self.logger.error(f"模式分析启动失败: {e}")
    
    def _analyze_patterns(self):
        """
        分析检测模式
        """
        try:
            current_time = time.time()
            
            # 清理过期模式
            self._cleanup_expired_patterns(current_time)
            
            # 发现新模式
            self._discover_new_patterns()
            
            # 更新自适应间隔
            self._update_adaptive_intervals()
            
            # 定期保存数据
            if len(self.detection_history) % 50 == 0:
                self._save_historical_data()
            
        except Exception as e:
            self.logger.error(f"模式分析失败: {e}")
    
    def _cleanup_expired_patterns(self, current_time: float):
        """
        清理过期模式
        
        Args:
            current_time: 当前时间戳
        """
        try:
            expired_keys = []
            decay_time = self.config["pattern_decay_time"]
            
            for key, pattern in self.region_patterns.items():
                if current_time - pattern.last_seen > decay_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.region_patterns[key]
            
            if expired_keys:
                self.logger.debug(f"清理了{len(expired_keys)}个过期模式")
        except Exception as e:
            self.logger.error(f"过期模式清理失败: {e}")
    
    def _discover_new_patterns(self):
        """
        发现新的检测模式
        """
        try:
            if len(self.detection_history) < self.config["min_pattern_frequency"]:
                return
            
            # 按目标文字分组分析
            text_groups = defaultdict(list)
            for record in self.detection_history:
                if record.success and record.found_region:
                    text_groups[record.target_text].append(record)
            
            for target_text, records in text_groups.items():
                if len(records) >= self.config["min_pattern_frequency"]:
                    self._analyze_text_patterns(target_text, records)
            
        except Exception as e:
            self.logger.error(f"新模式发现失败: {e}")
    
    def _analyze_text_patterns(self, target_text: str, records: List[DetectionRecord]):
        """
        分析特定文字的模式
        
        Args:
            target_text: 目标文字
            records: 检测记录列表
        """
        try:
            # 聚类相似区域
            region_clusters = self._cluster_regions([r.found_region for r in records])
            
            for cluster_regions in region_clusters:
                if len(cluster_regions) >= self.config["min_pattern_frequency"]:
                    # 计算聚类中心
                    center_region = self._calculate_region_center(cluster_regions)
                    
                    # 生成模式键
                    pattern_key = f"{target_text}_{center_region[0]}_{center_region[1]}"
                    
                    # 计算模式统计信息
                    cluster_records = [r for r in records if r.found_region in cluster_regions]
                    
                    success_rate = len([r for r in cluster_records if r.success]) / len(cluster_records)
                    avg_confidence = statistics.mean([r.confidence for r in cluster_records])
                    avg_processing_time = statistics.mean([r.processing_time for r in cluster_records])
                    
                    # 更新或创建模式
                    if pattern_key in self.region_patterns:
                        pattern = self.region_patterns[pattern_key]
                        pattern.frequency += len(cluster_records)
                        pattern.success_rate = (pattern.success_rate + success_rate) / 2
                        pattern.avg_confidence = (pattern.avg_confidence + avg_confidence) / 2
                        pattern.last_seen = time.time()
                        if target_text not in pattern.target_texts:
                            pattern.target_texts.append(target_text)
                    else:
                        # 创建新模式
                        new_pattern = RegionPattern(
                            region=center_region,
                            frequency=len(cluster_records),
                            success_rate=success_rate,
                            avg_confidence=avg_confidence,
                            last_seen=time.time(),
                            target_texts=[target_text],
                            avg_processing_time=avg_processing_time
                        )
                        
                        self.region_patterns[pattern_key] = new_pattern
                        
                        # 发送新模式发现信号
                        self.pattern_discovered.emit({
                            "pattern_key": pattern_key,
                            "target_text": target_text,
                            "region": center_region,
                            "frequency": len(cluster_records),
                            "success_rate": success_rate
                        })
                        
                        self.logger.info(f"发现新模式: {pattern_key}, 成功率: {success_rate:.2f}")
            
        except Exception as e:
            self.logger.error(f"文字模式分析失败: {e}")
    
    def _cluster_regions(self, regions: List[Tuple[int, int, int, int]]) -> List[List[Tuple[int, int, int, int]]]:
        """
        聚类相似区域
        
        Args:
            regions: 区域列表
            
        Returns:
            List: 聚类结果
        """
        try:
            if not regions:
                return []
            
            clusters = []
            threshold = self.config["pattern_similarity_threshold"]
            
            for region in regions:
                added_to_cluster = False
                
                for cluster in clusters:
                    # 计算与聚类中心的相似度
                    center = self._calculate_region_center(cluster)
                    similarity = self._calculate_region_similarity(region, center)
                    
                    if similarity >= threshold:
                        cluster.append(region)
                        added_to_cluster = True
                        break
                
                if not added_to_cluster:
                    clusters.append([region])
            
            return clusters
        except Exception as e:
            self.logger.error(f"区域聚类失败: {e}")
            return []
    
    def _calculate_region_center(self, regions: List[Tuple[int, int, int, int]]) -> Tuple[int, int, int, int]:
        """
        计算区域聚类中心
        
        Args:
            regions: 区域列表
            
        Returns:
            Tuple: 中心区域坐标
        """
        try:
            if not regions:
                return (0, 0, 0, 0)
            
            avg_x = int(statistics.mean([r[0] for r in regions]))
            avg_y = int(statistics.mean([r[1] for r in regions]))
            avg_w = int(statistics.mean([r[2] for r in regions]))
            avg_h = int(statistics.mean([r[3] for r in regions]))
            
            return (avg_x, avg_y, avg_w, avg_h)
        except Exception as e:
            self.logger.error(f"区域中心计算失败: {e}")
            return (0, 0, 0, 0)
    
    def _calculate_region_similarity(self, region1: Tuple[int, int, int, int], 
                                   region2: Tuple[int, int, int, int]) -> float:
        """
        计算两个区域的相似度
        
        Args:
            region1: 区域1
            region2: 区域2
            
        Returns:
            float: 相似度（0-1）
        """
        try:
            x1, y1, w1, h1 = region1
            x2, y2, w2, h2 = region2
            
            # 计算重叠区域
            overlap_x = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            overlap_y = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
            overlap_area = overlap_x * overlap_y
            
            # 计算并集面积
            area1 = w1 * h1
            area2 = w2 * h2
            union_area = area1 + area2 - overlap_area
            
            # 计算IoU（交并比）
            if union_area == 0:
                return 0.0
            
            return overlap_area / union_area
        except Exception as e:
            self.logger.error(f"区域相似度计算失败: {e}")
            return 0.0
    
    def _update_adaptive_intervals(self):
        """
        更新自适应检测间隔
        """
        try:
            if not self.config["adaptive_interval_enabled"]:
                return
            
            for target_text, stats in self.text_statistics.items():
                if stats["total_detections"] > 0:
                    success_rate = stats["successful_detections"] / stats["total_detections"]
                    avg_time = stats["avg_processing_time"]
                    
                    # 根据成功率和处理时间调整间隔
                    base_interval = self.config["base_detection_interval"]
                    
                    if success_rate > 0.8:
                        # 高成功率，可以增加间隔
                        new_interval = min(
                            base_interval * (1 + success_rate),
                            self.config["max_detection_interval"]
                        )
                    else:
                        # 低成功率，减少间隔
                        new_interval = max(
                            base_interval * success_rate,
                            self.config["min_detection_interval"]
                        )
                    
                    # 考虑处理时间
                    if avg_time > 5.0:  # 处理时间超过5秒
                        new_interval *= 1.5
                    
                    old_interval = self.adaptive_intervals[target_text]
                    self.adaptive_intervals[target_text] = int(new_interval)
                    
                    if abs(new_interval - old_interval) > 100:  # 变化超过100ms
                        self.strategy_updated.emit({
                            "target_text": target_text,
                            "old_interval": old_interval,
                            "new_interval": new_interval,
                            "success_rate": success_rate
                        })
            
        except Exception as e:
            self.logger.error(f"自适应间隔更新失败: {e}")
    
    def record_detection(self, target_text: str, found_region: Optional[Tuple[int, int, int, int]],
                        confidence: float, processing_time: float, 
                        screen_resolution: Tuple[int, int], success: bool,
                        metadata: Dict[str, Any] = None):
        """
        记录检测结果
        
        Args:
            target_text: 目标文字
            found_region: 找到的区域
            confidence: 置信度
            processing_time: 处理时间
            screen_resolution: 屏幕分辨率
            success: 是否成功
            metadata: 元数据
        """
        try:
            # 创建检测记录
            record = DetectionRecord(
                timestamp=time.time(),
                target_text=target_text,
                found_region=found_region,
                confidence=confidence,
                processing_time=processing_time,
                screen_resolution=screen_resolution,
                success=success,
                metadata=metadata or {}
            )
            
            # 添加到历史记录
            self.detection_history.append(record)
            
            # 更新文字统计
            stats = self.text_statistics[target_text]
            stats["total_detections"] += 1
            if success:
                stats["successful_detections"] += 1
            
            # 更新平均处理时间
            total = stats["total_detections"]
            if total == 1:
                stats["avg_processing_time"] = processing_time
            else:
                current_avg = stats["avg_processing_time"]
                stats["avg_processing_time"] = (
                    (current_avg * (total - 1) + processing_time) / total
                )
            
            # 更新热力图
            if found_region:
                region_key = f"{found_region[0]//50}_{found_region[1]//50}"  # 50像素网格
                self.heatmap_data[region_key] += 1
            
            # 记录检测间隔
            current_time = time.time()
            if stats["last_detection_time"] > 0:
                interval = current_time - stats["last_detection_time"]
                stats["detection_intervals"].append(interval)
            stats["last_detection_time"] = current_time
            
            self.logger.debug(f"检测记录已保存: {target_text}, 成功: {success}")
            
        except Exception as e:
            self.logger.error(f"检测记录保存失败: {e}")
    
    def predict_best_regions(self, target_text: str, 
                           screen_resolution: Tuple[int, int]) -> List[Dict[str, Any]]:
        """
        预测最佳检测区域
        
        Args:
            target_text: 目标文字
            screen_resolution: 屏幕分辨率
            
        Returns:
            List: 预测的区域列表，按优先级排序
        """
        try:
            start_time = time.time()
            
            # 检查预测缓存
            cache_key = f"{target_text}_{screen_resolution[0]}_{screen_resolution[1]}"
            if cache_key in self.prediction_cache:
                cache_entry = self.prediction_cache[cache_key]
                if time.time() - cache_entry["timestamp"] < 60:  # 缓存1分钟
                    return cache_entry["predictions"]
            
            predictions = []
            
            # 基于历史模式预测
            for pattern_key, pattern in self.region_patterns.items():
                if target_text in pattern.target_texts:
                    score = self._calculate_pattern_score(pattern, target_text)
                    
                    if score >= self.config["prediction_confidence_threshold"]:
                        predictions.append({
                            "region": pattern.region,
                            "confidence": score,
                            "success_rate": pattern.success_rate,
                            "frequency": pattern.frequency,
                            "avg_processing_time": pattern.avg_processing_time,
                            "source": "pattern_matching"
                        })
            
            # 基于热力图预测
            heatmap_predictions = self._predict_from_heatmap(target_text, screen_resolution)
            predictions.extend(heatmap_predictions)
            
            # 基于文字统计预测
            stats_predictions = self._predict_from_statistics(target_text, screen_resolution)
            predictions.extend(stats_predictions)
            
            # 按置信度排序
            predictions.sort(key=lambda x: x["confidence"], reverse=True)
            
            # 去重（合并相似区域）
            predictions = self._merge_similar_predictions(predictions)
            
            # 限制返回数量
            predictions = predictions[:5]
            
            # 缓存预测结果
            self.prediction_cache[cache_key] = {
                "predictions": predictions,
                "timestamp": time.time()
            }
            
            # 更新性能指标
            prediction_time = time.time() - start_time
            self.performance_metrics["total_predictions"] += 1
            
            current_avg = self.performance_metrics["avg_prediction_time"]
            total = self.performance_metrics["total_predictions"]
            self.performance_metrics["avg_prediction_time"] = (
                (current_avg * (total - 1) + prediction_time) / total
            )
            
            # 发送预测信号
            self.prediction_made.emit({
                "target_text": target_text,
                "predictions_count": len(predictions),
                "prediction_time": prediction_time
            })
            
            return predictions
            
        except Exception as e:
            self.logger.error(f"区域预测失败: {e}")
            return []
    
    def _calculate_pattern_score(self, pattern: RegionPattern, target_text: str) -> float:
        """
        计算模式得分
        
        Args:
            pattern: 区域模式
            target_text: 目标文字
            
        Returns:
            float: 模式得分
        """
        try:
            # 基础得分：成功率
            base_score = pattern.success_rate
            
            # 频率加权
            frequency_weight = min(1.0, pattern.frequency / 10.0)
            
            # 时间衰减
            time_decay = max(0.1, 1.0 - (time.time() - pattern.last_seen) / self.config["pattern_decay_time"])
            
            # 置信度加权
            confidence_weight = pattern.avg_confidence
            
            # 综合得分
            score = base_score * frequency_weight * time_decay * confidence_weight
            
            return min(1.0, score)
        except Exception as e:
            self.logger.error(f"模式得分计算失败: {e}")
            return 0.0
    
    def _predict_from_heatmap(self, target_text: str, 
                            screen_resolution: Tuple[int, int]) -> List[Dict[str, Any]]:
        """
        基于热力图预测区域
        
        Args:
            target_text: 目标文字
            screen_resolution: 屏幕分辨率
            
        Returns:
            List: 预测区域列表
        """
        try:
            predictions = []
            
            # 找到热点区域
            sorted_heatmap = sorted(self.heatmap_data.items(), key=lambda x: x[1], reverse=True)
            
            for region_key, frequency in sorted_heatmap[:3]:  # 取前3个热点
                try:
                    grid_x, grid_y = map(int, region_key.split('_'))
                    x = grid_x * 50
                    y = grid_y * 50
                    
                    # 估算区域大小
                    w = min(200, screen_resolution[0] - x)
                    h = min(100, screen_resolution[1] - y)
                    
                    confidence = min(0.8, frequency / max(self.heatmap_data.values()))
                    
                    predictions.append({
                        "region": (x, y, w, h),
                        "confidence": confidence,
                        "success_rate": 0.0,  # 未知
                        "frequency": frequency,
                        "avg_processing_time": 0.0,
                        "source": "heatmap"
                    })
                except ValueError:
                    continue
            
            return predictions
        except Exception as e:
            self.logger.error(f"热力图预测失败: {e}")
            return []
    
    def _predict_from_statistics(self, target_text: str, 
                               screen_resolution: Tuple[int, int]) -> List[Dict[str, Any]]:
        """
        基于统计数据预测区域
        
        Args:
            target_text: 目标文字
            screen_resolution: 屏幕分辨率
            
        Returns:
            List: 预测区域列表
        """
        try:
            predictions = []
            
            stats = self.text_statistics.get(target_text)
            if not stats or stats["total_detections"] == 0:
                return predictions
            
            success_rate = stats["successful_detections"] / stats["total_detections"]
            
            if success_rate > 0.5:
                # 基于成功率预测常见区域
                common_regions = [
                    (0, 0, screen_resolution[0]//2, screen_resolution[1]//2),  # 左上
                    (screen_resolution[0]//2, 0, screen_resolution[0]//2, screen_resolution[1]//2),  # 右上
                    (0, screen_resolution[1]//2, screen_resolution[0]//2, screen_resolution[1]//2),  # 左下
                    (screen_resolution[0]//2, screen_resolution[1]//2, screen_resolution[0]//2, screen_resolution[1]//2)  # 右下
                ]
                
                for i, region in enumerate(common_regions):
                    confidence = success_rate * (0.8 - i * 0.1)  # 递减置信度
                    
                    predictions.append({
                        "region": region,
                        "confidence": max(0.1, confidence),
                        "success_rate": success_rate,
                        "frequency": stats["total_detections"],
                        "avg_processing_time": stats["avg_processing_time"],
                        "source": "statistics"
                    })
            
            return predictions
        except Exception as e:
            self.logger.error(f"统计预测失败: {e}")
            return []
    
    def _merge_similar_predictions(self, predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并相似的预测区域
        
        Args:
            predictions: 预测列表
            
        Returns:
            List: 合并后的预测列表
        """
        try:
            if not predictions:
                return predictions
            
            merged = []
            threshold = 0.5  # 相似度阈值
            
            for pred in predictions:
                merged_with_existing = False
                
                for merged_pred in merged:
                    similarity = self._calculate_region_similarity(
                        pred["region"], merged_pred["region"]
                    )
                    
                    if similarity >= threshold:
                        # 合并预测，取较高置信度
                        if pred["confidence"] > merged_pred["confidence"]:
                            merged_pred.update(pred)
                        merged_with_existing = True
                        break
                
                if not merged_with_existing:
                    merged.append(pred)
            
            return merged
        except Exception as e:
            self.logger.error(f"预测合并失败: {e}")
            return predictions
    
    def get_adaptive_interval(self, target_text: str) -> int:
        """
        获取自适应检测间隔
        
        Args:
            target_text: 目标文字
            
        Returns:
            int: 检测间隔（毫秒）
        """
        return self.adaptive_intervals.get(target_text, self.config["base_detection_interval"])
    
    def validate_prediction(self, target_text: str, predicted_region: Tuple[int, int, int, int],
                          actual_region: Optional[Tuple[int, int, int, int]], success: bool):
        """
        验证预测结果
        
        Args:
            target_text: 目标文字
            predicted_region: 预测区域
            actual_region: 实际找到的区域
            success: 是否成功
        """
        try:
            self.performance_metrics["total_predictions"] += 1
            
            if success and actual_region:
                # 计算预测准确性
                similarity = self._calculate_region_similarity(predicted_region, actual_region)
                if similarity >= 0.5:  # 50%重叠认为预测正确
                    self.performance_metrics["correct_predictions"] += 1
            
            # 更新预测准确率
            total = self.performance_metrics["total_predictions"]
            correct = self.performance_metrics["correct_predictions"]
            self.performance_metrics["prediction_accuracy"] = correct / total if total > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"预测验证失败: {e}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        获取性能报告
        
        Returns:
            Dict: 性能报告
        """
        try:
            return {
                "performance_metrics": self.performance_metrics.copy(),
                "pattern_count": len(self.region_patterns),
                "detection_history_size": len(self.detection_history),
                "text_statistics_count": len(self.text_statistics),
                "heatmap_hotspots": len(self.heatmap_data),
                "adaptive_intervals": dict(self.adaptive_intervals),
                "config": self.config.copy()
            }
        except Exception as e:
            self.logger.error(f"性能报告生成失败: {e}")
            return {}
    
    def update_config(self, config: Dict[str, Any]):
        """
        更新服务配置
        
        Args:
            config: 新的配置参数
        """
        try:
            self.config.update(config)
            
            # 更新历史记录大小限制
            if "max_history_size" in config:
                new_maxlen = config["max_history_size"]
                if new_maxlen != self.detection_history.maxlen:
                    # 重新创建deque
                    old_data = list(self.detection_history)
                    self.detection_history = deque(old_data[-new_maxlen:], maxlen=new_maxlen)
            
            self.logger.info(f"智能检测服务配置已更新: {config}")
        except Exception as e:
            self.logger.error(f"配置更新失败: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            Dict: 当前配置
        """
        return self.config.copy()
    
    def cleanup(self):
        """
        清理服务资源
        """
        try:
            # 使用统一定时器服务停止分析任务
            if hasattr(self, 'timer_service'):
                self.timer_service.remove_task(self.analysis_task_id)
            
            # 备用：停止QTimer
            if self.analysis_timer.isActive():
                self.analysis_timer.stop()
            
            # 保存历史数据
            self._save_historical_data()
            
            self.logger.info("智能检测服务清理完成")
        except Exception as e:
            self.logger.error(f"智能检测服务清理失败: {e}")