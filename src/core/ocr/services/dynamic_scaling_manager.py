#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR实例池动态扩容管理器
负责监控系统负载并自动调整OCR实例数量
"""

import signal
import sys
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
import psutil
from src.config.ocr_logging_config import OCRLoggerMixin
from src.config.ocr_logging_config import log_ocr_operation
from src.config.ocr_pool_validator import config_consistency_checker
from src.config.ocr_pool_validator import parameter_validator
from src.core.ocr.services.ocr_pool_manager import get_pool_manager
from src.ui.services.logging_service import get_logger

# 获取日志记录器
logger = get_logger("DynamicScalingManager", "OCR")

def signal_handler(sig, frame):
    logger.info("正在关闭动态扩容管理器...")
    shutdown_scaling_manager()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# 启动动态扩容管理器
manager = get_scaling_manager()
manager.start_monitoring()

logger.info("动态扩容管理器已启动，按 Ctrl+C 退出")

try:
    while True:
        time.sleep(60)
        status = manager.get_scaling_status()
        logger.info(f"当前状态: {status['current_metrics']}")
except KeyboardInterrupt:
    pass
finally:
    shutdown_scaling_manager()