# -*- coding: utf-8 -*-
"""
OCR池参数验证器
在关键调用点添加参数一致性检查，确保配置参数的有效性

@author: Mr.Rey Copyright © 2025
@created: 2025-01-23 10:45:00
@modified: 2025-01-23 10:45:00
@version: 1.0.0
"""

from typing import Any, Callable, Dict
import functools

from src.config.ocr_pool_config import OCRPoolConfig, get_ocr_pool_config
from src.ui.services.logging_service import get_logger
















class OCRPoolValidator:
    """OCR池参数验证器"""
    
    def __init__(self):
        self.logger = get_logger("OCRPoolValidator", "Application")
    
    def validate_config(self, config: OCRPoolConfig) -> bool:
        """验证OCR池配置
        
        Args:
            config: OCR池配置对象
            
        Returns:
            bool: 验证是否通过
            
        Raises:
            ValueError: 配置参数无效时抛出异常
        """
        try:
            # 调用配置对象的验证方法
            config.validate()
            
            # 额外的业务逻辑验证
            self._validate_business_rules(config)
            
            self.logger.info("OCR池配置验证通过")
            return True
            
        except ValueError as e:
            self.logger.error(f"OCR池配置验证失败: {e}")
            raise
        except Exception as e:
            self.logger.error(f"OCR池配置验证过程中发生未知错误: {e}")
            raise ValueError(f"配置验证失败: {e}")
    
    def _validate_business_rules(self, config: OCRPoolConfig) -> None:
        """验证业务规则
        
        Args:
            config: OCR池配置对象
            
        Raises:
            ValueError: 业务规则验证失败时抛出异常
        """
        # 检查实例数量的合理性
        if config.max_instances > 20:
            self.logger.warning(f"最大实例数 {config.max_instances} 可能过大，建议不超过20")
        
        if config.min_instances > config.max_instances // 2:
            self.logger.warning(f"最小实例数 {config.min_instances} 相对于最大实例数 {config.max_instances} 可能过大")
        
        # 检查超时配置的合理性
        if config.request_timeout > 120:
            self.logger.warning(f"请求超时时间 {config.request_timeout}s 可能过长")
        
        if config.request_timeout < 5:
            raise ValueError(f"请求超时时间 {config.request_timeout}s 过短，建议至少5秒")
        
        # 检查资源配置的合理性
        if config.max_memory_per_instance > 2048:
            self.logger.warning(f"单实例最大内存 {config.max_memory_per_instance}MB 可能过大")
        
        if config.max_memory_per_instance < 256:
            raise ValueError(f"单实例最大内存 {config.max_memory_per_instance}MB 过小，建议至少256MB")
    
    def validate_runtime_parameters(self, **kwargs) -> Dict[str, Any]:
        """验证运行时参数
        
        Args:
            **kwargs: 运行时参数
            
        Returns:
            Dict[str, Any]: 验证后的参数字典
            
        Raises:
            ValueError: 参数验证失败时抛出异常
        """
        validated_params = {}
        
        # 验证实例数量参数
        if 'min_instances' in kwargs:
            min_instances = kwargs['min_instances']
            if not isinstance(min_instances, int) or min_instances <= 0:
                raise ValueError(f"min_instances必须是正整数，当前值: {min_instances}")
            validated_params['min_instances'] = min_instances
        
        if 'max_instances' in kwargs:
            max_instances = kwargs['max_instances']
            if not isinstance(max_instances, int) or max_instances <= 0:
                raise ValueError(f"max_instances必须是正整数，当前值: {max_instances}")
            validated_params['max_instances'] = max_instances
        
        # 验证实例数量关系
        if 'min_instances' in validated_params and 'max_instances' in validated_params:
            if validated_params['min_instances'] > validated_params['max_instances']:
                raise ValueError(f"min_instances({validated_params['min_instances']}) 不能大于 max_instances({validated_params['max_instances']})")
        
        # 验证端口参数
        if 'port' in kwargs:
            port = kwargs['port']
            if not isinstance(port, int) or port <= 0 or port > 65535:
                raise ValueError(f"port必须是1-65535之间的整数，当前值: {port}")
            validated_params['port'] = port
        
        # 验证主机参数
        if 'host' in kwargs:
            host = kwargs['host']
            if not isinstance(host, str) or not host.strip():
                raise ValueError(f"host必须是非空字符串，当前值: {host}")
            validated_params['host'] = host.strip()
        
        self.logger.debug(f"运行时参数验证通过: {validated_params}")
        return validated_params


# 全局验证器实例
_validator = OCRPoolValidator()


def validate_ocr_pool_config(config: OCRPoolConfig) -> bool:
    """验证OCR池配置
    
    Args:
        config: OCR池配置对象
        
    Returns:
        bool: 验证是否通过
    """
    return _validator.validate_config(config)


def validate_runtime_parameters(**kwargs) -> Dict[str, Any]:
    """验证运行时参数
    
    Args:
        **kwargs: 运行时参数
        
    Returns:
        Dict[str, Any]: 验证后的参数字典
    """
    return _validator.validate_runtime_parameters(**kwargs)


def parameter_validator(func: Callable) -> Callable:
    """参数验证装饰器
    
    用于在函数调用前验证OCR池相关参数
    
    Args:
        func: 被装饰的函数
        
    Returns:
        Callable: 装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # 提取OCR池相关参数进行验证
            ocr_params = {}
            for key in ['min_instances', 'max_instances', 'host', 'port']:
                if key in kwargs:
                    ocr_params[key] = kwargs[key]
            
            if ocr_params:
                validated_params = validate_runtime_parameters(**ocr_params)
                # 更新kwargs中的参数
                kwargs.update(validated_params)
            
            # 验证参数类型和范围
            if 'image_data' in kwargs:
                if not kwargs['image_data']:
                    raise ValueError("图像数据不能为空")
            
            if 'request_type' in kwargs:
                valid_types = ['recognize', 'batch', 'optimize']
                if kwargs['request_type'] not in valid_types:
                    raise ValueError(f"无效的请求类型: {kwargs['request_type']}")
            
            return func(*args, **kwargs)
            
        except ValueError as e:
            logger = get_logger(func.__module__, "Application")
            logger.error(f"函数 {func.__name__} 参数验证失败: {e}")
            raise
        except Exception as e:
            logger = get_logger(func.__module__, "Application")
            logger.error(f"函数 {func.__name__} 执行过程中发生错误: {e}")
            raise
    
    return wrapper


def config_consistency_checker(func: Callable) -> Callable:
    """配置一致性检查装饰器
    
    用于检查函数调用时的配置是否与全局配置一致
    
    Args:
        func: 被装饰的函数
        
    Returns:
        Callable: 装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # 获取全局配置
            global_config = get_ocr_pool_config()
            
            # 检查参数与全局配置的一致性
            inconsistencies = []
            
            if 'min_instances' in kwargs and kwargs['min_instances'] != global_config.min_instances:
                inconsistencies.append(f"min_instances: 传入值{kwargs['min_instances']} != 全局配置{global_config.min_instances}")
            
            if 'max_instances' in kwargs and kwargs['max_instances'] != global_config.max_instances:
                inconsistencies.append(f"max_instances: 传入值{kwargs['max_instances']} != 全局配置{global_config.max_instances}")
            
            if 'host' in kwargs and kwargs['host'] != global_config.host:
                inconsistencies.append(f"host: 传入值{kwargs['host']} != 全局配置{global_config.host}")
            
            if 'port' in kwargs and kwargs['port'] != global_config.port:
                inconsistencies.append(f"port: 传入值{kwargs['port']} != 全局配置{global_config.port}")
            
            if inconsistencies:
                logger = get_logger(func.__module__, "Application")
                logger.warning(f"函数 {func.__name__} 参数与全局配置不一致: {'; '.join(inconsistencies)}")
            
            return func(*args, **kwargs)
            
        except Exception as e:
            logger = get_logger(func.__module__, "Application")
            logger.error(f"函数 {func.__name__} 配置一致性检查失败: {e}")
            raise
    
    return wrapper