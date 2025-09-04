#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台信号处理工具类
提供外部进程发送信号的便捷方法

@author: Mr.Rey Copyright © 2025
"""

import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
import psutil
from src.ui.services.logging_service import get_logger

        time.sleep(min(timeout, 10))
        
        # 检查是否还有进程存活，强制终止
        remaining_processes = self.find_honygo_processes()
        if remaining_processes:
            self.logger.warning(f"仍有 {len(remaining_processes)} 个进程存活，强制终止")
            
            for proc_info in remaining_processes:
                pid = proc_info['pid']
                if self.send_signal_to_process(pid, signal.SIGKILL):
                    self.logger.info(f"已强制终止进程 {pid} ({proc_info['name']})")
        
        # 最终检查
        final_processes = self.find_honygo_processes()
        if not final_processes:
            self.logger.info("所有HonyGo进程已成功关闭")
            return True
        else:
            self.logger.error(f"仍有 {len(final_processes)} 个进程无法关闭")
            return False


class SignalFileMonitor:
    """信号文件监控器"""
    
    def __init__(self, signal_dir: str):
        self.signal_dir = Path(signal_dir)
        self.logger = get_logger("SignalMonitor", "System")
        self.signal_file_path = self.signal_dir / "honygo_signal.json"
        
        # 确保目录存在
        self.signal_dir.mkdir(parents=True, exist_ok=True)
    
    def create_shutdown_signal(self, reason: str = "外部关闭请求") -> bool:
        """创建关闭信号文件"""
        sender = CrossPlatformSignalSender()
        return sender.send_ipc_signal(str(self.signal_file_path), 'shutdown', reason)
    
    def create_restart_signal(self, reason: str = "外部重启请求") -> bool:
        """创建重启信号文件"""
        sender = CrossPlatformSignalSender()
        return sender.send_ipc_signal(str(self.signal_file_path), 'restart', reason)
    
    def check_signal_file(self) -> Optional[Dict[str, Any]]:
        """检查信号文件是否存在
        
        Returns:
            Dict: 信号数据，如果文件不存在返回None
        """
        try:
            if self.signal_file_path.exists():
                with open(self.signal_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"读取信号文件失败: {e}")
        
        return None
    
    def clear_signal_file(self) -> bool:
        """清理信号文件"""
        try:
            if self.signal_file_path.exists():
                self.signal_file_path.unlink()
                self.logger.debug("信号文件已清理")
            return True
        except Exception as e:
            self.logger.error(f"清理信号文件失败: {e}")
            return False


# 便捷函数
def send_shutdown_signal(signal_dir: str = None, reason: str = "外部关闭请求") -> bool:
    """发送关闭信号（便捷函数）"""
    if signal_dir is None:
        signal_dir = os.path.join(os.getcwd(), 'temp')
    
    monitor = SignalFileMonitor(signal_dir)
    return monitor.create_shutdown_signal(reason)


def send_restart_signal(signal_dir: str = None, reason: str = "外部重启请求") -> bool:
    """发送重启信号（便捷函数）"""
    if signal_dir is None:
        signal_dir = os.path.join(os.getcwd(), 'temp')
    
    monitor = SignalFileMonitor(signal_dir)
    return monitor.create_restart_signal(reason)


def shutdown_all_honygo_processes(timeout: int = 30) -> bool:
    """关闭所有HonyGo进程（便捷函数）"""
    sender = CrossPlatformSignalSender()
    return sender.shutdown_honygo_processes(timeout)


def find_honygo_processes() -> List[Dict[str, Any]]:
    """查找HonyGo进程（便捷函数）"""
    sender = CrossPlatformSignalSender()
    return sender.find_honygo_processes()