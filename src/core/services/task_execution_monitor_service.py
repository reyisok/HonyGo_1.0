#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务执行监控服务

实现定时任务的持久化、执行历史记录和性能统计分析

@author: Mr.Rey Copyright © 2025
"""

from datetime import datetime, timedelta
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional
)
import json
import threading

from dataclasses import asdict, dataclass
from enum import Enum

from src.ui.services.logging_service import get_logger
















class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 已取消
    TIMEOUT = "timeout"      # 执行超时


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskExecution:
    """任务执行记录"""
    task_id: str
    task_name: str
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    result: Optional[Any] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    priority: TaskPriority = TaskPriority.NORMAL
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskConfig:
    """任务配置"""
    task_id: str
    task_name: str
    function: Callable
    schedule_pattern: str  # cron表达式或间隔时间
    priority: TaskPriority = TaskPriority.NORMAL
    timeout_seconds: int = 300  # 5分钟默认超时
    max_retries: int = 3
    retry_delay_seconds: int = 60
    enabled: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TaskExecutionMonitorService:
    """任务执行监控服务"""
    
    def __init__(self):
        self.logger = get_logger("TaskExecutionMonitorService", "TaskMonitor")
        
        # 任务配置和执行记录
        self.task_configs: Dict[str, TaskConfig] = {}
        self.execution_history: List[TaskExecution] = []
        self.running_tasks: Dict[str, TaskExecution] = {}
        
        # 监控配置
        self.monitoring_enabled = True
        self.max_history_records = 10000  # 最大历史记录数
        self.cleanup_interval_hours = 24  # 清理间隔
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "average_duration": 0.0,
            "success_rate": 0.0,
            "last_cleanup": None
        }
        
        # 日志记录器
        self.execution_logger = get_logger('TaskExecutionData', 'TaskExecution')
        
        self.logger.info("任务执行监控服务初始化完成")
    
    def initialize(self) -> bool:
        """初始化服务"""
        try:
            self.logger.info("任务执行监控服务正在初始化...")
            # 加载历史任务配置和执行记录
            self._load_task_configs()
            self._load_execution_history()
            return True
        except Exception as e:
            self.logger.error(f"任务执行监控服务初始化失败: {e}")
            return False
    
    def start(self) -> bool:
        """启动服务"""
        try:
            self.logger.info("任务执行监控服务正在启动...")
            self.monitoring_enabled = True
            return True
        except Exception as e:
            self.logger.error(f"任务执行监控服务启动失败: {e}")
            return False
    
    def stop(self) -> bool:
        """停止服务"""
        try:
            self.logger.info("任务执行监控服务正在停止...")
            self.monitoring_enabled = False
            return True
        except Exception as e:
            self.logger.error(f"任务执行监控服务停止失败: {e}")
            return False
    
    def cleanup(self) -> bool:
        """清理资源"""
        try:
            self.logger.info("任务执行监控服务正在清理资源...")
            # 保存当前状态
            self._save_task_configs()
            self._save_execution_history()
            return True
        except Exception as e:
            self.logger.error(f"任务执行监控服务清理失败: {e}")
            return False
    
    def is_healthy(self) -> bool:
        """健康检查"""
        return self.monitoring_enabled
    
    def register_task(self, task_config: TaskConfig) -> bool:
        """注册任务"""
        try:
            with self._lock:
                self.task_configs[task_config.task_id] = task_config
                self.logger.info(f"任务 {task_config.task_name}({task_config.task_id}) 注册成功")
                return True
        except Exception as e:
            self.logger.error(f"注册任务失败: {e}")
            return False
    
    def unregister_task(self, task_id: str) -> bool:
        """注销任务"""
        try:
            with self._lock:
                if task_id in self.task_configs:
                    task_config = self.task_configs.pop(task_id)
                    self.logger.info(f"任务 {task_config.task_name}({task_id}) 注销成功")
                    return True
                else:
                    self.logger.warning(f"任务 {task_id} 不存在")
                    return False
        except Exception as e:
            self.logger.error(f"注销任务失败: {e}")
            return False
    
    def start_task_execution(self, task_id: str, **kwargs) -> Optional[TaskExecution]:
        """开始任务执行"""
        try:
            with self._lock:
                if task_id not in self.task_configs:
                    self.logger.error(f"任务 {task_id} 未注册")
                    return None
                
                task_config = self.task_configs[task_id]
                
                # 创建执行记录
                execution = TaskExecution(
                    task_id=task_id,
                    task_name=task_config.task_name,
                    status=TaskStatus.RUNNING,
                    start_time=datetime.now(),
                    priority=task_config.priority,
                    metadata=kwargs
                )
                
                self.running_tasks[task_id] = execution
                self.stats["total_tasks"] += 1
                
                # 记录到日志
                self._log_execution_data(execution)
                
                self.logger.info(f"任务 {task_config.task_name}({task_id}) 开始执行")
                return execution
                
        except Exception as e:
            self.logger.error(f"开始任务执行失败: {e}")
            return None
    
    def complete_task_execution(self, task_id: str, result: Any = None, 
                              cpu_usage: float = 0.0, memory_usage: float = 0.0) -> bool:
        """完成任务执行"""
        try:
            with self._lock:
                if task_id not in self.running_tasks:
                    self.logger.error(f"任务 {task_id} 未在运行中")
                    return False
                
                execution = self.running_tasks.pop(task_id)
                execution.status = TaskStatus.COMPLETED
                execution.end_time = datetime.now()
                execution.duration_seconds = (execution.end_time - execution.start_time).total_seconds()
                execution.result = result
                execution.cpu_usage_percent = cpu_usage
                execution.memory_usage_mb = memory_usage
                
                # 添加到历史记录
                self.execution_history.append(execution)
                self.stats["completed_tasks"] += 1
                
                # 记录到日志
                self._log_execution_data(execution)
                
                # 更新统计信息
                self._update_statistics()
                
                self.logger.info(f"任务 {execution.task_name}({task_id}) 执行完成，耗时: {execution.duration_seconds:.2f}秒")
                return True
                
        except Exception as e:
            self.logger.error(f"完成任务执行失败: {e}")
            return False
    
    def fail_task_execution(self, task_id: str, error_message: str, 
                           cpu_usage: float = 0.0, memory_usage: float = 0.0) -> bool:
        """标记任务执行失败"""
        try:
            with self._lock:
                if task_id not in self.running_tasks:
                    self.logger.error(f"任务 {task_id} 未在运行中")
                    return False
                
                execution = self.running_tasks.pop(task_id)
                execution.status = TaskStatus.FAILED
                execution.end_time = datetime.now()
                execution.duration_seconds = (execution.end_time - execution.start_time).total_seconds()
                execution.error_message = error_message
                execution.cpu_usage_percent = cpu_usage
                execution.memory_usage_mb = memory_usage
                
                # 添加到历史记录
                self.execution_history.append(execution)
                self.stats["failed_tasks"] += 1
                
                # 记录到日志
                self._log_execution_data(execution)
                
                # 更新统计信息
                self._update_statistics()
                
                self.logger.error(f"任务 {execution.task_name}({task_id}) 执行失败: {error_message}")
                return True
                
        except Exception as e:
            self.logger.error(f"标记任务失败失败: {e}")
            return False
    
    def get_task_execution_history(self, task_id: str = None, 
                                  hours: int = 24, limit: int = 100) -> List[TaskExecution]:
        """获取任务执行历史"""
        try:
            with self._lock:
                cutoff_time = datetime.now() - timedelta(hours=hours)
                
                filtered_history = [
                    execution for execution in self.execution_history
                    if execution.start_time >= cutoff_time and
                    (task_id is None or execution.task_id == task_id)
                ]
                
                # 按时间倒序排列，返回最新的记录
                filtered_history.sort(key=lambda x: x.start_time, reverse=True)
                return filtered_history[:limit]
                
        except Exception as e:
            self.logger.error(f"获取任务执行历史失败: {e}")
            return []
    
    def get_task_statistics(self, task_id: str = None, hours: int = 24) -> Dict[str, Any]:
        """获取任务统计信息"""
        try:
            with self._lock:
                cutoff_time = datetime.now() - timedelta(hours=hours)
                
                # 过滤指定时间范围内的执行记录
                filtered_executions = [
                    execution for execution in self.execution_history
                    if execution.start_time >= cutoff_time and
                    (task_id is None or execution.task_id == task_id)
                ]
                
                if not filtered_executions:
                    return {
                        "total_executions": 0,
                        "completed_executions": 0,
                        "failed_executions": 0,
                        "success_rate": 0.0,
                        "average_duration": 0.0,
                        "min_duration": 0.0,
                        "max_duration": 0.0,
                        "average_cpu_usage": 0.0,
                        "average_memory_usage": 0.0,
                        "time_range": f"最近{hours}小时"
                    }
                
                completed = [e for e in filtered_executions if e.status == TaskStatus.COMPLETED]
                failed = [e for e in filtered_executions if e.status == TaskStatus.FAILED]
                
                durations = [e.duration_seconds for e in completed if e.duration_seconds > 0]
                cpu_usages = [e.cpu_usage_percent for e in filtered_executions if e.cpu_usage_percent > 0]
                memory_usages = [e.memory_usage_mb for e in filtered_executions if e.memory_usage_mb > 0]
                
                return {
                    "total_executions": len(filtered_executions),
                    "completed_executions": len(completed),
                    "failed_executions": len(failed),
                    "success_rate": len(completed) / len(filtered_executions) * 100 if filtered_executions else 0.0,
                    "average_duration": sum(durations) / len(durations) if durations else 0.0,
                    "min_duration": min(durations) if durations else 0.0,
                    "max_duration": max(durations) if durations else 0.0,
                    "average_cpu_usage": sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0.0,
                    "average_memory_usage": sum(memory_usages) / len(memory_usages) if memory_usages else 0.0,
                    "time_range": f"最近{hours}小时"
                }
                
        except Exception as e:
            self.logger.error(f"获取任务统计信息失败: {e}")
            return {}
    
    def get_running_tasks(self) -> List[TaskExecution]:
        """获取正在运行的任务"""
        try:
            with self._lock:
                return list(self.running_tasks.values())
        except Exception as e:
            self.logger.error(f"获取运行中任务失败: {e}")
            return []
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            with self._lock:
                return {
                    "registered_tasks": len(self.task_configs),
                    "running_tasks": len(self.running_tasks),
                    "total_executions": self.stats["total_tasks"],
                    "completed_executions": self.stats["completed_tasks"],
                    "failed_executions": self.stats["failed_tasks"],
                    "success_rate": self.stats["success_rate"],
                    "average_duration": self.stats["average_duration"],
                    "history_records": len(self.execution_history),
                    "last_cleanup": self.stats["last_cleanup"],
                    "monitoring_enabled": self.monitoring_enabled
                }
        except Exception as e:
            self.logger.error(f"获取系统统计信息失败: {e}")
            return {}
    
    def _log_execution_data(self, execution: TaskExecution):
        """记录执行数据到日志"""
        try:
            # 将TaskExecution转换为可序列化的字典
            execution_dict = asdict(execution)
            
            # 处理datetime对象
            if execution_dict['start_time']:
                execution_dict['start_time'] = execution_dict['start_time'].isoformat()
            if execution_dict['end_time']:
                execution_dict['end_time'] = execution_dict['end_time'].isoformat()
            
            # 处理枚举类型
            execution_dict['status'] = execution.status.value
            execution_dict['priority'] = execution.priority.value
            
            # 记录到日志文件
            self.execution_logger.info(json.dumps(execution_dict, ensure_ascii=False))
            
        except Exception as e:
            self.logger.error(f"记录执行数据失败: {e}")
    
    def _update_statistics(self):
        """更新统计信息"""
        try:
            if self.execution_history:
                completed_executions = [
                    e for e in self.execution_history 
                    if e.status == TaskStatus.COMPLETED and e.duration_seconds > 0
                ]
                
                if completed_executions:
                    total_duration = sum(e.duration_seconds for e in completed_executions)
                    self.stats["average_duration"] = total_duration / len(completed_executions)
                
                self.stats["success_rate"] = (
                    self.stats["completed_tasks"] / self.stats["total_tasks"] * 100
                    if self.stats["total_tasks"] > 0 else 0.0
                )
                
        except Exception as e:
            self.logger.error(f"更新统计信息失败: {e}")
    
    def _load_task_configs(self):
        """加载任务配置（预留接口）"""
        # 这里可以从配置文件或数据库加载任务配置
        pass
    
    def _save_task_configs(self):
        """保存任务配置（预留接口）"""
        # 这里可以将任务配置保存到配置文件或数据库
        pass
    
    def _load_execution_history(self):
        """加载执行历史（预留接口）"""
        # 这里可以从日志文件加载历史执行记录
        pass
    
    def _save_execution_history(self):
        """保存执行历史（预留接口）"""
        # 执行历史已通过日志记录，这里可以做额外的持久化处理
        pass


# 全局任务执行监控服务实例
_task_execution_monitor_service = None


def get_task_execution_monitor_service() -> TaskExecutionMonitorService:
    """获取任务执行监控服务实例"""
    global _task_execution_monitor_service
    if _task_execution_monitor_service is None:
        _task_execution_monitor_service = TaskExecutionMonitorService()
    return _task_execution_monitor_service


def initialize_task_execution_monitor_service() -> TaskExecutionMonitorService:
    """初始化任务执行监控服务"""
    global _task_execution_monitor_service
    _task_execution_monitor_service = TaskExecutionMonitorService()
    return _task_execution_monitor_service