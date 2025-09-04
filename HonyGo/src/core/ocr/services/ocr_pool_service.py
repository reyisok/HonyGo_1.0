#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR实例池服务

@author: Mr.Rey Copyright © 2025
@created: 2025-01-03 18:05:00
@modified: 2025-01-03 18:05:00
@version: 1.0.0
"""

import argparse
import sys
import traceback
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
# 优先使用环境变量中的项目根目录路径
import os
project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
if project_root_env:
    project_root = Path(project_root_env)
else:
    # 备用方案：从当前文件路径计算
    project_root = Path(__file__).parent.parent.parent.parent

sys.path.insert(0, str(project_root))

from src.config.ocr_pool_config import get_ocr_pool_config
from src.core.ocr.services.ocr_pool_manager import get_pool_manager, shutdown_pool_manager
from src.ui.services.logging_service import get_logger
from src.ui.services.cross_process_log_bridge import create_cross_process_handler


def main():
    """
    OCR实例池服务主函数
    """
    logger = get_logger("OCRPoolService", "OCR")
    service = None
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='OCR实例池服务')
        parser.add_argument('--host', default='127.0.0.1', help='服务主机地址')
        parser.add_argument('--port', type=int, default=8900, help='服务端口')
        parser.add_argument('--min-instances', type=int, default=2, help='最小实例数')
        parser.add_argument('--max-instances', type=int, default=10, help='最大实例数')
        parser.add_argument('--debug', action='store_true', help='启用调试模式')
        
        args = parser.parse_args()
        
        logger.info(f"启动OCR实例池服务 - 主机: {args.host}, 端口: {args.port}")
        logger.info(f"实例配置 - 最小: {args.min_instances}, 最大: {args.max_instances}")
        
        # 创建跨进程日志桥接处理器
        log_bridge = create_cross_process_handler(source="OCRPoolService")
        
        # 将跨进程日志处理器添加到logger中
        logger.addHandler(log_bridge)
        logger.info("跨进程日志桥接处理器已添加到logger")
        
        # 获取OCR池配置
        config = get_ocr_pool_config()
        config.host = args.host
        config.port = args.port
        config.min_instances = args.min_instances
        config.max_instances = args.max_instances
        
        # 启动OCR实例池管理器
        pool_manager = get_pool_manager(config)
        logger.info("OCR实例池管理器已启动")
        
        # 启动服务
        pool_manager.start_service()
        logger.info(f"OCR实例池服务已启动，监听 {args.host}:{args.port}")
        
        # 保持服务运行
        try:
            pool_manager.wait_for_shutdown()
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在关闭服务...")
        
    except Exception as e:
        error_msg = f"OCR实例池服务启动失败: {e}"
        error_detail = f"详细错误信息: {traceback.format_exc()}"
        
        logger.error(error_msg)
        logger.error(error_detail)
        
        # 错误信息已通过统一日志服务记录
        
        return 1
    finally:
        try:
            if 'pool_manager' in locals():
                pool_manager.shutdown()
            shutdown_pool_manager()
            logger.info("OCR池服务资源清理完成")
        except Exception as e:
            logger.error(f"清理OCR池服务资源失败: {e}")
            logger.error(f"详细错误信息: {traceback.format_exc()}")
        logger.info("OCR池服务已关闭")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())