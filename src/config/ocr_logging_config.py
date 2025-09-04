# -*- coding: utf-8 -*-
"""
OCR日志配置优化
确保所有OCR相关操作都正确记录到对应分类日志中

@author: Mr.Rey Copyright © 2025
@created: 2025-01-23 10:50:00
@modified: 2025-01-03 03:37:00
@version: 1.0.0
"""

import time
from typing import Any, Callable, Optional
from functools import wraps

from src.ui.services.logging_service import get_logger


class OCRLoggerMixin:
    """OCR日志记录混入类
    
    为OCR相关类提供统一的日志记录功能
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = None
    
    @property
    def logger(self):
        """获取日志记录器"""
        if self._logger is None:
            class_name = self.__class__.__name__
            self._logger = get_logger(f"OCR.{class_name}")
        return self._logger
    
    def log_info(self, message: str):
        """记录信息日志"""
        self.logger.info(message)
    
    def log_debug(self, message: str):
        """记录调试日志"""
        self.logger.debug(message)
    
    def log_warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(message)
    
    def log_error(self, message: str):
        """记录错误日志"""
        self.logger.error(message)
    
    def log_operation_start(self, operation: str, **params: Any):
        """记录操作开始"""
        param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        self.logger.info(f"开始执行 {operation}({param_str})")
    
    def log_operation_end(self, operation: str, duration: Optional[float] = None, **results: Any):
        """记录操作结束"""
        msg = f"完成执行 {operation}"
        if duration is not None:
            msg += f" (耗时: {duration:.3f}秒)"
        if results:
            result_str = ", ".join([f"{k}={v}" for k, v in results.items()])
            msg += f" (结果: {result_str})"
        self.logger.info(msg)
    
    def log_exception(self, operation: str, exception: Exception):
        """记录异常信息"""
        self.logger.error(f"操作 {operation} 执行异常: {type(exception).__name__}: {str(exception)}")
    
    def log_performance(self, operation: str, duration: float, **metrics: Any):
        """记录性能信息"""
        msg = f"性能统计 - {operation}: 耗时 {duration:.3f}s"
        if metrics:
            metric_strs = [f"{k}={v}" for k, v in metrics.items()]
            msg += f", {', '.join(metric_strs)}"
        self.logger.info(msg)


def log_ocr_operation(operation: str, logger_name: str = "OCR"):
    """OCR操作日志装饰器
    
    Args:
        operation: 操作名称
        logger_name: 日志器名称
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            
            try:
                # 记录操作开始
                logger.info(f"开始执行: {operation}")
                start_time = time.time()
                
                # 执行操作
                result = func(*args, **kwargs)
                
                # 记录操作成功
                duration = time.time() - start_time
                logger.info(f"操作成功: {operation} (耗时: {duration:.3f}s)")
                
                return result
                
            except Exception as e:
                # 记录操作失败
                logger.error(f"操作失败: {operation} - {str(e)}")
                raise
        
        return wrapper
    return decorator














def ocr_operation_logger(operation: str, logger_name: str = "OCR"):
    """OCR操作日志装饰器（兼容性别名）
    
    Args:
        operation: 操作名称
        logger_name: 日志器名称
    """
    return log_ocr_operation(operation, logger_name)


def setup_ocr_logging():
    """
    设置OCR专用日志配置
    """
    # 获取OCR日志器
    ocr_logger = get_logger("OCR")
    ocr_logger.info("OCR日志配置已初始化")
    
    return ocr_logger