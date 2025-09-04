#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一定时器管理服务
使用schedule库实现统一的定时器管理，替代分散的QTimer

@author: Mr.Rey Copyright © 2025
"""

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import schedule
from PySide6.QtCore import QObject, Signal
from src.core.services.task_execution_monitor_service import TaskPriority, get_task_execution_monitor_service
from src.ui.services.logging_service import get_logger


@dataclass
class TimerTask:
    """
    定时器任务数据类
    """
    task_id: str
    service_name: str
    function: Callable
    interval: float
    task_type: str  # "interval", "once", "cron"
    enabled: bool = True
    created_at: float = 0.0
    last_run: float = 0.0
    run_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at == 0.0:
            self.created_at = time.time()


class UnifiedTimerService(QObject):
    """
    统一定时器管理服务
    """
    
    # 信号定义
    task_added = Signal(str)
    task_removed = Signal(str)
    task_executed = Signal(str, bool)
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("UnifiedTimerService", "System")
        
        # 任务存储
        self.tasks: Dict[str, TimerTask] = {}
        
        # 调度器线程
        self.scheduler_thread = None
        self.running = False
        
        # 统计信息
        self.statistics = {
            "total_tasks": 0,
            "active_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_executions": 0
        }
        
        # 任务监控服务
        try:
            self.task_monitor = get_task_execution_monitor_service()
        except Exception as e:
            self.logger.warning(f"任务监控服务不可用: {e}")
            self.task_monitor = None
        
        # 启动调度器
        self._start_scheduler()
    
    def add_task(self, task_id: str, service_name: str, function: Callable, 
                 interval: float, task_type: str = "interval", 
                 metadata: Dict[str, Any] = None) -> bool:
        """
        添加定时任务
        
        Args:
            task_id: 任务ID
            service_name: 服务名称
            function: 执行函数
            interval: 间隔时间（秒）
            task_type: 任务类型（interval, once, cron）
            metadata: 元数据
            
        Returns:
            bool: 是否添加成功
        """
        try:
            if task_id in self.tasks:
                self.logger.warning(f"任务 {task_id} 已存在，将覆盖")
                self.remove_task(task_id)
            
            # 创建任务对象
            task = TimerTask(
                task_id=task_id,
                service_name=service_name,
                function=function,
                interval=interval,
                task_type=task_type,
                metadata=metadata or {}
            )
            
            self.tasks[task_id] = task
            
            # 根据任务类型添加到schedule
            if task_type == "interval":
                schedule.every(interval).seconds.do(self._execute_task, task_id).tag(task_id)
            elif task_type == "once":
                # 延迟执行一次
                schedule.every(interval).seconds.do(self._execute_task, task_id).tag(task_id)
            
            # 更新统计
            self.statistics["total_tasks"] += 1
            self.statistics["active_tasks"] += 1
            
            # 注册到任务监控服务
            if self.task_monitor:
                priority = TaskPriority.NORMAL
                if metadata and 'priority' in metadata:
                    priority_str = metadata['priority'].upper()
                    if hasattr(TaskPriority, priority_str):
                        priority = getattr(TaskPriority, priority_str)
                
                self.task_monitor.register_task(
                    task_id=task_id,
                    name=f"{service_name}_{task_id}",
                    description=f"定时任务: {service_name} - {task_id}",
                    priority=priority,
                    interval_seconds=interval if task_type == "interval" else None,
                    metadata=metadata or {}
                )
            
            self.task_added.emit(task_id)
            self.logger.info(f"添加定时任务: {task_id} ({service_name}, {interval}s, {task_type})")
            return True
            
        except Exception as e:
            self.logger.error(f"添加定时任务失败 {task_id}: {e}")
            return False
    
    def add_job(self, function: Callable, job_type: str, **kwargs) -> bool:
        """
        添加定时任务（兼容APScheduler接口）
        
        Args:
            function: 执行函数
            job_type: 任务类型
            **kwargs: 其他参数
            
        Returns:
            bool: 是否添加成功
        """
        try:
            task_id = kwargs.get('id', f"job_{int(time.time() * 1000)}")
            interval = kwargs.get('seconds', 60)
            service_name = kwargs.get('service_name', 'UnknownService')
            
            return self.add_task(
                task_id=task_id,
                service_name=service_name,
                function=function,
                interval=interval,
                task_type=job_type,
                metadata=kwargs
            )
            
        except Exception as e:
            self.logger.error(f"添加定时任务失败 (add_job): {e}")
            return False
    
    def remove_task(self, task_id: str) -> bool:
        """
        移除定时任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否移除成功
        """
        try:
            if task_id not in self.tasks:
                self.logger.warning(f"任务 {task_id} 不存在")
                return False
            
            # 从schedule中移除
            schedule.clear(task_id)
            
            # 从任务监控服务中注销
            if self.task_monitor:
                self.task_monitor.unregister_task(task_id)
            
            # 从本地存储中移除
            del self.tasks[task_id]
            self.statistics["active_tasks"] -= 1
            
            self.task_removed.emit(task_id)
            self.logger.info(f"移除定时任务: {task_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"移除定时任务失败 {task_id}: {e}")
            return False
    
    def enable_task(self, task_id: str) -> bool:
        """
        启用任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否启用成功
        """
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            self.logger.info(f"启用任务: {task_id}")
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """
        禁用任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否禁用成功
        """
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            self.logger.info(f"禁用任务: {task_id}")
            return True
        return False
    
    def _start_scheduler(self):
        """
        启动调度器线程
        """
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            self.logger.info("统一定时器服务已启动")
    
    def _scheduler_loop(self):
        """
        调度器主循环
        """
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"调度器循环异常: {e}")
                time.sleep(5)
    
    def _run_scheduler(self):
        """
        运行调度器（单次）
        """
        try:
            schedule.run_pending()
        except Exception as e:
            self.logger.error(f"调度器运行异常: {e}")
    
    def _execute_task(self, task_id: str):
        """
        执行任务
        
        Args:
            task_id: 任务ID
        """
        if task_id not in self.tasks:
            self.logger.warning(f"任务 {task_id} 不存在")
            return
        
        task = self.tasks[task_id]
        
        # 检查任务是否启用
        if not task.enabled:
            return
        
        success = False
        start_time = time.time()
        
        try:
            # 更新任务监控状态
            if self.task_monitor:
                self.task_monitor.start_task_execution(task_id)
            
            # 执行任务函数
            task.function()
            
            # 更新任务信息
            task.last_run = time.time()
            task.run_count += 1
            
            # 更新统计
            self.statistics["total_executions"] += 1
            self.statistics["completed_tasks"] += 1
            
            success = True
            
            # 如果是一次性任务，执行后移除
            if task.task_type == "once":
                self.remove_task(task_id)
            
        except Exception as e:
            self.logger.error(f"任务执行失败 {task_id}: {e}")
            self.statistics["failed_tasks"] += 1
            
        finally:
            execution_time = time.time() - start_time
            
            # 更新任务监控状态
            if self.task_monitor:
                if success:
                    self.task_monitor.complete_task_execution(
                        task_id, 
                        execution_time=execution_time
                    )
                else:
                    self.task_monitor.fail_task_execution(
                        task_id, 
                        error_message=f"任务执行失败",
                        execution_time=execution_time
                    )
            
            # 发送执行完成信号
            self.task_executed.emit(task_id, success)
            
            self.logger.debug(f"任务 {task_id} 执行完成，耗时: {execution_time:.3f}s，成功: {success}")
    
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict[str, Any]]: 任务信息
        """
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        return {
            "task_id": task.task_id,
            "service_name": task.service_name,
            "interval": task.interval,
            "task_type": task.task_type,
            "enabled": task.enabled,
            "created_at": task.created_at,
            "last_run": task.last_run,
            "run_count": task.run_count,
            "metadata": task.metadata
        }
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有任务信息
        
        Returns:
            List[Dict[str, Any]]: 所有任务信息列表
        """
        return [self.get_task_info(task_id) for task_id in self.tasks.keys()]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.statistics,
            "scheduler_running": self.running,
            "thread_alive": self.scheduler_thread.is_alive() if self.scheduler_thread else False
        }
    
    def update_config(self, config: Dict[str, Any]):
        """
        更新配置
        
        Args:
            config: 新配置
        """
        try:
            # 这里可以添加配置更新逻辑
            self.logger.info(f"定时器服务配置已更新: {config}")
        except Exception as e:
            self.logger.error(f"配置更新失败: {e}")
    
    def cleanup(self):
        """
        清理服务资源
        """
        try:
            self.running = False
            
            # 清除所有任务
            task_ids = list(self.tasks.keys())
            for task_id in task_ids:
                self.remove_task(task_id)
            
            # 清除schedule中的所有任务
            schedule.clear()
            
            # 等待调度器线程结束
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)
            
            self.logger.info("统一定时器服务清理完成")
            
        except Exception as e:
            self.logger.error(f"统一定时器服务清理失败: {e}")


# 全局实例
_timer_service_instance: Optional[UnifiedTimerService] = None


def get_timer_service() -> UnifiedTimerService:
    """
    获取统一定时器服务实例
    
    Returns:
        UnifiedTimerService: 定时器服务实例
    """
    global _timer_service_instance
    if _timer_service_instance is None:
        _timer_service_instance = UnifiedTimerService()
    return _timer_service_instance