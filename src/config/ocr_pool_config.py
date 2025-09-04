# -*- coding: utf-8 -*-
"""
OCR池参数配置文件
统一管理OCR池相关参数，避免硬编码

@author: Mr.Rey Copyright © 2025
@created: 2025-01-23 10:30:00
@modified: 2025-01-23 10:30:00
@version: 1.0.0
"""

from typing import Any, Dict
import os

from dataclasses import dataclass
















@dataclass
class OCRPoolConfig:
    """OCR池配置类"""
    # 基础配置
    min_instances: int = 2
    max_instances: int = 10
    host: str = "localhost"
    port: int = 8900
    
    # 性能配置
    request_timeout: int = 30
    pool_check_interval: int = 5
    scaling_check_interval: int = 10
    
    # 资源配置
    max_memory_per_instance: int = 512  # MB
    max_cpu_usage: float = 80.0  # %
    
    # 日志配置
    log_level: str = "INFO"
    enable_performance_logging: bool = True
    enable_debug_logging: bool = False
    
    # 优化配置
    enable_auto_scaling: bool = True
    enable_load_balancing: bool = True
    enable_health_check: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'min_instances': self.min_instances,
            'max_instances': self.max_instances,
            'host': self.host,
            'port': self.port,
            'request_timeout': self.request_timeout,
            'pool_check_interval': self.pool_check_interval,
            'scaling_check_interval': self.scaling_check_interval,
            'max_memory_per_instance': self.max_memory_per_instance,
            'max_cpu_usage': self.max_cpu_usage,
            'log_level': self.log_level,
            'enable_performance_logging': self.enable_performance_logging,
            'enable_debug_logging': self.enable_debug_logging,
            'enable_auto_scaling': self.enable_auto_scaling,
            'enable_load_balancing': self.enable_load_balancing,
            'enable_health_check': self.enable_health_check
        }
    
    def validate(self) -> bool:
        """验证配置参数的有效性"""
        if self.min_instances <= 0:
            raise ValueError("min_instances must be greater than 0")
        
        if self.max_instances <= 0:
            raise ValueError("max_instances must be greater than 0")
        
        if self.min_instances > self.max_instances:
            raise ValueError("min_instances cannot be greater than max_instances")
        
        if self.port <= 0 or self.port > 65535:
            raise ValueError("port must be between 1 and 65535")
        
        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be greater than 0")
        
        if self.max_cpu_usage <= 0 or self.max_cpu_usage > 100:
            raise ValueError("max_cpu_usage must be between 0 and 100")
        
        return True


class OCRPoolConfigManager:
    """OCR池配置管理器"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._config = self._load_config()
    
    def _load_config(self) -> OCRPoolConfig:
        """加载配置"""
        # 从环境变量读取配置（优先级最高）
        config = OCRPoolConfig()
        
        # 环境变量覆盖默认配置
        if os.getenv('OCR_POOL_MIN_INSTANCES'):
            config.min_instances = int(os.getenv('OCR_POOL_MIN_INSTANCES'))
        
        if os.getenv('OCR_POOL_MAX_INSTANCES'):
            config.max_instances = int(os.getenv('OCR_POOL_MAX_INSTANCES'))
        
        if os.getenv('OCR_POOL_HOST'):
            config.host = os.getenv('OCR_POOL_HOST')
        
        if os.getenv('OCR_POOL_PORT'):
            config.port = int(os.getenv('OCR_POOL_PORT'))
        
        if os.getenv('OCR_POOL_LOG_LEVEL'):
            config.log_level = os.getenv('OCR_POOL_LOG_LEVEL')
        
        # 验证配置
        config.validate()
        
        return config
    
    def get_config(self) -> OCRPoolConfig:
        """获取配置"""
        return self._config
    
    def reload_config(self) -> OCRPoolConfig:
        """重新加载配置"""
        self._config = self._load_config()
        return self._config
    
    def update_config(self, **kwargs) -> OCRPoolConfig:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        
        # 验证更新后的配置
        self._config.validate()
        
        return self._config


# 全局配置管理器实例
config_manager = OCRPoolConfigManager()


def get_ocr_pool_config() -> OCRPoolConfig:
    """获取OCR池配置"""
    return config_manager.get_config()


def reload_ocr_pool_config() -> OCRPoolConfig:
    """重新加载OCR池配置"""
    return config_manager.reload_config()


def update_ocr_pool_config(**kwargs) -> OCRPoolConfig:
    """更新OCR池配置"""
    return config_manager.update_config(**kwargs)