#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步OCR处理服务
实现异步OCR处理队列和优先级管理

@author: Mr.Rey Copyright © 2025
"""

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple
)
import time
import threading
import uuid

from PySide6.QtCore import (
    QObject,
    QThread,
    QTimer,
    Signal
)
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from src.core.ocr.utils.ocr_logger import get_logger
















class OCRPriority(Enum):
    """
    OCR任务优先级枚举
    """
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class OCRTaskStatus(Enum):
    """
    OCR任务状态枚举
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OCRTask:
    """
    OCR任务数据类
    """
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    image_data: bytes = b''
    roi_info: Optional[Dict[str, Any]] = None
    target_text: str = ""
    priority: OCRPriority = OCRPriority.NORMAL
    status: OCRTaskStatus = OCRTaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[List[Tuple]] = None
    error: Optional[str] = None
    callback: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3


class AsyncOCRWorker(QThread):
    """
    异步OCR工作线程
    """
    
    # 信号定义
    task_started = Signal(str)  # 任务开始信号
    task_completed = Signal(str, list)  # 任务完成信号
    task_failed = Signal(str, str)  # 任务失败信号
    
    def __init__(self, worker_id: str, ocr_service, parent=None):
        super().__init__(parent)
        self.worker_id = worker_id
        self.ocr_service = ocr_service
        self.logger = get_logger(f"OCRWorker-{worker_id}")
        self.current_task: Optional[OCRTask] = None
        self.is_busy = False
        self.should_stop = False
    
    def set_task(self, task: OCRTask):
        """
        设置当前任务
        
        Args:
            task: OCR任务
        """
        self.current_task = task
        self.is_busy = True
    
    def run(self):
        """
        工作线程主循环
        """
        try:
            if not self.current_task:
                return
            
            task = self.current_task
            task.status = OCRTaskStatus.PROCESSING
            task.started_at = time.time()
            
            self.task_started.emit(task.task_id)
            self.logger.debug(f"开始处理任务: {task.task_id}")
            
            # 执行OCR处理
            try:
                result = self._process_ocr_task(task)
                task.result = result
                task.status = OCRTaskStatus.COMPLETED
                task.completed_at = time.time()
                
                self.task_completed.emit(task.task_id, result)
                self.logger.debug(f"任务完成: {task.task_id}")
                
            except Exception as e:
                task.error = str(e)
                task.status = OCRTaskStatus.FAILED
                task.completed_at = time.time()
                
                self.task_failed.emit(task.task_id, str(e))
                self.logger.error(f"任务失败: {task.task_id}, 错误: {e}")
            
        except Exception as e:
            self.logger.error(f"工作线程异常: {e}")
        finally:
            self.is_busy = False
            self.current_task = None
    
    def _process_ocr_task(self, task: OCRTask) -> List[Tuple]:
        """
        处理OCR任务
        
        Args:
            task: OCR任务
            
        Returns:
            List[Tuple]: OCR结果
        """
        try:
            # 这里调用实际的OCR服务
            # 注意：这是一个同步调用，在工作线程中执行
            if hasattr(self.ocr_service, 'recognize_text_sync'):
                return self.ocr_service.recognize_text_sync(
                    task.image_data, 
                    task.roi_info, 
                    task.target_text
                )
            else:
                # 如果没有同步方法，使用异步方法的同步版本
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self.ocr_service.recognize_text(
                            task.image_data, 
                            task.roi_info, 
                            task.target_text
                        )
                    )
                finally:
                    loop.close()
        except Exception as e:
            self.logger.error(f"OCR处理失败: {e}")
            raise
    
    def stop(self):
        """
        停止工作线程
        """
        self.should_stop = True
        if self.current_task:
            self.current_task.status = OCRTaskStatus.CANCELLED


class AsyncOCRService(QObject):
    """
    异步OCR处理服务类
    """
    
    # 信号定义
    task_queued = Signal(str)  # 任务入队信号
    task_started = Signal(str)  # 任务开始信号
    task_completed = Signal(str, list)  # 任务完成信号
    task_failed = Signal(str, str)  # 任务失败信号
    queue_status_changed = Signal(dict)  # 队列状态变化信号
    
    def __init__(self, ocr_service):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.ocr_service = ocr_service
        
        # 服务配置
        self.config = {
            "max_workers": 4,              # 最大工作线程数
            "max_queue_size": 100,         # 最大队列大小
            "task_timeout": 30.0,          # 任务超时时间（秒）
            "enable_priority_queue": True,  # 启用优先级队列
            "enable_parallel_processing": True,  # 启用并行处理
            "queue_check_interval": 100    # 队列检查间隔（毫秒）
        }
        
        # 任务队列（按优先级分组）
        self.task_queues = {
            OCRPriority.CRITICAL: [],
            OCRPriority.HIGH: [],
            OCRPriority.NORMAL: [],
            OCRPriority.LOW: []
        }
        
        # 任务管理
        self.active_tasks: Dict[str, OCRTask] = {}
        self.completed_tasks: Dict[str, OCRTask] = {}
        self.failed_tasks: Dict[str, OCRTask] = {}
        
        # 工作线程池
        self.workers: Dict[str, AsyncOCRWorker] = {}
        self.available_workers: List[str] = []
        
        # 队列处理定时器
        if threading.current_thread() == threading.main_thread():
            self.queue_timer = QTimer()
            self.queue_timer.timeout.connect(self._process_queue)
        else:
            self.queue_timer = None
        
        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0,
            "average_processing_time": 0.0,
            "queue_wait_time": 0.0
        }
        
        # 初始化服务
        self._initialize_workers()
        self._start_queue_processing()
        
        self.logger.info("异步OCR处理服务初始化完成")
    
    def _initialize_workers(self):
        """
        初始化工作线程
        """
        try:
            for i in range(self.config["max_workers"]):
                worker_id = f"worker_{i}"
                worker = AsyncOCRWorker(worker_id, self.ocr_service, self)
                
                # 连接信号
                worker.task_started.connect(self._on_task_started)
                worker.task_completed.connect(self._on_task_completed)
                worker.task_failed.connect(self._on_task_failed)
                
                self.workers[worker_id] = worker
                self.available_workers.append(worker_id)
            
            self.logger.info(f"初始化了{len(self.workers)}个工作线程")
        except Exception as e:
            self.logger.error(f"工作线程初始化失败: {e}")
    
    def _start_queue_processing(self):
        """
        启动队列处理
        """
        try:
            self.queue_timer.start(self.config["queue_check_interval"])
            self.logger.info("队列处理已启动")
        except Exception as e:
            self.logger.error(f"队列处理启动失败: {e}")
    
    def _process_queue(self):
        """
        处理任务队列
        """
        try:
            if not self.available_workers:
                return
            
            # 按优先级顺序处理任务
            for priority in [OCRPriority.CRITICAL, OCRPriority.HIGH, 
                           OCRPriority.NORMAL, OCRPriority.LOW]:
                queue = self.task_queues[priority]
                
                while queue and self.available_workers:
                    task = queue.pop(0)
                    worker_id = self.available_workers.pop(0)
                    
                    # 分配任务给工作线程
                    self._assign_task_to_worker(task, worker_id)
                    
                    if not self.config["enable_parallel_processing"]:
                        break
                
                if not self.available_workers:
                    break
            
            # 发送队列状态更新
            self._emit_queue_status()
            
        except Exception as e:
            self.logger.error(f"队列处理失败: {e}")
    
    def _assign_task_to_worker(self, task: OCRTask, worker_id: str):
        """
        将任务分配给工作线程
        
        Args:
            task: OCR任务
            worker_id: 工作线程ID
        """
        try:
            worker = self.workers[worker_id]
            worker.set_task(task)
            
            self.active_tasks[task.task_id] = task
            
            # 启动工作线程
            worker.start()
            
            self.logger.debug(f"任务 {task.task_id} 已分配给工作线程 {worker_id}")
        except Exception as e:
            self.logger.error(f"任务分配失败: {e}")
            # 将工作线程重新加入可用列表
            if worker_id not in self.available_workers:
                self.available_workers.append(worker_id)
    
    def _on_task_started(self, task_id: str):
        """
        任务开始处理回调
        
        Args:
            task_id: 任务ID
        """
        self.task_started.emit(task_id)
    
    def _on_task_completed(self, task_id: str, result: List[Tuple]):
        """
        任务完成回调
        
        Args:
            task_id: 任务ID
            result: OCR结果
        """
        try:
            if task_id in self.active_tasks:
                task = self.active_tasks.pop(task_id)
                task.result = result
                self.completed_tasks[task_id] = task
                
                # 更新统计信息
                self.stats["completed_tasks"] += 1
                if task.started_at and task.completed_at:
                    processing_time = task.completed_at - task.started_at
                    self._update_average_processing_time(processing_time)
                
                # 执行回调
                if task.callback:
                    try:
                        task.callback(task_id, result, None)
                    except Exception as e:
                        self.logger.error(f"任务回调执行失败: {e}")
                
                # 释放工作线程
                self._release_worker_for_task(task_id)
                
                self.task_completed.emit(task_id, result)
                
        except Exception as e:
            self.logger.error(f"任务完成处理失败: {e}")
    
    def _on_task_failed(self, task_id: str, error: str):
        """
        任务失败回调
        
        Args:
            task_id: 任务ID
            error: 错误信息
        """
        try:
            if task_id in self.active_tasks:
                task = self.active_tasks.pop(task_id)
                task.error = error
                
                # 检查是否需要重试
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = OCRTaskStatus.PENDING
                    
                    # 重新加入队列
                    self.task_queues[task.priority].append(task)
                    self.logger.info(f"任务 {task_id} 重试 ({task.retry_count}/{task.max_retries})")
                else:
                    # 达到最大重试次数，标记为失败
                    self.failed_tasks[task_id] = task
                    self.stats["failed_tasks"] += 1
                    
                    # 执行回调
                    if task.callback:
                        try:
                            task.callback(task_id, None, error)
                        except Exception as e:
                            self.logger.error(f"任务回调执行失败: {e}")
                    
                    self.task_failed.emit(task_id, error)
                
                # 释放工作线程
                self._release_worker_for_task(task_id)
                
        except Exception as e:
            self.logger.error(f"任务失败处理失败: {e}")
    
    def _release_worker_for_task(self, task_id: str):
        """
        释放任务对应的工作线程
        
        Args:
            task_id: 任务ID
        """
        try:
            for worker_id, worker in self.workers.items():
                if (worker.current_task and 
                    worker.current_task.task_id == task_id) or not worker.is_busy:
                    if worker_id not in self.available_workers:
                        self.available_workers.append(worker_id)
                    break
        except Exception as e:
            self.logger.error(f"工作线程释放失败: {e}")
    
    def _update_average_processing_time(self, processing_time: float):
        """
        更新平均处理时间
        
        Args:
            processing_time: 处理时间
        """
        try:
            completed_count = self.stats["completed_tasks"]
            if completed_count == 1:
                self.stats["average_processing_time"] = processing_time
            else:
                # 计算移动平均
                current_avg = self.stats["average_processing_time"]
                self.stats["average_processing_time"] = (
                    (current_avg * (completed_count - 1) + processing_time) / completed_count
                )
        except Exception as e:
            self.logger.error(f"平均处理时间更新失败: {e}")
    
    def _emit_queue_status(self):
        """
        发送队列状态信号
        """
        try:
            status = {
                "total_queued": sum(len(queue) for queue in self.task_queues.values()),
                "active_tasks": len(self.active_tasks),
                "available_workers": len(self.available_workers),
                "queue_by_priority": {
                    priority.name: len(queue) 
                    for priority, queue in self.task_queues.items()
                }
            }
            self.queue_status_changed.emit(status)
        except Exception as e:
            self.logger.error(f"队列状态发送失败: {e}")
    
    def submit_task(self, image_data: bytes, roi_info: Dict[str, Any] = None,
                   target_text: str = "", priority: OCRPriority = OCRPriority.NORMAL,
                   callback: Callable = None, metadata: Dict[str, Any] = None) -> str:
        """
        提交OCR任务
        
        Args:
            image_data: 图像数据
            roi_info: ROI信息
            target_text: 目标文字
            priority: 任务优先级
            callback: 完成回调函数
            metadata: 元数据
            
        Returns:
            str: 任务ID
        """
        try:
            # 检查队列大小限制
            total_queued = sum(len(queue) for queue in self.task_queues.values())
            if total_queued >= self.config["max_queue_size"]:
                raise Exception(f"队列已满，当前大小: {total_queued}")
            
            # 创建任务
            task = OCRTask(
                image_data=image_data,
                roi_info=roi_info,
                target_text=target_text,
                priority=priority,
                callback=callback,
                metadata=metadata or {}
            )
            
            # 加入对应优先级队列
            self.task_queues[priority].append(task)
            
            # 更新统计
            self.stats["total_tasks"] += 1
            
            self.task_queued.emit(task.task_id)
            self.logger.debug(f"任务已入队: {task.task_id}, 优先级: {priority.name}")
            
            return task.task_id
            
        except Exception as e:
            self.logger.error(f"任务提交失败: {e}")
            raise
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        try:
            # 在队列中查找并移除
            for priority, queue in self.task_queues.items():
                for i, task in enumerate(queue):
                    if task.task_id == task_id:
                        task.status = OCRTaskStatus.CANCELLED
                        queue.pop(i)
                        self.stats["cancelled_tasks"] += 1
                        self.logger.info(f"任务已从队列中取消: {task_id}")
                        return True
            
            # 在活动任务中查找
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                task.status = OCRTaskStatus.CANCELLED
                
                # 停止对应的工作线程
                for worker in self.workers.values():
                    if (worker.current_task and 
                        worker.current_task.task_id == task_id):
                        worker.stop()
                        break
                
                self.stats["cancelled_tasks"] += 1
                self.logger.info(f"活动任务已取消: {task_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"任务取消失败: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[OCRTaskStatus]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            OCRTaskStatus: 任务状态
        """
        try:
            # 检查各个状态的任务
            if task_id in self.active_tasks:
                return self.active_tasks[task_id].status
            
            if task_id in self.completed_tasks:
                return OCRTaskStatus.COMPLETED
            
            if task_id in self.failed_tasks:
                return OCRTaskStatus.FAILED
            
            # 检查队列中的任务
            for queue in self.task_queues.values():
                for task in queue:
                    if task.task_id == task_id:
                        return task.status
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取任务状态失败: {e}")
            return None
    
    def get_task_result(self, task_id: str) -> Optional[List[Tuple]]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            List[Tuple]: OCR结果
        """
        try:
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id].result
            return None
        except Exception as e:
            self.logger.error(f"获取任务结果失败: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取服务统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            return {
                **self.stats,
                "queue_sizes": {
                    priority.name: len(queue) 
                    for priority, queue in self.task_queues.items()
                },
                "active_tasks_count": len(self.active_tasks),
                "available_workers": len(self.available_workers),
                "total_workers": len(self.workers)
            }
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def update_config(self, config: Dict[str, Any]):
        """
        更新服务配置
        
        Args:
            config: 新的配置参数
        """
        try:
            self.config.update(config)
            
            # 更新队列检查间隔
            if self.queue_timer.isActive():
                self.queue_timer.setInterval(self.config["queue_check_interval"])
            
            self.logger.info(f"异步OCR服务配置已更新: {config}")
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
            # 停止队列处理
            if self.queue_timer.isActive():
                self.queue_timer.stop()
            
            # 停止所有工作线程
            for worker in self.workers.values():
                worker.stop()
                if worker.isRunning():
                    worker.wait(5000)  # 等待5秒
            
            # 清理任务队列
            for queue in self.task_queues.values():
                queue.clear()
            
            self.logger.info("异步OCR处理服务清理完成")
        except Exception as e:
            self.logger.error(f"异步OCR处理服务清理失败: {e}")