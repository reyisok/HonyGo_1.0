#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨进程日志桥接服务
实现OCR池服务等独立进程的日志传递到主界面

@author: Mr.Rey Copyright © 2025
"""

from typing import Callable, Optional
import json
import logging
import socket
import threading
import time

# 避免循环导入，直接使用标准logging模块
















class CrossProcessLogBridge:
    """
    跨进程日志桥接服务
    
    功能：
    1. 启动TCP服务器接收其他进程的日志
    2. 将接收到的日志转发给UI回调函数
    3. 提供日志发送客户端功能
    """
    
    def __init__(self, host='127.0.0.1', port=8902):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.ui_callback: Optional[Callable[[str, str], None]] = None
        self.server_thread: Optional[threading.Thread] = None
        self.client_threads = []
        self.logger = logging.getLogger("CrossProcessLogBridge")
        
    def set_ui_callback(self, callback: Callable[[str, str], None]):
        """
        设置UI回调函数
        
        Args:
            callback: 接收日志的回调函数，参数为(level, message)
        """
        self.ui_callback = callback
        
    def start_server(self) -> bool:
        """
        启动日志桥接服务器
        
        Returns:
            bool: 启动是否成功
        """
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()
            
            self.logger.info(f"跨进程日志桥接服务器已启动: {self.host}:{self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"跨进程日志桥接服务器启动失败: {e}")
            return False
    
    def stop_server(self):
        """
        停止日志桥接服务器
        """
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        # 等待服务器线程结束
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2)
        
        # 清理客户端线程
        for thread in self.client_threads:
            if thread.is_alive():
                thread.join(timeout=1)
        
        self.logger.info("跨进程日志桥接服务器已停止")
    
    def _server_loop(self):
        """
        服务器主循环
        """
        while self.running:
            try:
                if self.server_socket:
                    client_socket, addr = self.server_socket.accept()
                    self.logger.debug(f"跨进程日志桥接新客户端连接: {addr}")
                    
                    # 为每个客户端创建处理线程
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, addr),
                        daemon=True
                    )
                    client_thread.start()
                    self.client_threads.append(client_thread)
                    
            except Exception as e:
                if self.running:  # 只在运行时报告错误
                    self.logger.error(f"跨进程日志桥接服务器循环异常: {e}")
                break
    
    def _handle_client(self, client_socket: socket.socket, addr):
        """
        处理客户端连接
        
        Args:
            client_socket: 客户端socket
            addr: 客户端地址
        """
        buffer = ""
        try:
            while self.running:
                # 接收数据
                data = client_socket.recv(4096)
                if not data:
                    break
                
                # 将接收到的数据添加到缓冲区
                buffer += data.decode('utf-8')
                
                # 按行处理消息
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():  # 跳过空行
                        try:
                            # 解析JSON格式的日志数据
                            log_data = json.loads(line)
                            level = log_data.get('level', 'INFO')
                            message = log_data.get('message', '')
                            source = log_data.get('source', 'Unknown')
                            
                            # 添加来源信息
                            formatted_message = f"[{source}] {message}"
                            
                            # 转发给UI回调
                            if self.ui_callback:
                                self.ui_callback(level, formatted_message)
                            
                        except json.JSONDecodeError as e:
                            self.logger.error(f"跨进程日志桥接JSON解析失败: {e}")
                        except Exception as e:
                            self.logger.error(f"跨进程日志桥接处理日志数据失败: {e}")
                    
        except Exception as e:
            self.logger.error(f"跨进程日志桥接客户端处理异常: {e}")
        finally:
            try:
                client_socket.close()
                self.logger.debug(f"跨进程日志桥接客户端连接关闭: {addr}")
            except:
                pass


class CrossProcessLogSender:
    """
    跨进程日志发送器
    用于其他进程向主界面发送日志
    """
    
    def __init__(self, host='127.0.0.1', port=8902, source='Unknown'):
        self.host = host
        self.port = port
        self.source = source
        self.socket: Optional[socket.socket] = None
        self.connected = False
        
    def connect(self) -> bool:
        """
        连接到日志桥接服务器
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 设置连接超时，避免长时间等待
            self.socket.settimeout(2.0)
            self.socket.connect((self.host, self.port))
            self.connected = True
            return True
        except Exception:
            # 静默处理连接失败，避免在日志桥接服务器未启动时产生大量错误信息
            self.connected = False
            return False
    
    def send_log(self, level: str, message: str) -> bool:
        """
        发送日志消息
        
        Args:
            level: 日志级别
            message: 日志消息
            
        Returns:
            bool: 发送是否成功
        """
        if not self.connected or not self.socket:
            return False
        
        try:
            log_data = {
                'level': level,
                'message': message,
                'source': self.source,
                'timestamp': time.time()
            }
            
            json_data = json.dumps(log_data, ensure_ascii=False)
            # 添加换行符作为消息分隔符
            message_with_delimiter = json_data + '\n'
            self.socket.send(message_with_delimiter.encode('utf-8'))
            return True
            
        except Exception:
            # 静默处理发送失败
            self.connected = False
            return False
    
    def disconnect(self):
        """
        断开连接
        """
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None


class CrossProcessLogHandler(logging.Handler):
    """
    跨进程日志处理器
    将日志发送到主界面进程
    """
    
    def __init__(self, host='127.0.0.1', port=8902, source='OCRPool'):
        super().__init__()
        self.sender = CrossProcessLogSender(host, port, source)
        self.connected = False
        
    def emit(self, record):
        """
        发送日志记录
        
        Args:
            record: 日志记录
        """
        try:
            # 尝试连接（如果未连接），但不要频繁重试
            if not self.connected:
                # 使用时间戳记录上次尝试时间，避免频繁重试
                current_time = time.time()
                if not hasattr(self, 'last_connect_attempt') or current_time - self.last_connect_attempt > 60:
                    self.last_connect_attempt = current_time
                    self.connected = self.sender.connect()
                    if not self.connected:
                        # 连接失败时，标记为已尝试，避免后续频繁重试
                        return
            
            if self.connected:
                message = self.format(record)
                level = record.levelname
                success = self.sender.send_log(level, message)
                if not success:
                    # 发送失败时，重置连接状态
                    self.connected = False
                
        except Exception:
            # 静默处理异常，避免影响主程序
            self.connected = False


# 全局实例
_log_bridge_server: Optional[CrossProcessLogBridge] = None


def get_log_bridge_server() -> CrossProcessLogBridge:
    """
    获取全局日志桥接服务器实例
    
    Returns:
        CrossProcessLogBridge: 日志桥接服务器实例
    """
    global _log_bridge_server
    if _log_bridge_server is None:
        _log_bridge_server = CrossProcessLogBridge()
    return _log_bridge_server


def create_cross_process_handler(source='OCRPool') -> CrossProcessLogHandler:
    """
    创建跨进程日志处理器
    
    Args:
        source: 日志来源标识
        
    Returns:
        CrossProcessLogHandler: 跨进程日志处理器
    """
    return CrossProcessLogHandler(source=source)