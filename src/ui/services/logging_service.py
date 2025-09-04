#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志服务
为整个HonyGo应用程序提供统一的日志管理功能

@author: Mr.Rey Copyright © 2025
"""

from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional
)
import logging
import os
import sys

import shutil

from src.ui.services.cross_process_log_bridge import get_log_bridge_server















class UILogHandler(logging.Handler):
    """
    UI日志处理器 - 将日志输出到界面
    """
    
    def __init__(self, ui_callback: Callable[[str, str], None]):
        super().__init__()
        self.ui_callback = ui_callback
        # 修复重复日志问题：UI处理器不需要包含levelname，因为UI回调会单独处理级别
        self.setFormatter(logging.Formatter('[%(name)s] %(message)s'))
    
    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname
            if self.ui_callback:
                self.ui_callback(level, msg)
        except Exception:
            self.handleError(record)


class UnifiedLoggingService:
    """
    统一日志服务管理器
    提供应用程序级别的统一日志管理
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            # 优先使用环境变量中的项目根目录路径，确保路径一致性
            project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
            if project_root_env:
                self.project_root = Path(project_root_env)
            else:
                # 备用方案：从 src/ui/services 向上到项目根目录
                self.project_root = Path(__file__).parent.parent.parent
            
            # 确保项目根目录路径正确
            # 检查是否为正确的项目根目录（应该包含src目录和start_honygo.py文件）
            if not (self.project_root / "src").exists() or not (self.project_root / "start_honygo.py").exists():
                raise RuntimeError(f"项目根目录路径错误: {self.project_root}，缺少src目录或start_honygo.py文件")
            
            self.log_base_dir = self.project_root / "data" / "logs"
            self.loggers: Dict[str, logging.Logger] = {}
            self.ui_handler: Optional[UILogHandler] = None
            # 日志文件配置
            self.max_log_size = 10 * 1024 * 1024  # 10MB
            self.backup_count = 5  # 保留5个备份文件
            self.archive_dir = self.log_base_dir / "archive"
            self._setup_base_logging()
            UnifiedLoggingService._initialized = True
    
    def _setup_base_logging(self):
        """
        设置基础日志配置
        """
        # 创建日志目录结构
        self.app_log_dir = self.log_base_dir / "Application"
        self.system_log_dir = self.log_base_dir / "System"
        self.ocr_log_dir = self.log_base_dir / "OCR"
        self.error_log_dir = self.log_base_dir / "Error"
        self.performance_log_dir = self.log_base_dir / "Performance"
        self.tests_log_dir = self.log_base_dir / "Tests"
        self.general_log_dir = self.log_base_dir / "General"
        
        for log_dir in [self.app_log_dir, self.system_log_dir, self.ocr_log_dir, self.error_log_dir, 
                       self.performance_log_dir, self.tests_log_dir, self.general_log_dir, self.archive_dir]:
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器以避免重复
        root_logger.handlers.clear()
        
        # 创建统一格式
        self.detailed_format = '[%(asctime)s] [%(levelname)s] [%(name)s] [Thread-%(thread)d] %(message)s'
        self.simple_format = '[%(asctime)s] [%(levelname)s] %(message)s'
        self.date_format = '%Y-%m-%d %H:%M:%S'
        
        # 创建主应用日志文件
        timestamp = datetime.now().strftime("%Y%m%d")
        main_log_file = self.app_log_dir / f"HonyGo_Main_{timestamp}.log"
        error_log_file = self.error_log_dir / f"HonyGo_Error_{timestamp}.log"
        
        # 主日志文件处理器 - 使用RotatingFileHandler
        main_file_handler = RotatingFileHandler(
            main_log_file, 
            maxBytes=self.max_log_size, 
            backupCount=self.backup_count, 
            encoding='utf-8'
        )
        main_file_handler.setLevel(logging.DEBUG)
        main_file_handler.setFormatter(logging.Formatter(self.detailed_format, self.date_format))
        root_logger.addHandler(main_file_handler)
        
        # 错误日志文件处理器 - 使用RotatingFileHandler
        error_file_handler = RotatingFileHandler(
            error_log_file, 
            maxBytes=self.max_log_size, 
            backupCount=self.backup_count, 
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(logging.Formatter(self.detailed_format, self.date_format))
        root_logger.addHandler(error_file_handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(self.simple_format, '%H:%M:%S'))
        root_logger.addHandler(console_handler)
        
        # 设置第三方库日志级别
        logging.getLogger('PySide6').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
    
    def set_ui_callback(self, ui_callback: Callable[[str, str], None]):
        """
        设置UI回调函数，用于将日志输出到界面
        
        Args:
            ui_callback: 回调函数，接收(level, message)参数
        """
        # 保存UI回调函数
        self.ui_callback = ui_callback
        
        if self.ui_handler:
            # 移除旧的UI处理器
            root_logger = logging.getLogger()
            if self.ui_handler in root_logger.handlers:
                root_logger.removeHandler(self.ui_handler)
            
            # 从所有特定记录器移除
            for logger in self.loggers.values():
                if self.ui_handler in logger.handlers:
                    logger.removeHandler(self.ui_handler)
        
        # 创建新的UI处理器
        self.ui_handler = UILogHandler(ui_callback)
        self.ui_handler.setLevel(logging.DEBUG)  # 设置为DEBUG级别以接收所有日志
        
        # 添加到根日志记录器
        root_logger = logging.getLogger()
        root_logger.addHandler(self.ui_handler)
        
        # 确保根记录器的级别不会阻止日志传播
        if root_logger.level > logging.DEBUG:
            root_logger.setLevel(logging.DEBUG)
        
        # 添加到所有已存在的特定记录器（修复聚合显示问题）
        ui_handler_added_count = 0
        for logger in self.loggers.values():
            if not any(isinstance(h, UILogHandler) for h in logger.handlers):
                logger.addHandler(self.ui_handler)
                ui_handler_added_count += 1
        
        # 同时检查所有已注册的logger（包括通过logging.getLogger创建的）
        all_loggers = [logging.getLogger(name) for name in logging.Logger.manager.loggerDict]
        for logger in all_loggers:
            if hasattr(logger, 'handlers') and logger.name.startswith(('Application.', 'System.', 'OCR.', 'Error.')):
                if not any(isinstance(h, UILogHandler) for h in logger.handlers):
                    logger.addHandler(self.ui_handler)
                    ui_handler_added_count += 1
        
        # 直接启动跨进程日志桥接服务器
        try:
            log_bridge = get_log_bridge_server()
            log_bridge.set_ui_callback(self.ui_callback)
            if log_bridge.start_server():
                # 跨进程日志桥接服务器已启动
                pass
            else:
                # 跨进程日志桥接服务器启动失败
                pass
        except Exception as e:
            # 跨进程日志桥接服务器启动异常
            pass
        
        # 调试信息已通过内部日志记录
    
    def get_logger(self, name: str, category: str = "Application", level: int = logging.INFO) -> logging.Logger:
        """
        获取指定名称和类别的日志记录器
        
        Args:
            name: 日志记录器名称
            category: 日志类别 (Application, System, OCR, Error)
            level: 日志级别
            
        Returns:
            配置好的日志记录器
        """
        logger_key = f"{category}.{name}"
        
        if logger_key in self.loggers:
            # 确保现有logger也有UI处理器（修复聚合显示问题）
            existing_logger = self.loggers[logger_key]
            if hasattr(self, 'ui_handler') and self.ui_handler:
                if not any(isinstance(h, UILogHandler) for h in existing_logger.handlers):
                    existing_logger.addHandler(self.ui_handler)
            return existing_logger
        
        logger = logging.getLogger(logger_key)
        logger.setLevel(level)
        
        # 阻止向根记录器传播，避免重复输出
        logger.propagate = False
        
        # 为所有类别添加专用日志文件处理器
        self._add_category_handler(logger, category)
        
        # 添加控制台处理器到特定logger，因为已经阻止了传播
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            # 修复重复日志问题：简化控制台格式，避免与UI处理器重复
            console_formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # 确保UI回调处理器被添加到特定logger中（修复聚合显示问题）
        if hasattr(self, 'ui_handler') and self.ui_handler:
            if not any(isinstance(h, UILogHandler) for h in logger.handlers):
                logger.addHandler(self.ui_handler)
        
        self.loggers[logger_key] = logger
        return logger
    
    def _add_category_handler(self, logger: logging.Logger, category: str):
        """
        为特定类别添加专用日志处理器
        
        Args:
            logger: 日志记录器
            category: 日志类别
        """
        # 检查是否已经有处理器，避免重复添加
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler) and category in str(handler.baseFilename):
                return  # 已经存在该类别的处理器，直接返回
        
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # 根据类别确定日志目录和文件名
        if category == "OCR":
            log_dir = self.ocr_log_dir
            log_file = log_dir / f"OCR_Pool_{timestamp}.log"
        elif category == "System":
            log_dir = self.system_log_dir
            log_file = log_dir / f"HonyGo_System_{timestamp}.log"
        elif category == "Tests":
            log_dir = self.tests_log_dir
            log_file = log_dir / f"Tests_{timestamp}.log"
        elif category == "Performance":
            log_dir = self.performance_log_dir
            log_file = log_dir / f"Performance_{timestamp}.log"
        elif category == "Application":
            log_dir = self.app_log_dir
            log_file = log_dir / f"Application_{timestamp}.log"
        else:
            # 其他类别使用通用目录
            log_dir = self.log_base_dir / category
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"{category}_{timestamp}.log"
        
        # 创建类别专用文件处理器
        category_handler = logging.FileHandler(log_file, encoding='utf-8')
        category_handler.setLevel(logging.DEBUG)
        category_handler.setFormatter(logging.Formatter(self.detailed_format, self.date_format))
        logger.addHandler(category_handler)
    
    def log_system_info(self):
        """
        记录系统信息
        """
        system_logger = self.get_logger("System", "System")
        system_logger.info("=== HonyGo 统一日志系统启动 ===")
        system_logger.info(f"项目根目录: {self.project_root}")
        system_logger.info(f"日志基础目录: {self.log_base_dir}")
        system_logger.info(f"Python版本: {sys.version}")
        system_logger.info(f"工作目录: {os.getcwd()}")
        system_logger.info("=== 日志系统初始化完成 ===")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        获取日志统计信息
        
        Returns:
            日志统计信息字典
        """
        stats = {
            "total_loggers": len(self.loggers),
            "log_directories": {
                "application": str(self.app_log_dir),
                "system": str(self.system_log_dir),
                "ocr": str(self.ocr_log_dir),
                "error": str(self.error_log_dir),
                "archive": str(self.archive_dir)
            },
            "active_loggers": list(self.loggers.keys()),
            "max_log_size_mb": self.max_log_size / (1024 * 1024),
            "backup_count": self.backup_count
        }
        return stats
    
    def clear_logger_cache(self):
        """
        清除logger缓存，强制重新创建所有logger实例
        这在修改了logger配置后需要重新应用时很有用
        """
        # 关闭所有现有的文件处理器
        for logger in self.loggers.values():
            for handler in logger.handlers[:]:
                if isinstance(handler, (logging.FileHandler, RotatingFileHandler)):
                    handler.close()
                    logger.removeHandler(handler)
        
        # 清空logger缓存
        self.loggers.clear()
        
        # 清理Python内置的logger管理器缓存
        logging.Logger.manager.loggerDict.clear()
        
        # Logger缓存已清除，所有logger将重新创建
    
    def filter_logs_by_level(self, log_file_path: str, level: str = "ERROR") -> List[str]:
        """
        按日志级别筛选日志内容
        
        Args:
            log_file_path: 日志文件路径
            level: 要筛选的日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            
        Returns:
            筛选后的日志行列表
        """
        filtered_logs = []
        try:
            log_path = Path(log_file_path)
            if not log_path.exists():
                return filtered_logs
                
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if f'[{level}]' in line:
                        filtered_logs.append(line.strip())
        except Exception as e:
            error_logger = self.get_logger("LogFilter", "System")
            error_logger.error(f"筛选日志失败: {e}")
            
        return filtered_logs
    
    def archive_old_logs(self, days_old: int = 7) -> Dict[str, int]:
        """
        归档旧日志文件
        
        Args:
            days_old: 归档多少天前的日志文件
            
        Returns:
            归档统计信息
        """
        archived_count = 0
        total_size = 0
        
        try:
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
            
            for log_dir in [self.app_log_dir, self.system_log_dir, self.ocr_log_dir, self.error_log_dir]:
                for log_file in log_dir.glob("*.log*"):
                    if log_file.stat().st_mtime < cutoff_time:
                        # 移动到归档目录
                        archive_path = self.archive_dir / log_file.name
                        shutil.move(str(log_file), str(archive_path))
                        archived_count += 1
                        total_size += archive_path.stat().st_size
                        
            archive_logger = self.get_logger("LogArchive", "System")
            archive_logger.info(f"日志归档完成: 归档了 {archived_count} 个文件，总大小 {total_size / (1024*1024):.2f}MB")
            
        except Exception as e:
            error_logger = self.get_logger("LogArchive", "System")
            error_logger.error(f"日志归档失败: {e}")
            
        return {
            "archived_files": archived_count,
            "total_size_mb": total_size / (1024 * 1024)
        }
    
    def get_error_logs_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取最近错误日志摘要
        
        Args:
            hours: 获取最近多少小时的错误日志
            
        Returns:
            错误日志摘要信息
        """
        error_summary = {
            "total_errors": 0,
            "error_types": {},
            "recent_errors": []
        }
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d")
            error_log_file = self.error_log_dir / f"HonyGo_Error_{timestamp}.log"
            
            if error_log_file.exists():
                cutoff_time = datetime.now().timestamp() - (hours * 3600)
                
                with open(error_log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '[ERROR]' in line:
                            error_summary["total_errors"] += 1
                            
                            # 提取错误类型
                            if 'Traceback' in line or 'Exception' in line:
                                error_type = "Exception"
                            elif 'Failed' in line or '失败' in line:
                                error_type = "Operation Failed"
                            else:
                                error_type = "General Error"
                                
                            error_summary["error_types"][error_type] = error_summary["error_types"].get(error_type, 0) + 1
                            
                            # 保存最近的错误（最多10条）
                            if len(error_summary["recent_errors"]) < 10:
                                error_summary["recent_errors"].append(line.strip())
                                
        except Exception as e:
            summary_logger = self.get_logger("ErrorSummary", "System")
            summary_logger.error(f"获取错误日志摘要失败: {e}")
            
        return error_summary

# 创建全局统一日志服务实例
_unified_logging_service = None

# 便捷函数
def get_logger(name: str, category: str = "Application", level: int = logging.INFO) -> logging.Logger:
    """获取指定名称和类别的日志记录器
    
    Args:
        name: 日志记录器名称
        category: 日志类别
        level: 日志级别
        
    Returns:
        配置好的日志记录器
    """
    global _unified_logging_service
    if _unified_logging_service is None:
        _unified_logging_service = UnifiedLoggingService()
    return _unified_logging_service.get_logger(name, category, level)

def log_system_info():
    """
    记录系统信息的便捷函数
    """
    _unified_logging_service.log_system_info()

def get_log_stats() -> Dict[str, Any]:
    """
    获取日志统计信息的便捷函数
    
    Returns:
        日志统计信息字典
    """
    return _unified_logging_service.get_log_stats()


def set_ui_log_callback(ui_callback: Callable[[str, str], None]):
    """
    设置UI日志回调函数的便捷函数
    
    Args:
        ui_callback: 回调函数，接收(level, message)参数
    """
    _unified_logging_service.set_ui_callback(ui_callback)

def filter_logs_by_level(log_file_path: str, level: str = "ERROR") -> List[str]:
    """
    按日志级别筛选日志内容的便捷函数
    
    Args:
        log_file_path: 日志文件路径
        level: 要筛选的日志级别
        
    Returns:
        筛选后的日志行列表
    """
    return _unified_logging_service.filter_logs_by_level(log_file_path, level)

def archive_old_logs(days_old: int = 7) -> Dict[str, int]:
    """
    归档旧日志文件的便捷函数
    
    Args:
        days_old: 归档多少天前的日志文件
        
    Returns:
        归档统计信息
    """
    return _unified_logging_service.archive_old_logs(days_old)

def get_error_logs_summary(hours: int = 24) -> Dict[str, Any]:
    """
    获取最近错误日志摘要的便捷函数
    
    Args:
        hours: 获取最近多少小时的错误日志
        
    Returns:
        错误日志摘要信息
    """
    return _unified_logging_service.get_error_logs_summary(hours)

def clear_logger_cache():
    """
    清除logger缓存的便捷函数
    强制重新创建所有logger实例，在修改了logger配置后使用
    """
    _unified_logging_service.clear_logger_cache()

if __name__ == "__main__":
    # 测试统一日志服务
    log_system_info()
    
    # 测试不同类别的日志记录器
    app_logger = get_logger("TestApp", "Application")
    ocr_logger = get_logger("TestOCR", "OCR")
    system_logger = get_logger("TestSystem", "System")
    
    app_logger.info("应用程序日志测试")
    ocr_logger.info("OCR日志测试")
    system_logger.info("系统日志测试")
    
    # 输出统计信息
    stats = get_log_stats()
    # 日志统计信息通过内部日志记录