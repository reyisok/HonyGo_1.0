#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能告警服务
实现动态阈值调整、多级告警机制和告警聚合去重

@author: Mr.Rey Copyright © 2025
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import (
    Callable,
    Dict,
    List,
    Optional,
    Set
)
import threading
import time

from dataclasses import dataclass
from enum import Enum

from src.core.services.unified_timer_service import get_timer_service
from src.ui.services.logging_service import get_logger
















class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class SmartAlert:
    """智能告警信息"""
    id: str
    pid: int
    alert_type: str
    level: AlertLevel
    current_value: float
    threshold: float
    dynamic_threshold: float  # 动态阈值
    message: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    count: int = 1  # 重复次数
    first_occurrence: datetime = None
    last_occurrence: datetime = None
    acknowledged_by: str = None
    acknowledged_at: datetime = None
    resolved_at: datetime = None
    
    def __post_init__(self):
        if self.first_occurrence is None:
            self.first_occurrence = self.timestamp
        if self.last_occurrence is None:
            self.last_occurrence = self.timestamp


@dataclass
class ThresholdConfig:
    """动态阈值配置"""
    base_threshold: float  # 基础阈值
    min_threshold: float   # 最小阈值
    max_threshold: float   # 最大阈值
    adjustment_factor: float = 0.1  # 调整因子
    learning_window: int = 100  # 学习窗口大小
    stability_factor: float = 0.8  # 稳定性因子


class IntelligentAlertService:
    """智能告警服务"""
    
    def __init__(self):
        self.logger = get_logger('IntelligentAlert')
        self.timer_service = None
        
        # 告警存储
        self.active_alerts: Dict[str, SmartAlert] = {}  # 活跃告警
        self.alert_history: List[SmartAlert] = []  # 告警历史
        self.suppressed_alerts: Set[str] = set()  # 被抑制的告警类型
        
        # 动态阈值管理
        self.dynamic_thresholds: Dict[str, Dict[int, float]] = defaultdict(dict)  # alert_type -> pid -> threshold
        self.threshold_configs: Dict[str, ThresholdConfig] = {}
        self.metric_history: Dict[str, Dict[int, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=100)))
        
        # 告警聚合配置
        self.aggregation_window = 300  # 5分钟聚合窗口
        self.max_alerts_per_type = 5  # 每种类型最大告警数
        self.suppression_duration = 3600  # 抑制持续时间（秒）
        
        # 回调函数
        self.alert_callbacks: List[Callable[[SmartAlert], None]] = []
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 初始化默认阈值配置
        self._initialize_threshold_configs()
        
        self.logger.info("智能告警服务初始化完成")

    def initialize(self) -> bool:
        """初始化服务"""
        try:
            self.logger.info("智能告警服务正在初始化...")
            # 这里可以添加初始化逻辑，如加载配置等
            return True
        except Exception as e:
            self.logger.error(f"智能告警服务初始化失败: {e}")
            return False
    
    def start(self) -> bool:
        """启动服务"""
        try:
            self.logger.info("智能告警服务正在启动...")
            return True
        except Exception as e:
            self.logger.error(f"智能告警服务启动失败: {e}")
            return False
    
    def stop(self) -> bool:
        """停止服务"""
        try:
            self.logger.info("智能告警服务正在停止...")
            return True
        except Exception as e:
            self.logger.error(f"智能告警服务停止失败: {e}")
            return False
    
    def cleanup(self) -> bool:
        """清理资源"""
        try:
            self.logger.info("智能告警服务正在清理资源...")
            return True
        except Exception as e:
            self.logger.error(f"智能告警服务清理失败: {e}")
            return False
    
    def is_healthy(self) -> bool:
        """健康检查"""
        return True
    
    def _initialize_threshold_configs(self):
        """初始化默认阈值配置"""
        self.threshold_configs = {
            'high_cpu': ThresholdConfig(
                base_threshold=80.0,
                min_threshold=60.0,
                max_threshold=95.0,
                adjustment_factor=0.1,
                learning_window=50
            ),
            'high_memory': ThresholdConfig(
                base_threshold=80.0,
                min_threshold=60.0,
                max_threshold=95.0,
                adjustment_factor=0.1,
                learning_window=50
            ),
            'too_many_threads': ThresholdConfig(
                base_threshold=100.0,
                min_threshold=50.0,
                max_threshold=200.0,
                adjustment_factor=0.05,
                learning_window=30
            ),
            'too_many_handles': ThresholdConfig(
                base_threshold=1000.0,
                min_threshold=500.0,
                max_threshold=2000.0,
                adjustment_factor=0.05,
                learning_window=30
            ),
            'too_many_connections': ThresholdConfig(
                base_threshold=500.0,
                min_threshold=200.0,
                max_threshold=1000.0,
                adjustment_factor=0.1,
                learning_window=40
            ),
            'high_gpu_usage': ThresholdConfig(
                base_threshold=90.0,
                min_threshold=70.0,
                max_threshold=98.0,
                adjustment_factor=0.05,
                learning_window=30
            ),
            'slow_response': ThresholdConfig(
                base_threshold=5000.0,
                min_threshold=2000.0,
                max_threshold=10000.0,
                adjustment_factor=0.2,
                learning_window=20
            )
        }
    
    def initialize(self):
        """初始化服务"""
        try:
            self.timer_service = get_timer_service()
            if self.timer_service:
                # 定期清理过期告警
                self.timer_service.add_job(
                    self._cleanup_expired_alerts,
                    'interval',
                    seconds=300,  # 每5分钟清理一次
                    id='cleanup_expired_alerts'
                )
                
                # 定期调整动态阈值
                self.timer_service.add_job(
                    self._adjust_dynamic_thresholds,
                    'interval',
                    seconds=600,  # 每10分钟调整一次
                    id='adjust_dynamic_thresholds'
                )
                
                self.logger.info("智能告警服务定时任务已启动")
            
        except Exception as e:
            self.logger.error(f"智能告警服务初始化失败: {e}")
    
    def process_alert(self, pid: int, alert_type: str, current_value: float, 
                     base_threshold: float, message: str) -> Optional[SmartAlert]:
        """处理告警"""
        try:
            with self._lock:
                # 更新指标历史
                self._update_metric_history(alert_type, pid, current_value)
                
                # 获取动态阈值
                dynamic_threshold = self._get_dynamic_threshold(alert_type, pid, base_threshold)
                
                # 检查是否需要触发告警
                if current_value <= dynamic_threshold:
                    return None
                
                # 生成告警ID
                alert_id = f"{alert_type}_{pid}_{int(time.time())}"
                
                # 检查是否为重复告警
                existing_alert = self._find_similar_alert(pid, alert_type)
                if existing_alert:
                    return self._handle_duplicate_alert(existing_alert, current_value, dynamic_threshold)
                
                # 检查告警抑制
                if self._is_alert_suppressed(alert_type, pid):
                    self.logger.debug(f"告警被抑制: {alert_type} for PID {pid}")
                    return None
                
                # 确定告警级别
                level = self._determine_alert_level(alert_type, current_value, dynamic_threshold)
                
                # 创建新告警
                alert = SmartAlert(
                    id=alert_id,
                    pid=pid,
                    alert_type=alert_type,
                    level=level,
                    current_value=current_value,
                    threshold=base_threshold,
                    dynamic_threshold=dynamic_threshold,
                    message=message,
                    timestamp=datetime.now()
                )
                
                # 存储告警
                self.active_alerts[alert_id] = alert
                self.alert_history.append(alert)
                
                # 检查是否需要聚合抑制
                self._check_aggregation_suppression(alert_type)
                
                # 触发回调
                self._trigger_callbacks(alert)
                
                self.logger.info(f"新告警: {alert.message} (动态阈值: {dynamic_threshold:.2f})")
                return alert
                
        except Exception as e:
            self.logger.error(f"处理告警失败: {e}")
            return None
    
    def _update_metric_history(self, alert_type: str, pid: int, value: float):
        """更新指标历史"""
        self.metric_history[alert_type][pid].append({
            'value': value,
            'timestamp': datetime.now()
        })
    
    def _get_dynamic_threshold(self, alert_type: str, pid: int, base_threshold: float) -> float:
        """获取动态阈值"""
        # 如果没有历史数据，使用基础阈值
        if alert_type not in self.metric_history or pid not in self.metric_history[alert_type]:
            return base_threshold
        
        history = self.metric_history[alert_type][pid]
        if len(history) < 10:  # 数据不足，使用基础阈值
            return base_threshold
        
        # 获取阈值配置
        config = self.threshold_configs.get(alert_type)
        if not config:
            return base_threshold
        
        # 计算历史平均值和标准差
        values = [item['value'] for item in history]
        avg_value = sum(values) / len(values)
        variance = sum((x - avg_value) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        # 动态调整阈值
        # 如果历史值普遍较低，降低阈值；如果普遍较高，提高阈值
        adjustment = (avg_value - config.base_threshold) * config.adjustment_factor
        
        # 考虑稳定性因子
        if std_dev > avg_value * 0.3:  # 数据波动较大
            adjustment *= config.stability_factor
        
        new_threshold = config.base_threshold + adjustment
        
        # 限制在最小最大阈值范围内
        new_threshold = max(config.min_threshold, min(config.max_threshold, new_threshold))
        
        # 更新动态阈值缓存
        self.dynamic_thresholds[alert_type][pid] = new_threshold
        
        return new_threshold
    
    def _find_similar_alert(self, pid: int, alert_type: str) -> Optional[SmartAlert]:
        """查找相似的活跃告警"""
        for alert in self.active_alerts.values():
            if (alert.pid == pid and 
                alert.alert_type == alert_type and 
                alert.status == AlertStatus.ACTIVE):
                return alert
        
        return None


# 全局智能告警服务实例
_intelligent_alert_service = None


def get_intelligent_alert_service() -> IntelligentAlertService:
    """获取智能告警服务实例"""
    global _intelligent_alert_service
    if _intelligent_alert_service is None:
        _intelligent_alert_service = IntelligentAlertService()
    return _intelligent_alert_service


def initialize_intelligent_alert_service() -> IntelligentAlertService:
    """初始化智能告警服务"""
    global _intelligent_alert_service
    _intelligent_alert_service = IntelligentAlertService()
    return _intelligent_alert_service
    
    def _handle_duplicate_alert(self, existing_alert: SmartAlert, 
                               current_value: float, dynamic_threshold: float) -> SmartAlert:
        """处理重复告警"""
        existing_alert.count += 1
        existing_alert.current_value = current_value
        existing_alert.dynamic_threshold = dynamic_threshold
        existing_alert.last_occurrence = datetime.now()
        
        # 更新告警级别
        new_level = self._determine_alert_level(existing_alert.alert_type, current_value, dynamic_threshold)
        if new_level.value != existing_alert.level.value:
            existing_alert.level = new_level
            self.logger.info(f"告警级别变更: {existing_alert.id} -> {new_level.value}")
        
        return existing_alert
    
    def _is_alert_suppressed(self, alert_type: str, pid: int) -> bool:
        """检查告警是否被抑制"""
        suppression_key = f"{alert_type}_{pid}"
        return suppression_key in self.suppressed_alerts
    
    def _determine_alert_level(self, alert_type: str, current_value: float, threshold: float) -> AlertLevel:
        """确定告警级别"""
        ratio = current_value / threshold
        
        if ratio >= 2.0:  # 超过阈值100%
            return AlertLevel.CRITICAL
        elif ratio >= 1.5:  # 超过阈值50%
            return AlertLevel.ERROR
        elif ratio >= 1.2:  # 超过阈值20%
            return AlertLevel.WARNING
        else:
            return AlertLevel.INFO
    
    def _check_aggregation_suppression(self, alert_type: str):
        """检查聚合抑制"""
        # 统计最近时间窗口内同类型告警数量
        now = datetime.now()
        window_start = now - timedelta(seconds=self.aggregation_window)
        
        recent_alerts = [
            alert for alert in self.active_alerts.values()
            if (alert.alert_type == alert_type and 
                alert.timestamp >= window_start and
                alert.status == AlertStatus.ACTIVE)
        ]
        
        if len(recent_alerts) >= self.max_alerts_per_type:
            # 抑制后续同类型告警
            self.suppressed_alerts.add(alert_type)
            self.logger.warning(f"告警类型 {alert_type} 触发聚合抑制，抑制时长: {self.suppression_duration}秒")
            
            # 设置定时解除抑制
            if self.timer_service:
                self.timer_service.add_job(
                    lambda: self._remove_suppression(alert_type),
                    'date',
                    run_date=now + timedelta(seconds=self.suppression_duration),
                    id=f'remove_suppression_{alert_type}_{int(time.time())}'
                )
    
    def _remove_suppression(self, alert_type: str):
        """移除告警抑制"""
        if alert_type in self.suppressed_alerts:
            self.suppressed_alerts.remove(alert_type)
            self.logger.info(f"告警类型 {alert_type} 抑制已解除")
    
    def _trigger_callbacks(self, alert: SmartAlert):
        """触发告警回调"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"告警回调执行失败: {e}")
    
    def _cleanup_expired_alerts(self):
        """清理过期告警"""
        try:
            now = datetime.now()
            expired_threshold = now - timedelta(hours=24)  # 24小时后清理
            
            # 清理活跃告警中的过期项
            expired_ids = [
                alert_id for alert_id, alert in self.active_alerts.items()
                if alert.timestamp < expired_threshold and alert.status != AlertStatus.ACTIVE
            ]
            
            for alert_id in expired_ids:
                del self.active_alerts[alert_id]
            
            # 清理历史告警（保留最近7天）
            history_threshold = now - timedelta(days=7)
            self.alert_history = [
                alert for alert in self.alert_history
                if alert.timestamp >= history_threshold
            ]
            
            if expired_ids:
                self.logger.info(f"清理了 {len(expired_ids)} 个过期告警")
                
        except Exception as e:
            self.logger.error(f"清理过期告警失败: {e}")
    
    def _adjust_dynamic_thresholds(self):
        """调整动态阈值"""
        try:
            adjusted_count = 0
            
            for alert_type, pid_thresholds in self.dynamic_thresholds.items():
                config = self.threshold_configs.get(alert_type)
                if not config:
                    continue
                
                for pid in list(pid_thresholds.keys()):
                    # 重新计算动态阈值
                    old_threshold = pid_thresholds[pid]
                    new_threshold = self._get_dynamic_threshold(alert_type, pid, config.base_threshold)
                    
                    if abs(new_threshold - old_threshold) > config.base_threshold * 0.05:  # 变化超过5%
                        adjusted_count += 1
                        self.logger.debug(f"调整动态阈值: {alert_type}[{pid}] {old_threshold:.2f} -> {new_threshold:.2f}")
            
            if adjusted_count > 0:
                self.logger.info(f"调整了 {adjusted_count} 个动态阈值")
                
        except Exception as e:
            self.logger.error(f"调整动态阈值失败: {e}")
    
    def add_alert_callback(self, callback: Callable[[SmartAlert], None]):
        """添加告警回调"""
        self.alert_callbacks.append(callback)
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """确认告警"""
        try:
            with self._lock:
                if alert_id in self.active_alerts:
                    alert = self.active_alerts[alert_id]
                    alert.status = AlertStatus.ACKNOWLEDGED
                    alert.acknowledged_by = acknowledged_by
                    alert.acknowledged_at = datetime.now()
                    
                    self.logger.info(f"告警已确认: {alert_id} by {acknowledged_by}")
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"确认告警失败: {e}")
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        try:
            with self._lock:
                if alert_id in self.active_alerts:
                    alert = self.active_alerts[alert_id]
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.now()
                    
                    self.logger.info(f"告警已解决: {alert_id}")
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"解决告警失败: {e}")
            return False
    
    def get_active_alerts(self, alert_type: str = None, level: AlertLevel = None) -> List[SmartAlert]:
        """获取活跃告警"""
        alerts = list(self.active_alerts.values())
        
        if alert_type:
            alerts = [alert for alert in alerts if alert.alert_type == alert_type]
        
        if level:
            alerts = [alert for alert in alerts if alert.level == level]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def get_alert_statistics(self) -> dict:
        """获取告警统计信息"""
        try:
            now = datetime.now()
            last_24h = now - timedelta(hours=24)
            
            # 统计最近24小时的告警
            recent_alerts = [
                alert for alert in self.alert_history
                if alert.timestamp >= last_24h
            ]
            
            stats = {
                'total_active': len(self.active_alerts),
                'total_recent': len(recent_alerts),
                'by_level': defaultdict(int),
                'by_type': defaultdict(int),
                'suppressed_types': len(self.suppressed_alerts),
                'dynamic_thresholds_count': sum(len(pids) for pids in self.dynamic_thresholds.values())
            }
            
            # 按级别统计
            for alert in self.active_alerts.values():
                stats['by_level'][alert.level.value] += 1
            
            # 按类型统计
            for alert in recent_alerts:
                stats['by_type'][alert.alert_type] += 1
            
            return dict(stats)
            
        except Exception as e:
            self.logger.error(f"获取告警统计失败: {e}")
            return {}
    
    def cleanup(self):
        """清理资源"""
        try:
            with self._lock:
                self.active_alerts.clear()
                self.alert_history.clear()
                self.suppressed_alerts.clear()
                self.dynamic_thresholds.clear()
                self.metric_history.clear()
                self.alert_callbacks.clear()
            
            self.logger.info("智能告警服务资源已清理")
            
        except Exception as e:
            self.logger.error(f"清理智能告警服务资源失败: {e}")


# 全局服务实例
_intelligent_alert_service = None


def get_intelligent_alert_service() -> IntelligentAlertService:
    """获取智能告警服务实例"""
    global _intelligent_alert_service
    if _intelligent_alert_service is None:
        _intelligent_alert_service = IntelligentAlertService()
    return _intelligent_alert_service


def initialize_intelligent_alert_service() -> IntelligentAlertService:
    """初始化智能告警服务"""
    service = get_intelligent_alert_service()
    service.initialize()
    return service