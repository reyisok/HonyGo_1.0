#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端口管理器
负责OCR实例的端口分配、释放和管理

@author: Mr.Rey Copyright © 2025
"""

from typing import (
    Dict,
    List,
    Optional,
    Set
)
import socket
import threading
import time

from dataclasses import dataclass

from src.ui.services.logging_service import get_logger
















@dataclass
class PortInfo:
    """端口信息"""
    port: int
    instance_id: str
    allocated_time: float
    is_active: bool = True


class PortManager:
    """端口管理器"""
    
    def __init__(self, port_range_start: int = 8901, port_range_end: int = 8920, reserved_ports: List[int] = None):
        """
        初始化端口管理器
        
        Args:
            port_range_start: 端口范围起始
            port_range_end: 端口范围结束
            reserved_ports: 保留端口列表
        """
        self.logger = get_logger("PortManager", "System")
        self.port_range_start = port_range_start
        self.port_range_end = port_range_end
        self.reserved_ports = set(reserved_ports or [8900])  # 默认保留主服务端口8900
        
        # 端口分配状态
        self.allocated_ports: Dict[int, PortInfo] = {}
        self.available_ports: Set[int] = set()
        
        # 线程安全锁
        self._lock = threading.RLock()
        
        # 初始化可用端口
        self._initialize_available_ports()
        
        self.logger.info(f"端口管理器初始化完成，端口范围: {port_range_start}-{port_range_end}, 保留端口: {list(self.reserved_ports)}")
    
    def _initialize_available_ports(self):
        """初始化可用端口列表"""
        with self._lock:
            for port in range(self.port_range_start, self.port_range_end + 1):
                if port not in self.reserved_ports:
                    self.available_ports.add(port)
            
            self.logger.info(f"初始化可用端口数量: {len(self.available_ports)}")
    
    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                return result != 0  # 连接失败表示端口可用
        except Exception as e:
            self.logger.warning(f"检查端口 {port} 可用性时发生异常: {e}")
            return False
    
    def allocate_port(self, instance_id: str) -> Optional[int]:
        """分配端口给实例"""
        with self._lock:
            if not self.available_ports:
                self.logger.error("没有可用端口")
                return None
            
            # 按顺序尝试分配端口
            for port in sorted(self.available_ports):
                if self._is_port_available(port):
                    # 分配端口
                    port_info = PortInfo(
                        port=port,
                        instance_id=instance_id,
                        allocated_time=time.time()
                    )
                    
                    self.allocated_ports[port] = port_info
                    self.available_ports.remove(port)
                    
                    self.logger.info(f"为实例 {instance_id} 分配端口 {port}")
                    return port
                else:
                    self.logger.warning(f"端口 {port} 被占用，尝试下一个端口")
            
            self.logger.error("所有可用端口都被占用")
            return None
    
    def release_port(self, port: int) -> bool:
        """释放端口"""
        with self._lock:
            if port not in self.allocated_ports:
                self.logger.warning(f"尝试释放未分配的端口: {port}")
                return False
            
            port_info = self.allocated_ports.pop(port)
            self.available_ports.add(port)
            
            self.logger.info(f"释放端口 {port}，原实例ID: {port_info.instance_id}")
            return True
    
    def get_port_info(self, port: int) -> Optional[PortInfo]:
        """获取端口信息"""
        with self._lock:
            return self.allocated_ports.get(port)
    
    def get_instance_port(self, instance_id: str) -> Optional[int]:
        """根据实例ID获取端口"""
        with self._lock:
            for port, port_info in self.allocated_ports.items():
                if port_info.instance_id == instance_id:
                    return port
            return None
    
    def get_allocated_ports(self) -> Dict[int, PortInfo]:
        """获取所有已分配端口信息"""
        with self._lock:
            return self.allocated_ports.copy()
    
    def get_available_ports(self) -> Set[int]:
        """获取所有可用端口"""
        with self._lock:
            return self.available_ports.copy()
    
    def get_status(self) -> Dict:
        """获取端口管理器状态"""
        with self._lock:
            return {
                "port_range": f"{self.port_range_start}-{self.port_range_end}",
                "reserved_ports": list(self.reserved_ports),
                "total_ports": self.port_range_end - self.port_range_start + 1 - len(self.reserved_ports),
                "allocated_count": len(self.allocated_ports),
                "available_count": len(self.available_ports),
                "allocated_ports": {
                    port: {
                        "instance_id": info.instance_id,
                        "allocated_time": info.allocated_time,
                        "is_active": info.is_active
                    } for port, info in self.allocated_ports.items()
                },
                "available_ports": list(self.available_ports)
            }
    
    def cleanup_inactive_ports(self) -> int:
        """清理非活跃端口"""
        cleaned_count = 0
        current_time = time.time()
        
        with self._lock:
            ports_to_clean = []
            
            for port, port_info in self.allocated_ports.items():
                # 检查端口是否仍在使用
                if not self._is_port_available(port):  # 端口被占用表示仍在使用
                    port_info.is_active = True
                else:
                    # 端口空闲超过5分钟则标记为非活跃
                    if current_time - port_info.allocated_time > 300:
                        port_info.is_active = False
                        ports_to_clean.append(port)
            
            # 清理非活跃端口
            for port in ports_to_clean:
                if self.release_port(port):
                    cleaned_count += 1
                    self.logger.info(f"清理非活跃端口: {port}")
        
        if cleaned_count > 0:
            self.logger.info(f"清理了 {cleaned_count} 个非活跃端口")
        
        return cleaned_count


# 全局端口管理器实例
_port_manager_instance = None
_port_manager_lock = threading.Lock()


def get_port_manager() -> PortManager:
    """获取全局端口管理器实例"""
    global _port_manager_instance
    
    if _port_manager_instance is None:
        with _port_manager_lock:
            if _port_manager_instance is None:
                _port_manager_instance = PortManager()
    
    return _port_manager_instance


def reset_port_manager():
    """重置端口管理器（主要用于测试）"""
    global _port_manager_instance
    
    with _port_manager_lock:
        _port_manager_instance = None