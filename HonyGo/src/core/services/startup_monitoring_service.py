#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动过程监控和日志记录服务

@author: Mr.Rey Copyright © 2025

功能:
1. 启动过程各阶段监控
2. 启动性能分析和记录
3. 启动错误检测和诊断
4. 启动依赖关系验证
5. 启动超时检测和处理
"""

from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional
)
import json
import os
import threading
import time

from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
import psutil

from src.ui.services.logging_service import get_logger
















class StartupPhase(Enum):
    """启动阶段枚举"""
    INITIALIZATION = "initialization"
    CONFIG_LOADING = "config_loading"
    SERVICE_REGISTRATION = "service_registration"
    SERVICE_INITIALIZATION = "service_initialization"
    SERVICE_STARTUP = "service_startup"
    UI_INITIALIZATION = "ui_initialization"
    FINAL_VALIDATION = "final_validation"
    COMPLETED = "completed"
    FAILED = "failed"


class StartupStatus(Enum):
    """启动状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class StartupPhaseInfo:
    """启动阶段信息"""
    phase: StartupPhase
    status: StartupStatus = StartupStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    error: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[StartupPhase] = field(default_factory=list)
    timeout_seconds: float = 30.0
    
    @property
    def is_completed(self) -> bool:
        return self.status == StartupStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        return self.status in [StartupStatus.FAILED, StartupStatus.TIMEOUT]
    
    @property
    def is_running(self) -> bool:
        return self.status == StartupStatus.IN_PROGRESS


@dataclass
class StartupMetrics:
    """启动指标"""
    total_duration: float = 0.0
    phase_count: int = 0
    completed_phases: int = 0
    failed_phases: int = 0
    timeout_phases: int = 0
    memory_usage_start: float = 0.0
    memory_usage_end: float = 0.0
    cpu_usage_avg: float = 0.0
    process_count: int = 0
    startup_timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        if self.phase_count == 0:
            return 0.0
        return (self.completed_phases / self.phase_count) * 100
    
    @property
    def memory_increase(self) -> float:
        return self.memory_usage_end - self.memory_usage_start


class StartupMonitoringService:
    """启动过程监控和日志记录服务"""
    
    def __init__(self):
        """初始化启动监控服务"""
        self.logger = get_logger("StartupMonitoringService", "System")
        self.startup_logger = get_logger("StartupProcess", "System")
        self.performance_logger = get_logger("StartupPerformance", "System")
        self.error_logger = get_logger("StartupError", "System")
        
        # 启动阶段信息
        self.phases: Dict[StartupPhase, StartupPhaseInfo] = {}
        self.current_phase: Optional[StartupPhase] = None
        self.startup_start_time: Optional[datetime] = None
        self.startup_end_time: Optional[datetime] = None
        
        # 监控指标
        self.metrics = StartupMetrics()
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        
        # 性能监控数据
        self.cpu_samples: List[float] = []
        self.memory_samples: List[float] = []
        
        # 错误回调
        self.error_callbacks: List[Callable[[StartupPhase, str], None]] = []
        
        # 初始化启动阶段
        self._initialize_phases()
        
        self.logger.info("启动监控服务初始化完成")
    
    def _initialize_phases(self):
        """初始化启动阶段"""
        phase_configs = [
            (StartupPhase.INITIALIZATION, [], 10.0),
            (StartupPhase.CONFIG_LOADING, [StartupPhase.INITIALIZATION], 15.0),
            (StartupPhase.SERVICE_REGISTRATION, [StartupPhase.CONFIG_LOADING], 20.0),
            (StartupPhase.SERVICE_INITIALIZATION, [StartupPhase.SERVICE_REGISTRATION], 30.0),
            (StartupPhase.SERVICE_STARTUP, [StartupPhase.SERVICE_INITIALIZATION], 45.0),
            (StartupPhase.UI_INITIALIZATION, [StartupPhase.SERVICE_STARTUP], 25.0),
            (StartupPhase.FINAL_VALIDATION, [StartupPhase.UI_INITIALIZATION], 10.0),
            (StartupPhase.COMPLETED, [StartupPhase.FINAL_VALIDATION], 5.0)
        ]
        
        for phase, dependencies, timeout in phase_configs:
            self.phases[phase] = StartupPhaseInfo(
                phase=phase,
                dependencies=dependencies,
                timeout_seconds=timeout
            )
        
        self.metrics.phase_count = len(self.phases)
    
    def start_monitoring(self):
        """开始启动监控"""
        self.startup_logger.info("开始启动过程监控")
        
        self.startup_start_time = datetime.now()
        self.metrics.startup_timestamp = self.startup_start_time
        self.metrics.memory_usage_start = self._get_memory_usage()
        self.monitoring_active = True
        
        # 启动性能监控线程
        self.monitoring_thread = threading.Thread(
            target=self._performance_monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        
        self.startup_logger.info(f"启动监控开始，时间: {self.startup_start_time}")
        self.performance_logger.info(f"初始内存使用: {self.metrics.memory_usage_start:.2f}MB")
    
    def stop_monitoring(self):
        """停止启动监控"""
        self.monitoring_active = False
        self.startup_end_time = datetime.now()
        
        if self.startup_start_time:
            self.metrics.total_duration = (
                self.startup_end_time - self.startup_start_time
            ).total_seconds()
        
        self.metrics.memory_usage_end = self._get_memory_usage()
        
        if self.cpu_samples:
            self.metrics.cpu_usage_avg = sum(self.cpu_samples) / len(self.cpu_samples)
        
        self.metrics.process_count = len(psutil.pids())
        
        self.startup_logger.info(f"启动监控结束，时间: {self.startup_end_time}")
        self.performance_logger.info(
            f"启动总耗时: {self.metrics.total_duration:.2f}秒, "
            f"内存增长: {self.metrics.memory_increase:.2f}MB, "
            f"平均CPU使用率: {self.metrics.cpu_usage_avg:.2f}%"
        )
        
        # 等待监控线程结束
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=1.0)
    
    @contextmanager
    def phase_context(self, phase: StartupPhase, description: str = ""):
        """启动阶段上下文管理器"""
        self.start_phase(phase, description)
        try:
            yield
            self.complete_phase(phase)
        except Exception as e:
            self.fail_phase(phase, str(e))
            raise
    
    def start_phase(self, phase: StartupPhase, description: str = ""):
        """开始启动阶段"""
        if phase not in self.phases:
            self.error_logger.error(f"未知的启动阶段: {phase}")
            return
        
        phase_info = self.phases[phase]
        
        # 检查依赖阶段是否完成
        for dep_phase in phase_info.dependencies:
            if not self.phases[dep_phase].is_completed:
                error_msg = f"启动阶段 {phase.value} 的依赖阶段 {dep_phase.value} 未完成"
                self.error_logger.error(error_msg)
                self.fail_phase(phase, error_msg)
                return
        
        phase_info.status = StartupStatus.IN_PROGRESS
        phase_info.start_time = datetime.now()
        phase_info.details['description'] = description
        self.current_phase = phase
        
        desc_text = f" - {description}" if description else ""
        self.startup_logger.info(f"开始启动阶段: {phase.value}{desc_text}")
        
        # 启动超时检测
        self._start_timeout_detection(phase)
    
    def complete_phase(self, phase: StartupPhase, details: Dict[str, Any] = None):
        """完成启动阶段"""
        if phase not in self.phases:
            self.error_logger.error(f"未知的启动阶段: {phase}")
            return
        
        phase_info = self.phases[phase]
        
        if not phase_info.is_running:
            self.error_logger.warning(f"启动阶段 {phase.value} 未在运行中")
            return
        
        phase_info.status = StartupStatus.COMPLETED
        phase_info.end_time = datetime.now()
        
        if phase_info.start_time:
            phase_info.duration = (
                phase_info.end_time - phase_info.start_time
            ).total_seconds()
        
        if details:
            phase_info.details.update(details)
        
        self.metrics.completed_phases += 1
        
        self.startup_logger.info(
            f"完成启动阶段: {phase.value}, 耗时: {phase_info.duration:.2f}秒"
        )
        
        # 检查是否所有阶段都完成
        if self._all_phases_completed():
            self._handle_startup_completion()
    
    def fail_phase(self, phase: StartupPhase, error: str, details: Dict[str, Any] = None):
        """启动阶段失败"""
        if phase not in self.phases:
            self.error_logger.error(f"未知的启动阶段: {phase}")
            return
        
        phase_info = self.phases[phase]
        phase_info.status = StartupStatus.FAILED
        phase_info.end_time = datetime.now()
        phase_info.error = error
        
        if phase_info.start_time:
            phase_info.duration = (
                phase_info.end_time - phase_info.start_time
            ).total_seconds()
        
        if details:
            phase_info.details.update(details)
        
        self.metrics.failed_phases += 1
        
        self.error_logger.error(
            f"启动阶段失败: {phase.value}, 错误: {error}, 耗时: {phase_info.duration:.2f}秒"
        )
        
        # 调用错误回调
        for callback in self.error_callbacks:
            try:
                callback(phase, error)
            except Exception as e:
                self.error_logger.error(f"错误回调执行失败: {e}")
        
        # 标记启动失败
        self._handle_startup_failure(phase, error)
    
    def skip_phase(self, phase: StartupPhase, reason: str = ""):
        """跳过启动阶段"""
        if phase not in self.phases:
            self.error_logger.error(f"未知的启动阶段: {phase}")
            return
        
        phase_info = self.phases[phase]
        phase_info.status = StartupStatus.SKIPPED
        phase_info.end_time = datetime.now()
        phase_info.details['skip_reason'] = reason
        
        reason_text = f" - {reason}" if reason else ""
        self.startup_logger.info(f"跳过启动阶段: {phase.value}{reason_text}")
    
    def add_phase_detail(self, phase: StartupPhase, key: str, value: Any):
        """添加阶段详细信息"""
        if phase in self.phases:
            self.phases[phase].details[key] = value
            self.startup_logger.debug(f"阶段 {phase.value} 添加详细信息: {key} = {value}")
    
    def get_phase_info(self, phase: StartupPhase) -> Optional[StartupPhaseInfo]:
        """获取阶段信息"""
        return self.phases.get(phase)
    
    def get_current_phase(self) -> Optional[StartupPhase]:
        """获取当前阶段"""
        return self.current_phase
    
    def get_startup_metrics(self) -> StartupMetrics:
        """获取启动指标"""
        return self.metrics
    
    def add_error_callback(self, callback: Callable[[StartupPhase, str], None]):
        """添加错误回调"""
        self.error_callbacks.append(callback)
        self.logger.info("添加启动错误回调")
    
    def remove_error_callback(self, callback: Callable[[StartupPhase, str], None]):
        """移除错误回调"""
        if callback in self.error_callbacks:
            self.error_callbacks.remove(callback)
            self.logger.info("移除启动错误回调")
    
    def generate_startup_report(self) -> Dict[str, Any]:
        """生成启动报告"""
        self.logger.info("生成启动报告")
        
        try:
            phases_data = {}
            for phase, info in self.phases.items():
                phases_data[phase.value] = {
                    'status': info.status.value,
                    'start_time': info.start_time.isoformat() if info.start_time else None,
                    'end_time': info.end_time.isoformat() if info.end_time else None,
                    'duration': info.duration,
                    'error': info.error,
                    'details': info.details,
                    'dependencies': [dep.value for dep in info.dependencies],
                    'timeout_seconds': info.timeout_seconds
                }
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'startup_start_time': self.startup_start_time.isoformat() if self.startup_start_time else None,
                'startup_end_time': self.startup_end_time.isoformat() if self.startup_end_time else None,
                'metrics': {
                    'total_duration': self.metrics.total_duration,
                    'phase_count': self.metrics.phase_count,
                    'completed_phases': self.metrics.completed_phases,
                    'failed_phases': self.metrics.failed_phases,
                    'timeout_phases': self.metrics.timeout_phases,
                    'success_rate': self.metrics.success_rate,
                    'memory_usage_start': self.metrics.memory_usage_start,
                    'memory_usage_end': self.metrics.memory_usage_end,
                    'memory_increase': self.metrics.memory_increase,
                    'cpu_usage_avg': self.metrics.cpu_usage_avg,
                    'process_count': self.metrics.process_count
                },
                'phases': phases_data,
                'performance_samples': {
                    'cpu_samples': self.cpu_samples[-100:],  # 最近100个样本
                    'memory_samples': self.memory_samples[-100:]
                }
            }
            
            self.logger.info("启动报告生成完成")
            return report
            
        except Exception as e:
            self.error_logger.error(f"生成启动报告失败: {e}")
            return {}
    
    def save_startup_report(self, report: Dict[str, Any] = None, filename: str = None) -> bool:
        """保存启动报告"""
        try:
            if report is None:
                report = self.generate_startup_report()
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"startup_report_{timestamp}.json"
            
            # 确保日志目录存在 - 优先使用环境变量
            project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
            if project_root_env:
                project_root = Path(project_root_env)
            else:
                # 回退到基于文件路径的计算
                project_root = Path(__file__).parent.parent.parent.parent.parent
            report_path = project_root / "data" / "logs" / filename
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"启动报告已保存: {report_path}")
            return True
            
        except Exception as e:
            self.error_logger.error(f"保存启动报告失败: {e}")
            return False
    
    def _performance_monitoring_loop(self):
        """性能监控循环"""
        self.performance_logger.info("启动性能监控线程")
        
        try:
            while self.monitoring_active:
                try:
                    # 采集CPU使用率
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    self.cpu_samples.append(cpu_percent)
                    
                    # 采集内存使用量
                    memory_usage = self._get_memory_usage()
                    self.memory_samples.append(memory_usage)
                    
                    # 限制样本数量
                    if len(self.cpu_samples) > 1000:
                        self.cpu_samples = self.cpu_samples[-500:]
                    if len(self.memory_samples) > 1000:
                        self.memory_samples = self.memory_samples[-500:]
                    
                    time.sleep(1.0)  # 每秒采集一次
                    
                except Exception as e:
                    self.performance_logger.error(f"性能监控采集失败: {e}")
                    time.sleep(1.0)
                    
        except Exception as e:
            self.performance_logger.error(f"性能监控线程异常: {e}")
        
        self.performance_logger.info("性能监控线程结束")
    
    def _start_timeout_detection(self, phase: StartupPhase):
        """启动超时检测"""
        phase_info = self.phases[phase]
        
        def timeout_check():
            time.sleep(phase_info.timeout_seconds)
            if phase_info.is_running:
                error_msg = f"启动阶段 {phase.value} 超时 ({phase_info.timeout_seconds}秒)"
                phase_info.status = StartupStatus.TIMEOUT
                phase_info.end_time = datetime.now()
                phase_info.error = error_msg
                
                if phase_info.start_time:
                    phase_info.duration = (
                        phase_info.end_time - phase_info.start_time
                    ).total_seconds()
                
                self.metrics.timeout_phases += 1
                self.error_logger.error(error_msg)
                
                # 调用错误回调
                for callback in self.error_callbacks:
                    try:
                        callback(phase, error_msg)
                    except Exception as e:
                        self.error_logger.error(f"超时错误回调执行失败: {e}")
        
        timeout_thread = threading.Thread(target=timeout_check, daemon=True)
        timeout_thread.start()
    
    def _all_phases_completed(self) -> bool:
        """检查是否所有阶段都完成"""
        for phase_info in self.phases.values():
            if phase_info.status not in [StartupStatus.COMPLETED, StartupStatus.SKIPPED]:
                return False
        return True
    
    def _handle_startup_completion(self):
        """处理启动完成"""
        self.startup_logger.info("所有启动阶段完成")
        self.stop_monitoring()
        
        # 生成并保存启动报告
        report = self.generate_startup_report()
        self.save_startup_report(report)
        
        self.startup_logger.info(
            f"启动完成 - 总耗时: {self.metrics.total_duration:.2f}秒, "
            f"成功率: {self.metrics.success_rate:.1f}%"
        )
    
    def _handle_startup_failure(self, failed_phase: StartupPhase, error: str):
        """处理启动失败"""
        self.error_logger.error(f"启动失败于阶段: {failed_phase.value}, 错误: {error}")
        
        # 标记后续阶段为失败
        for phase, phase_info in self.phases.items():
            if phase_info.status == StartupStatus.PENDING:
                phase_info.status = StartupStatus.FAILED
                phase_info.error = f"由于前置阶段 {failed_phase.value} 失败而跳过"
                self.metrics.failed_phases += 1
        
        self.stop_monitoring()
        
        # 生成并保存启动报告
        report = self.generate_startup_report()
        self.save_startup_report(report)
    
    def _get_memory_usage(self) -> float:
        """获取当前进程内存使用量(MB)"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0
    
    def cleanup(self):
        """清理资源"""
        self.logger.info("启动监控服务清理资源")
        self.monitoring_active = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2.0)
        
        self.phases.clear()
        self.cpu_samples.clear()
        self.memory_samples.clear()
        self.error_callbacks.clear()


# 全局实例
_startup_monitoring_service = None


def get_startup_monitoring_service() -> StartupMonitoringService:
    """获取启动监控服务实例"""
    global _startup_monitoring_service
    if _startup_monitoring_service is None:
        _startup_monitoring_service = StartupMonitoringService()
    return _startup_monitoring_service


def cleanup_startup_monitoring_service():
    """清理启动监控服务"""
    global _startup_monitoring_service
    if _startup_monitoring_service is not None:
        _startup_monitoring_service.cleanup()
        _startup_monitoring_service = None