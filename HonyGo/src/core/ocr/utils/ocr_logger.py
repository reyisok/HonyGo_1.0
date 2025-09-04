#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR日志服务包装器
为OCR功能提供统一日志记录接口，内部使用统一日志服务

@author: Mr.Rey Copyright © 2025
@created: 2025-01-24 15:45:00
@modified: 2025-01-24 15:45:00
@version: 1.0.0
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.ui.services.logging_service import get_logger


class OCRLogger:
    """OCR专用日志记录器
    
    提供OCR模块专用的日志记录功能，内部使用统一日志服务
    """
    
    def __init__(self, name: str = "OCR", log_level: int = logging.INFO):
        """初始化OCR日志记录器
        
        Args:
            name: 日志记录器名称
            log_level: 日志级别
        """
        self.name = name
        self.log_level = log_level
        
        # 优先使用统一日志服务
        try:
            self.unified_logger = unified_get_logger(f"OCR.{name}")
            self.use_unified = True
        except Exception:
            # 如果统一日志服务不可用，使用备用日志
            self.use_unified = False
            self._setup_fallback_logger()
    
    def _setup_fallback_logger(self):
        """设置备用日志记录器"""
        # 创建日志记录器 - 使用统一日志服务的格式但独立管理
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.log_level)
        
        # 避免重复添加处理器
        if self.logger.handlers:
            return
        
        # 确定日志目录 - 使用统一的日志目录
        # 获取项目根目录
        project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
        if project_root_env:
            project_root = Path(project_root_env)
        else:
            # 备用方案：从当前文件路径计算到项目根目录
            project_root = Path(__file__).parent.parent.parent.parent.parent
 
        log_dir = project_root / "data" / "logs" / "OCR"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建日志文件路径
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"OCR_Fallback_{timestamp}.log"
        
        # 创建格式化器 - 与统一格式保持一致
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] [Thread-%(thread)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str):
        """记录调试信息"""
        if self.use_unified:
            self.unified_logger.debug(message)
        else:
            self.logger.debug(message)
    
    def info(self, message: str):
        """记录一般信息"""
        if self.use_unified:
            self.unified_logger.info(message)
        else:
            self.logger.info(message)
    
    def warning(self, message: str):
        """记录警告信息"""
        if self.use_unified:
            self.unified_logger.warning(message)
        else:
            self.logger.warning(message)
    
    def error(self, message: str):
        """记录错误信息"""
        if self.use_unified:
            self.unified_logger.error(message)
        else:
            self.logger.error(message)
    
    def critical(self, message: str):
        """记录严重错误信息"""
        if self.use_unified:
            self.unified_logger.critical(message)
        else:
            self.logger.critical(message)
    
    def log_function_start(self, func_name: str, **params: Any):
        """记录函数开始执行"""
        param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        self.info(f"开始执行 {func_name}({param_str})")
    
    def log_function_end(self, func_name: str, result: Any = None, duration: Optional[float] = None):
        """记录函数执行结束"""
        msg = f"完成执行 {func_name}"
        if duration is not None:
            msg += f" (耗时: {duration:.3f}秒)"
        if result is not None:
            msg += f" (结果: {result})"
        self.info(msg)
    
    def log_exception(self, func_name: str, exception: Exception):
        """记录异常信息"""
        self.error(f"函数 {func_name} 执行异常: {type(exception).__name__}: {str(exception)}")
    
    def log_process_status(self, process_name: str, status: str, pid: Optional[int] = None):
        """记录进程状态"""
        msg = f"进程 {process_name} 状态: {status}"
        if pid:
            msg += f" (PID: {pid})"
        self.info(msg)
    
    def log_performance(self, operation: str, duration: float, **metrics: Any):
        """记录性能信息"""
        msg = f"性能统计 - {operation}: 耗时 {duration:.3f}s"
        if metrics:
            metric_strs = [f"{k}={v}" for k, v in metrics.items()]
            msg += f", {', '.join(metric_strs)}"
        self.info(msg)


# 创建全局OCR日志实例
ocr_logger = OCRLogger()


# 便捷函数
def log_debug(message: str):
    """记录调试信息"""
    ocr_logger.debug(message)


def log_info(message: str):
    """记录一般信息"""
    ocr_logger.info(message)


def log_warning(message: str):
    """记录警告信息"""
    ocr_logger.warning(message)


def log_error(message: str):
    """记录错误信息"""
    ocr_logger.error(message)


def log_critical(message: str):
    """记录严重错误信息"""
    ocr_logger.critical(message)


# 导出get_logger函数以保持兼容性
def get_logger(name: str = "OCR", category: str = "OCR", log_level: Optional[int] = None) -> OCRLogger:
    """获取OCR日志记录器
    
    Args:
        name: 日志记录器名称
        category: 日志分类（保持兼容性）
        log_level: 日志级别
        
    Returns:
        OCRLogger实例
    """
    if log_level is None:
        log_level = logging.INFO
    return OCRLogger(name, log_level)


if __name__ == "__main__":
    # 测试日志功能
    log_info("OCR日志服务初始化完成")
    log_debug("这是一条调试信息")
    log_warning("这是一条警告信息")
    log_error("这是一条错误信息")
    log_critical("这是一条严重错误信息")
    
    # 测试函数日志
    ocr_logger.log_function_start("test_function", param1="value1", param2=123)
    ocr_logger.log_function_end("test_function", result="success", duration=0.123)
    
    # 测试进程状态日志
    ocr_logger.log_process_status("easyocr_service", "running", pid=1234)