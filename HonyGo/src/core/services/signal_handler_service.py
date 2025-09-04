#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一信号处理服务
使用signal模块捕获退出信号，实现程序的优雅关闭

@author: Mr.Rey Copyright © 2025
"""

from datetime import datetime
from typing import Callable, List, Optional
import json
import os
import sys
import threading
import time

import platform
import queue
import signal
import win32api
import win32con

from src.ui.services.logging_service import get_logger















# 信号处理优先级常量
SIGNAL_PRIORITIES = {
    'critical': 0,    # 关键服务（数据库、日志）
    'high': 1,        # 重要服务（OCR池、UI）
    'medium': 2,      # 一般服务（监控、定时器）
    'low': 3          # 辅助服务（缓存、临时文件）
}

# 跨平台进程间通信配置
IPC_CONFIG = {
    'pipe_name': 'honygo_signal_pipe',
    'signal_file': 'honygo_signal.json',
    'check_interval': 0.5  # 检查间隔（秒）
}


class SignalHandlerService:
    """统一信号处理服务"""
    
    def __init__(self):
        self.logger = get_logger("SignalHandler", "System")
        self._shutdown_callbacks: List[tuple] = []  # (priority_level, priority_value, callback)
        self._emergency_callbacks: List[Callable[[], None]] = []
        self._is_shutting_down = False
        self._shutdown_timeout = 30  # 关闭超时时间（秒）
        self._lock = threading.RLock()
        self._platform = platform.system().lower()
        
        # 跨平台进程间通信
        self._ipc_enabled = False
        self._ipc_thread = None
        self._ipc_queue = queue.Queue()
        self._signal_file_path = None
        self._pipe_handle = None
        
        # 支持的信号
        self._supported_signals = {
            signal.SIGINT: "SIGINT (Ctrl+C)",
            signal.SIGTERM: "SIGTERM (终止信号)",
        }
        
        # 平台特定信号
        if sys.platform == "win32":
            self._supported_signals[signal.SIGBREAK] = "SIGBREAK (Ctrl+Break)"
            # Windows控制台事件处理
            self._setup_windows_console_handler()
        else:
            # Unix/Linux特有信号
            self._supported_signals[signal.SIGHUP] = "SIGHUP (挂起信号)"
            self._supported_signals[signal.SIGQUIT] = "SIGQUIT (退出信号)"
            self._supported_signals[signal.SIGUSR1] = "SIGUSR1 (用户信号1)"
            self._supported_signals[signal.SIGUSR2] = "SIGUSR2 (用户信号2)"
        
        self.logger.info(f"信号处理服务初始化完成 (平台: {self._platform})")
    
    def _setup_windows_console_handler(self):
        """设置Windows控制台事件处理器"""
        if sys.platform != "win32":
            return
        
        try:
            # 设置控制台控制处理器
            def console_ctrl_handler(ctrl_type):
                if ctrl_type == win32con.CTRL_C_EVENT:
                    self.logger.info("接收到Windows Ctrl+C事件")
                    self._perform_shutdown("Windows Ctrl+C事件")
                    return True
                elif ctrl_type == win32con.CTRL_BREAK_EVENT:
                    self.logger.info("接收到Windows Ctrl+Break事件")
                    self._perform_shutdown("Windows Ctrl+Break事件")
                    return True
                elif ctrl_type == win32con.CTRL_CLOSE_EVENT:
                    self.logger.info("接收到Windows控制台关闭事件")
                    self._perform_shutdown("Windows控制台关闭事件")
                    return True
                elif ctrl_type == win32con.CTRL_LOGOFF_EVENT:
                    self.logger.info("接收到Windows注销事件")
                    self._perform_shutdown("Windows注销事件")
                    return True
                elif ctrl_type == win32con.CTRL_SHUTDOWN_EVENT:
                    self.logger.info("接收到Windows关机事件")
                    self._perform_shutdown("Windows关机事件")
                    return True
                return False
            
            win32api.SetConsoleCtrlHandler(console_ctrl_handler, True)
            self.logger.debug("Windows控制台事件处理器设置成功")
        except Exception as e:
            self.logger.warning(f"设置Windows控制台事件处理器失败: {e}")
    
    def enable_ipc(self, signal_dir: str = None):
        """启用跨平台进程间通信"""
        try:
            if signal_dir is None:
                signal_dir = os.path.join(os.getcwd(), 'temp')
            
            os.makedirs(signal_dir, exist_ok=True)
            self._signal_file_path = os.path.join(signal_dir, IPC_CONFIG['signal_file'])
            
            # 启动IPC监听线程
            self._ipc_thread = threading.Thread(target=self._ipc_listener, daemon=True)
            self._ipc_thread.start()
            self._ipc_enabled = True
            
            self.logger.info(f"跨平台进程间通信已启用 (信号文件: {self._signal_file_path})")
        except Exception as e:
            self.logger.error(f"启用跨平台进程间通信失败: {e}")
    
    def _ipc_listener(self):
        """IPC监听线程"""
        while not self._is_shutting_down:
            try:
                # 检查信号文件
                if self._signal_file_path and os.path.exists(self._signal_file_path):
                    with open(self._signal_file_path, 'r', encoding='utf-8') as f:
                        signal_data = json.load(f)
                    
                    # 处理信号
                    signal_type = signal_data.get('type', 'unknown')
                    signal_reason = signal_data.get('reason', '外部信号')
                    
                    self.logger.info(f"接收到IPC信号: {signal_type} - {signal_reason}")
                    
                    # 删除信号文件
                    os.remove(self._signal_file_path)
                    
                    # 触发关闭
                    if signal_type in ['shutdown', 'terminate']:
                        self._perform_shutdown(f"IPC信号: {signal_reason}")
                        break
                
                time.sleep(IPC_CONFIG['check_interval'])
            except Exception as e:
                if not self._is_shutting_down:
                    self.logger.error(f"IPC监听器错误: {e}")
                time.sleep(IPC_CONFIG['check_interval'])
    
    def send_ipc_signal(self, signal_type: str, reason: str = "外部触发"):
        """发送IPC信号"""
        if not self._signal_file_path:
            self.logger.warning("IPC未启用，无法发送信号")
            return False
        
        try:
            signal_data = {
                'type': signal_type,
                'reason': reason,
                'timestamp': datetime.now().isoformat(),
                'platform': self._platform
            }
            
            with open(self._signal_file_path, 'w', encoding='utf-8') as f:
                json.dump(signal_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"IPC信号已发送: {signal_type} - {reason}")
            return True
        except Exception as e:
            self.logger.error(f"发送IPC信号失败: {e}")
            return False
    
    def initialize(self):
        """初始化信号处理器"""
        try:
            # 注册信号处理器
            for sig, name in self._supported_signals.items():
                try:
                    signal.signal(sig, self._signal_handler)
                    self.logger.debug(f"已注册信号处理器: {name}")
                except (OSError, ValueError) as e:
                    self.logger.warning(f"无法注册信号处理器 {name}: {e}")
            
            self.logger.info("信号处理服务初始化成功")
        except Exception as e:
            self.logger.error(f"信号处理服务初始化失败: {e}")
            raise
    
    def add_shutdown_callback(self, callback: Callable[[], None], priority: str = 'medium', priority_value: int = None):
        """添加关闭回调函数
        
        Args:
            callback: 回调函数
            priority: 优先级级别 ('critical', 'high', 'medium', 'low')
            priority_value: 自定义优先级数值（可选，数字越小优先级越高）
        """
        # 验证优先级级别
        if priority not in SIGNAL_PRIORITIES:
            self.logger.warning(f"无效的优先级级别: {priority}，使用默认值 'medium'")
            priority = 'medium'
        
        # 确定优先级数值
        if priority_value is None:
            priority_value = SIGNAL_PRIORITIES[priority]
        
        with self._lock:
            self._shutdown_callbacks.append((priority, priority_value, callback))
            # 按优先级排序（数字越小优先级越高）
            self._shutdown_callbacks.sort(key=lambda x: x[1])
        
        self.logger.info(f"已添加关闭回调函数: {callback.__name__} (级别: {priority}, 数值: {priority_value})")
    
    def add_emergency_callback(self, callback: Callable[[], None]):
        """添加紧急关闭回调函数（用于强制关闭时的清理）"""
        with self._lock:
            self._emergency_callbacks.append(callback)
        
        self.logger.info(f"已添加紧急关闭回调函数: {callback.__name__}")
    
    def remove_shutdown_callback(self, callback: Callable[[], None]):
        """移除关闭回调函数"""
        with self._lock:
            self._shutdown_callbacks = [
                (priority_level, priority_value, cb) for priority_level, priority_value, cb in self._shutdown_callbacks 
                if cb != callback
            ]
        
        self.logger.info(f"已移除关闭回调函数: {callback.__name__}")
    
    def is_shutting_down(self) -> bool:
        """检查是否正在关闭"""
        return self._is_shutting_down
    
    def set_shutdown_timeout(self, timeout: int):
        """设置关闭超时时间"""
        self._shutdown_timeout = timeout
        self.logger.info(f"关闭超时时间设置为: {timeout}秒")
    
    def trigger_shutdown(self, reason: str = "手动触发"):
        """手动触发关闭流程"""
        self.logger.info(f"手动触发关闭流程: {reason}")
        self._perform_shutdown(reason)
    
    def _signal_handler(self, signum: int, frame):
        """信号处理器"""
        signal_name = self._supported_signals.get(signum, f"信号{signum}")
        self.logger.info(f"接收到信号: {signal_name}")
        
        # 避免重复处理
        if self._is_shutting_down:
            self.logger.warning(f"正在关闭中，忽略信号: {signal_name}")
            return
        
        # 启动关闭流程
        self._perform_shutdown(f"接收到信号: {signal_name}")
    
    def _perform_shutdown(self, reason: str):
        """执行关闭流程"""
        with self._lock:
            if self._is_shutting_down:
                return
            self._is_shutting_down = True
        
        self.logger.info(f"开始关闭流程: {reason}")
        start_time = time.time()
        
        try:
            # 执行关闭回调函数
            self._execute_shutdown_callbacks()
            
            # 检查关闭时间
            elapsed_time = time.time() - start_time
            if elapsed_time > self._shutdown_timeout:
                self.logger.warning(f"关闭流程超时 ({elapsed_time:.1f}秒)，执行紧急关闭")
                self._execute_emergency_callbacks()
            else:
                self.logger.info(f"关闭流程完成，耗时: {elapsed_time:.1f}秒")
            
        except Exception as e:
            self.logger.error(f"关闭流程执行失败: {e}")
            self._execute_emergency_callbacks()
        
        finally:
            # 最终退出
            self.logger.info("程序即将退出")
            sys.exit(0)
    
    def _execute_shutdown_callbacks(self):
        """执行关闭回调函数"""
        self.logger.info(f"执行 {len(self._shutdown_callbacks)} 个关闭回调函数")
        
        for priority_level, priority_value, callback in self._shutdown_callbacks:
            try:
                callback_name = getattr(callback, '__name__', str(callback))
                self.logger.debug(f"执行关闭回调: {callback_name} (级别: {priority_level}, 数值: {priority_value})")
                
                # 设置超时
                start_time = time.time()
                callback()
                elapsed_time = time.time() - start_time
                
                if elapsed_time > 5:  # 单个回调超过5秒记录警告
                    self.logger.warning(f"关闭回调 {callback_name} 执行时间过长: {elapsed_time:.1f}秒")
                else:
                    self.logger.debug(f"关闭回调 {callback_name} 执行完成，耗时: {elapsed_time:.1f}秒")
                
            except Exception as e:
                callback_name = getattr(callback, '__name__', str(callback))
                self.logger.error(f"关闭回调 {callback_name} 执行失败: {e}")
    
    def _execute_emergency_callbacks(self):
        """执行紧急关闭回调函数"""
        if not self._emergency_callbacks:
            return
        
        self.logger.warning(f"执行 {len(self._emergency_callbacks)} 个紧急关闭回调函数")
        
        for callback in self._emergency_callbacks:
            try:
                callback_name = getattr(callback, '__name__', str(callback))
                self.logger.debug(f"执行紧急关闭回调: {callback_name}")
                callback()
            except Exception as e:
                callback_name = getattr(callback, '__name__', str(callback))
                self.logger.error(f"紧急关闭回调 {callback_name} 执行失败: {e}")
    
    def wait_for_shutdown(self):
        """等待关闭信号（阻塞当前线程）"""
        self.logger.info("等待关闭信号...")
        try:
            while not self._is_shutting_down:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.logger.info("接收到键盘中断")
            self._perform_shutdown("键盘中断")
    
    def cleanup(self):
        """清理资源"""
        try:
            # 停止IPC监听
            if self._ipc_enabled:
                self._ipc_enabled = False
                if self._ipc_thread and self._ipc_thread.is_alive():
                    self._ipc_thread.join(timeout=2)
                
                # 清理信号文件
                if self._signal_file_path and os.path.exists(self._signal_file_path):
                    try:
                        os.remove(self._signal_file_path)
                        self.logger.debug("已清理IPC信号文件")
                    except Exception as e:
                        self.logger.warning(f"清理IPC信号文件失败: {e}")
            
            with self._lock:
                self._shutdown_callbacks.clear()
                self._emergency_callbacks.clear()
            
            # 恢复默认信号处理器
            for sig in self._supported_signals.keys():
                try:
                    signal.signal(sig, signal.SIG_DFL)
                except (OSError, ValueError):
                    pass
            
            # Windows特定清理
            if sys.platform == "win32":
                try:
                    win32api.SetConsoleCtrlHandler(None, False)
                    self.logger.debug("已清理Windows控制台事件处理器")
                except Exception as e:
                    self.logger.warning(f"清理Windows控制台事件处理器失败: {e}")
            
            self.logger.info("信号处理服务清理完成")
        except Exception as e:
            self.logger.error(f"信号处理服务清理失败: {e}")


class GracefulShutdownMixin:
    """优雅关闭混入类
    
    为其他服务类提供优雅关闭功能
    """
    
    def __init__(self):
        self._shutdown_requested = False
        self._shutdown_event = threading.Event()
    
    def request_shutdown(self):
        """请求关闭"""
        self._shutdown_requested = True
        self._shutdown_event.set()
    
    def is_shutdown_requested(self) -> bool:
        """检查是否请求关闭"""
        return self._shutdown_requested
    
    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """等待关闭事件
        
        Returns:
            bool: True表示接收到关闭信号，False表示超时
        """
        return self._shutdown_event.wait(timeout)
    
    def should_continue_running(self) -> bool:
        """检查是否应该继续运行"""
        return not self._shutdown_requested


# 全局实例
_signal_handler_service = None


def get_signal_handler_service() -> SignalHandlerService:
    """获取信号处理服务实例"""
    global _signal_handler_service
    if _signal_handler_service is None:
        _signal_handler_service = SignalHandlerService()
    return _signal_handler_service


def initialize_signal_handler_service():
    """初始化信号处理服务"""
    service = get_signal_handler_service()
    service.initialize()
    return service


def register_shutdown_callback(callback: Callable[[], None], priority: str = 'medium', priority_value: int = None):
    """注册关闭回调函数（便捷函数）"""
    service = get_signal_handler_service()
    service.add_shutdown_callback(callback, priority, priority_value)


def register_emergency_callback(callback: Callable[[], None]):
    """注册紧急关闭回调函数（便捷函数）"""
    service = get_signal_handler_service()
    service.add_emergency_callback(callback)