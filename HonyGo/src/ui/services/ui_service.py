#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HonyGo UI服务
统一管理UI相关的服务功能

@author: Mr.Rey Copyright © 2025
@created: 2025-01-04 10:30:00
@modified: 2025-01-04 10:30:00
@version: 1.0.0
"""

import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional
import requests
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QFileDialog
from src.core.ocr.services.ocr_pool_manager import get_pool_manager
from src.core.services.unified_config_service import get_config_service
from src.ui.services.lightweight_task_execution_service import LightweightTaskExecutionService
from src.ui.services.logging_service import get_logger


class UIService(QObject):
    """
    UI服务类
    负责管理UI相关的服务功能，包括OCR池服务的启动和停止
    """
    
    # 信号定义
    log_message = Signal(str)
    ocr_service_status_changed = Signal(bool)
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("UIService", "UI")
        
        # OCR池服务相关
        self.ocr_pool_process = None
        self.ocr_port = 8900
        
        # 配置服务
        try:
            self.config_service = get_config_service()
        except Exception as e:
            self.logger.warning(f"配置服务不可用: {e}")
            self.config_service = None
        
        # 轻量级任务执行服务
        try:
            self.task_service = LightweightTaskExecutionService()
        except Exception as e:
            self.logger.warning(f"任务执行服务不可用: {e}")
            self.task_service = None
        
        self.logger.info("UI服务初始化完成")
    
    def start_ocr_pool_service(self) -> bool:
        """
        启动OCR池服务
        
        Returns:
            bool: 启动是否成功
        """
        try:
            # 检查是否已经在运行
            if self.is_ocr_pool_service_running():
                self.log_message.emit("OCR池服务已在运行")
                return True
            
            # 获取OCR池管理器
            pool_manager = get_pool_manager()
            if not pool_manager:
                self.log_message.emit("无法获取OCR池管理器")
                return False
            
            # 启动OCR池服务进程
            self.log_message.emit("正在启动OCR池服务...")
            
            # 构建启动命令
            python_exe = sys.executable
            ocr_pool_script = Path("src/core/ocr/services/ocr_pool_server.py")
            
            if not ocr_pool_script.exists():
                self.log_message.emit(f"OCR池服务脚本不存在: {ocr_pool_script}")
                return False
            
            # 启动进程
            self.ocr_pool_process = subprocess.Popen(
                [python_exe, str(ocr_pool_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待服务启动
            for _ in range(10):  # 最多等待10秒
                time.sleep(1)
                if self._check_ocr_service_running():
                    self.log_message.emit(f"OCR池服务启动成功，监听端口: {self.ocr_port}")
                    self.logger.info(f"OCR池服务启动成功: PID={self.ocr_pool_process.pid}")
                    self.ocr_service_status_changed.emit(True)
                    return True
            
            # 启动超时
            self.log_message.emit("OCR池服务启动超时")
            if self.ocr_pool_process:
                self.ocr_pool_process.terminate()
                self.ocr_pool_process = None
            return False
            
        except Exception as e:
            self.logger.error(f"启动OCR池服务失败: {e}")
            self.log_message.emit(f"启动OCR池服务失败: {str(e)}")
            return False
    
    def stop_ocr_pool_service(self) -> bool:
        """
        停止OCR池服务
        
        Returns:
            bool: 停止是否成功
        """
        try:
            if self.ocr_pool_process:
                self.ocr_pool_process.terminate()
                try:
                    self.ocr_pool_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.ocr_pool_process.kill()
                    self.ocr_pool_process.wait()
                
                self.ocr_pool_process = None
                self.log_message.emit("OCR池服务已停止")
                self.logger.info("OCR池服务已停止")
                self.ocr_service_status_changed.emit(False)
                return True
            else:
                self.log_message.emit("OCR池服务未在运行")
                return False
                
        except Exception as e:
            self.logger.error(f"停止OCR池服务失败: {e}")
            self.log_message.emit(f"停止OCR池服务失败: {str(e)}")
            return False
    
    def is_ocr_pool_service_running(self) -> bool:
        """
        检查OCR池服务是否在运行
        
        Returns:
            bool: 是否在运行
        """
        return (self.ocr_pool_process is not None and 
                self.ocr_pool_process.poll() is None and 
                self._check_ocr_service_running())
    
    def _check_ocr_service_running(self) -> bool:
        """
        检查OCR服务端口是否可用
        
        Returns:
            bool: 端口是否可用
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', self.ocr_port))
                return result == 0
        except Exception:
            return False
    
    def execute_ocr_test(self) -> bool:
        """
        执行OCR测试
        
        Returns:
            bool: 测试是否成功
        """
        try:
            if self.task_service:
                return self.task_service.execute_ocr_test()
            else:
                self.logger.warning("任务执行服务不可用")
                return False
        except Exception as e:
            self.logger.error(f"执行OCR测试失败: {e}")
            return False
    
    def select_reference_image(self) -> Optional[str]:
        """
        选择参照图片
        
        Returns:
            Optional[str]: 选择的图片路径
        """
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "选择参照图片",
                "",
                "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
            )
            
            if file_path:
                self.logger.info(f"选择参照图片: {file_path}")
                return file_path
            return None
            
        except Exception as e:
            self.logger.error(f"选择参照图片失败: {e}")
            return None
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态
        
        Returns:
            Dict[str, Any]: 服务状态信息
        """
        return {
            "ocr_pool_running": self.is_ocr_pool_service_running(),
            "ocr_port": self.ocr_port,
            "task_service_available": self.task_service is not None,
            "config_service_available": self.config_service is not None
        }
    
    def cleanup(self):
        """
        清理服务资源
        """
        try:
            # 停止OCR池服务
            if self.is_ocr_pool_service_running():
                self.stop_ocr_pool_service()
            
            # 清理任务服务
            if self.task_service:
                self.task_service.cleanup()
            
            self.logger.info("UI服务清理完成")
            
        except Exception as e:
            self.logger.error(f"UI服务清理失败: {e}")


# 全局实例
_ui_service_instance: Optional[UIService] = None


def get_ui_service() -> UIService:
    """
    获取UI服务实例
    
    Returns:
        UIService: UI服务实例
    """
    global _ui_service_instance
    if _ui_service_instance is None:
        _ui_service_instance = UIService()
    return _ui_service_instance