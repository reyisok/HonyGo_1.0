#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[已弃用] OCR优化系统启动脚本
整合所有优化功能，提供统一的启动和管理界面

警告: 此脚本已被弃用！
请使用新的统一启动方式:
  cd ../../../..
  python start_honygo.py

@author: Mr.Rey Copyright © 2025
"""

import argparse
import json
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict
from typing import Optional
from src.config.optimization_config_manager import OptimizationConfigManager
from src.core.ocr.monitoring.performance_dashboard import PerformanceDashboard
from src.core.ocr.monitoring.performance_monitor import PerformanceMonitor
from src.ui.services.logging_service import get_logger
# from test_ocr_performance import OCRPerformanceTester  # 模块不存在，已注释

# 获取日志记录器
logger = get_logger("OptimizedOCRSystem", "OCR")


def load_config(config_file: Optional[str] = None) -> Dict:
    """
    加载配置文件
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        配置字典
    """
    try:
        # 获取统一配置管理器
        config_manager = OptimizationConfigManager()
        config_obj = config_manager.get_config()
        
        # 将配置对象转换为字典
        if hasattr(config_obj, '__dict__'):
            default_config = config_obj.__dict__.copy()
        else:
            # 如果已经是字典，直接使用
            default_config = config_obj if isinstance(config_obj, dict) else {}
        
        # 如果指定了用户配置文件，则合并配置
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # 合并配置
                def merge_dict(default, user):
                    for key, value in user.items():
                        if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                            merge_dict(default[key], value)
                        else:
                            default[key] = value
                
                merge_dict(default_config, user_config)
                
            except Exception as e:
                logger.warning(f"加载用户配置文件失败: {e}，使用统一配置")
        
        return default_config
        
    except Exception as e:
        logger.warning(f"加载统一配置失败: {e}，使用默认配置")
        # 回退到默认配置
        return {
            'ocr_pool': {
                'host': '127.0.0.1',
                'port': 8900,
                'min_instances': 2,
                'max_instances': 8,
                'enable_cache': True,
                'enable_scaling': True
            },
            'monitoring': {
                'enabled': True,
                'interval': 5.0,
                'auto_optimize': True
            },
            'dashboard': {
                'enabled': True,
                'host': '127.0.0.1',
                'port': 8081
            },
            'run_initial_test': False
        }


class OptimizedOCRSystem:
    """
    优化的OCR系统管理器
    
    注意: 此类已被弃用，请使用新的统一启动方式
    """
    
    def __init__(self, config: Dict):
        """
        初始化OCR系统
        
        Args:
            config: 系统配置
        """
        self.config = config
        self.monitor = None
        self.dashboard = None
        self.shutdown_event = threading.Event()
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """
        信号处理器
        
        Args:
            signum: 信号编号
            frame: 帧对象
        """
        logger.info(f"接收到信号 {signum}，准备关闭系统...")
        self.shutdown_event.set()
    
    def start_system(self) -> bool:
        """
        启动系统
        
        Returns:
            启动是否成功
        """
        try:
            logger.info("[已弃用] 正在启动OCR优化系统...")
            logger.warning("警告: 此脚本已被弃用！请使用: python start_honygo.py")
            
            # 启动性能监控
            if self.config.get('monitoring', {}).get('enabled', True):
                self.monitor = PerformanceMonitor(
                    interval=self.config['monitoring'].get('interval', 5.0),
                    auto_optimize=self.config['monitoring'].get('auto_optimize', True)
                )
                self.monitor.start()
                logger.info("性能监控已启动")
            
            # 启动监控界面
            if self.config.get('dashboard', {}).get('enabled', True):
                self.dashboard = PerformanceDashboard(
                    host=self.config['dashboard'].get('host', '127.0.0.1'),
                    port=self.config['dashboard'].get('port', 8081)
                )
                self.dashboard.start()
                logger.info(f"监控界面已启动: http://{self.config['dashboard']['host']}:{self.config['dashboard']['port']}")
            
            # 运行初始测试
            if self.config.get('run_initial_test', False):
                self._run_performance_test()
            
            logger.info("OCR优化系统启动完成")
            return True
            
        except Exception as e:
            logger.error(f"系统启动失败: {e}")
            return False
    
    def _run_performance_test(self):
        """
        运行性能测试
        
        注意: OCRPerformanceTester模块不存在，此功能已禁用
        """
        try:
            logger.info("开始运行性能测试...")
            logger.warning("OCRPerformanceTester模块不存在，跳过性能测试")
            logger.info("如需性能测试功能，请使用统一启动方式: python start_honygo.py")
                
        except Exception as e:
            logger.error(f"性能测试失败: {e}")
    
    def wait_for_shutdown(self):
        """
        等待关闭信号
        """
        try:
            logger.info("系统运行中，按 Ctrl+C 退出...")
            self.shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("接收到键盘中断信号")
        
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """
        清理资源
        """
        logger.info("正在关闭系统...")
        
        # 停止监控
        if self.monitor:
            try:
                self.monitor.stop()
                logger.info("性能监控已停止")
            except Exception as e:
                logger.error(f"停止性能监控失败: {e}")
        
        # 停止界面
        if self.dashboard:
            try:
                self.dashboard.stop()
                logger.info("监控界面已停止")
            except Exception as e:
                logger.error(f"停止监控界面失败: {e}")
        
        logger.info("系统已关闭")


def main():
    """
    主函数
    
    注意: 此脚本已被弃用，请使用新的统一启动方式
    """
    logger.warning("[已弃用] 此脚本已被弃用！")
    logger.info("请使用新的统一启动方式:")
    logger.info("  cd ../../../..")
    logger.info("  python start_honygo.py")
    
    parser = argparse.ArgumentParser(description='[已弃用] OCR优化系统启动脚本')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--host', default='127.0.0.1', help='OCR池服务主机')
    parser.add_argument('--port', type=int, default=8900, help='OCR池服务端口')
    parser.add_argument('--min-instances', type=int, default=2, help='最小实例数')
    parser.add_argument('--max-instances', type=int, default=8, help='最大实例数')
    parser.add_argument('--dashboard-port', type=int, default=8081, help='监控界面端口')
    parser.add_argument('--no-monitoring', action='store_true', help='禁用性能监控')
    parser.add_argument('--no-dashboard', action='store_true', help='禁用监控界面')
    parser.add_argument('--no-cache', action='store_true', help='禁用缓存功能')
    parser.add_argument('--no-scaling', action='store_true', help='禁用自动扩容')
    parser.add_argument('--no-auto-optimize', action='store_true', help='禁用自动优化')
    parser.add_argument('--test', action='store_true', help='启动后运行性能测试')
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 应用命令行参数
    if args.host:
        config['ocr_pool']['host'] = args.host
    if args.port:
        config['ocr_pool']['port'] = args.port
    if args.min_instances:
        config['ocr_pool']['min_instances'] = args.min_instances
    if args.max_instances:
        config['ocr_pool']['max_instances'] = args.max_instances
    if args.dashboard_port:
        config['dashboard']['port'] = args.dashboard_port
    
    if args.no_monitoring:
        config['monitoring']['enabled'] = False
    if args.no_dashboard:
        config['dashboard']['enabled'] = False
    if args.no_cache:
        config['ocr_pool']['enable_cache'] = False
    if args.no_scaling:
        config['ocr_pool']['enable_scaling'] = False
    if args.no_auto_optimize:
        config['monitoring']['auto_optimize'] = False
    if args.test:
        config['run_initial_test'] = True
    
    # 创建并启动系统
    system = OptimizedOCRSystem(config)
    
    try:
        if system.start_system():
            system.wait_for_shutdown()
        else:
            logger.error("系统启动失败")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"系统运行异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()