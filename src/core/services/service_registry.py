#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务自动注册器

自动发现和注册系统中的所有服务，建立服务依赖关系，
确保服务按正确顺序初始化和启动。

@author: Mr.Rey Copyright © 2025
"""

import importlib
import inspect
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional
from typing import Type
from src.core.services.system_manager_service import ServiceInfo
from src.core.services.system_manager_service import ServicePriority
from src.core.services.system_manager_service import SystemManagerService
from src.core.services.system_manager_service import get_system_manager_service
from src.ui.services.logging_service import get_logger


class ServiceRegistry:
    """
    服务自动注册器
    
    功能：
    - 自动发现服务模块
    - 解析服务依赖关系
    - 注册服务到系统管理器
    - 验证服务配置
    """
    
    def __init__(self):
        self.logger = get_logger("ServiceRegistry", "System")
        self.system_manager = get_system_manager_service()
        
        # 获取项目根目录
        import os
        project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
        if project_root_env:
            project_root = Path(project_root_env)
        else:
            # 备用方案：从当前文件路径计算
            project_root = Path(__file__).parent.parent.parent.parent
        
        # 服务发现配置
        self.service_directories = [
            project_root / "src" / "core" / "services",  # core/services
            project_root / "src" / "ui" / "services"  # ui/services
        ]
        
        # 服务配置映射
        self.service_configs = {
            # 核心服务配置
            "UnifiedLoggingService": {
                "priority": ServicePriority.CRITICAL,
                "dependencies": []
            },
            "ProcessMonitorService": {
                "priority": ServicePriority.NORMAL,
                "dependencies": ["UnifiedLoggingService", "UnifiedConfigService"]
            },
            "SignalHandlerService": {
                "priority": ServicePriority.HIGH,
                "dependencies": ["UnifiedLoggingService"]
            },
            "SystemManagerService": {
                "priority": ServicePriority.CRITICAL,
                "dependencies": []
            },
            "UnifiedConfigService": {
                "priority": ServicePriority.CRITICAL,
                "dependencies": ["UnifiedLoggingService"]
            },
            "IntelligentAlertService": {
                "priority": ServicePriority.NORMAL,
                "dependencies": ["UnifiedLoggingService", "UnifiedConfigService"]
            },
            "TaskExecutionMonitorService": {
                "priority": ServicePriority.NORMAL,
                "dependencies": ["UnifiedLoggingService", "UnifiedConfigService"]
            },
            
            # UI服务配置
            "UnifiedTimerService": {
                "priority": ServicePriority.HIGH,
                "dependencies": ["UnifiedLoggingService"]
            },
            "SmartClickService": {
                "priority": ServicePriority.LOW,
                "dependencies": ["UnifiedLoggingService", "UnifiedConfigService"]
            },
            "LightweightTaskExecutionService": {
                "priority": ServicePriority.NORMAL,
                "dependencies": ["UnifiedLoggingService", "UnifiedConfigService"]
            },
            "UIService": {
                "priority": ServicePriority.LOW,
                "dependencies": ["UnifiedLoggingService", "UnifiedConfigService"]
            }
        }
        
        # 排除的服务（已移除或不需要注册的）
        self.excluded_services = {
            "SupervisorManagerService",  # 已移除
            "ConfigService",  # 重复服务，使用UnifiedConfigService
            "TaskExecutionService"  # 重复服务，使用LightweightTaskExecutionService
        }
    
    def discover_services(self) -> Dict[str, Any]:
        """
        自动发现所有服务模块
        
        Returns:
            Dict[str, Any]: 发现的服务类映射
        """
        discovered_services = {}
        
        for service_dir in self.service_directories:
            if not service_dir.exists():
                self.logger.warning(f"服务目录不存在: {service_dir}")
                continue
                
            self.logger.info(f"扫描服务目录: {service_dir}")
            
            # 扫描Python文件
            for py_file in service_dir.glob("*_service.py"):
                if py_file.name.startswith("__"):
                    continue
                    
                try:
                    service_classes = self._load_service_from_file(py_file)
                    discovered_services.update(service_classes)
                except Exception as e:
                    self.logger.error(f"加载服务文件失败 {py_file}: {e}")
        
        self.logger.info(f"发现 {len(discovered_services)} 个服务类")
        return discovered_services
    
    def _load_service_from_file(self, py_file: Path) -> Dict[str, Any]:
        """
        从Python文件中加载服务类
        
        Args:
            py_file: Python文件路径
            
        Returns:
            Dict[str, Any]: 服务类映射
        """
        services = {}
        
        # 构建模块名
        py_file_str = str(py_file).replace('\\', '/')
        if "core/services" in py_file_str:
            module_name = f"src.core.services.{py_file.stem}"
        elif "ui/services" in py_file_str:
            module_name = f"src.ui.services.{py_file.stem}"
        else:
            self.logger.warning(f"未知服务目录: {py_file}")
            return services
        
        try:
            # 动态导入模块
            module = importlib.import_module(module_name)
            
            # 查找服务类
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # 检查是否是服务类（以Service结尾且不在排除列表中）
                if (name.endswith("Service") and 
                    name not in self.excluded_services and
                    obj.__module__ == module_name):
                    
                    services[name] = obj
                    self.logger.debug(f"发现服务类: {name} 来自 {module_name}")
        
        except Exception as e:
            self.logger.error(f"导入模块失败 {module_name}: {e}")
        
        return services
    
    def register_all_services(self) -> bool:
        """
        注册所有发现的服务
        
        Returns:
            bool: 注册是否成功
        """
        try:
            self.logger.info("开始自动注册服务...")
            
            # 发现服务
            discovered_services = self.discover_services()
            
            if not discovered_services:
                self.logger.warning("未发现任何服务")
                return True
            
            # 注册服务
            registered_count = 0
            for service_name, service_class in discovered_services.items():
                if self._register_single_service(service_name, service_class):
                    registered_count += 1
            
            self.logger.info(f"服务注册完成，成功注册 {registered_count}/{len(discovered_services)} 个服务")
            return registered_count > 0
            
        except Exception as e:
            self.logger.error(f"服务注册失败: {e}")
            return False
    
    def _register_single_service(self, service_name: str, service_class: Type) -> bool:
        """
        注册单个服务
        
        Args:
            service_name: 服务名称
            service_class: 服务类
            
        Returns:
            bool: 注册是否成功
        """
        try:
            # 获取服务配置
            config = self.service_configs.get(service_name, {})
            priority = config.get("priority", ServicePriority.NORMAL)
            dependencies = config.get("dependencies", [])
            
            # 获取服务实例
            service_instance = self._get_service_instance(service_name, service_class)
            if not service_instance:
                self.logger.error(f"无法获取服务实例: {service_name}")
                return False
            
            # 创建服务信息
            service_info = ServiceInfo(
                name=service_name,
                service_instance=service_instance,
                priority=priority,
                dependencies=dependencies
            )
            
            # 注册到系统管理器
            if self.system_manager.register_service(service_info):
                self.logger.info(f"服务注册成功: {service_name} (优先级: {priority.name})")
                return True
            else:
                self.logger.error(f"服务注册失败: {service_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"注册服务 {service_name} 时发生异常: {e}")
            return False
    
    def _get_service_instance(self, service_name: str, service_class: Type) -> Optional[Any]:
        """
        获取服务实例
        
        Args:
            service_name: 服务名称
            service_class: 服务类
            
        Returns:
            Optional[Any]: 服务实例
        """
        try:
            # 特殊处理某些服务
            if service_name == "AsyncOCRService":
                # AsyncOCRService已修复QTimer主线程问题，可以正常初始化
                from src.core.ocr.async_ocr_service import AsyncOCRService
                from src.core.ocr.easyocr_service import EasyOCRService
                
                # 创建EasyOCR服务实例
                easyocr_service = EasyOCRService()
                
                # 根据优化配置启用或禁用GPU
                optimization_config = self._get_optimization_config()
                if optimization_config and not optimization_config.get('gpu_acceleration', {}).get('enabled', True):
                    easyocr_service.disable_gpu()
                
                instance = AsyncOCRService(easyocr_service)
                self.logger.info(f"异步OCR服务已创建: {service_name}")
                return instance
            
            if service_name == "CoordinateService":
                # CoordinateService需要QApplication实例，延迟初始化
                self.logger.warning(f"跳过服务 {service_name}：需要QApplication实例，延迟初始化")
                return None
            
            if service_name == "IntelligentDetectionService":
                # IntelligentDetectionService已修复QTimer主线程问题，可以正常初始化
                from src.ui.services.intelligent_detection_service import IntelligentDetectionService
                instance = IntelligentDetectionService()
                self.logger.info(f"智能检测服务已创建: {service_name}")
                return instance
            
            # 跳过依赖CoordinateService的服务，避免过早初始化
            coordinate_dependent_services = [
                "SimulationTaskService", "ImageReferenceService", "PreciseImageReferenceService",
                "LightweightTaskExecutionService", "SmartClickService"
            ]
            if service_name in coordinate_dependent_services:
                self.logger.warning(f"跳过服务 {service_name}：依赖CoordinateService，延迟初始化")
                return None
            
            # 尝试获取现有实例的方法
            get_method_names = [
                f'get_{service_name.lower()}',
                f'get_{service_name.lower()}_service',
                'get_instance'
            ]
            
            for method_name in get_method_names:
                if hasattr(service_class, method_name):
                    get_method = getattr(service_class, method_name)
                    if callable(get_method):
                        return get_method()
            
            # 尝试使用全局获取函数（如果存在）
            module = inspect.getmodule(service_class)
            if module:
                # 尝试常见的获取函数名称模式
                get_function_names = [
                    f'get_{service_name.lower()}',
                    f'get_{service_name.lower()}_service',
                    f'get_{service_name.replace("Service", "").lower()}_service'
                ]
                
                for func_name in get_function_names:
                    if hasattr(module, func_name):
                        get_func = getattr(module, func_name)
                        if callable(get_func):
                            return get_func()
            
            # 尝试直接实例化（无参数）
            return service_class()
            
        except Exception as e:
            self.logger.error(f"获取服务实例失败 {service_name}: {e}")
            return None
    
    def validate_service_dependencies(self) -> bool:
        """
        验证服务依赖关系
        
        Returns:
            bool: 依赖关系是否有效
        """
        try:
            self.logger.info("验证服务依赖关系...")
            
            all_services = set(self.system_manager.list_services())
            validation_errors = []
            
            for service_name in all_services:
                service_info = self.system_manager.services.get(service_name)
                if service_info and service_info.dependencies:
                    for dep in service_info.dependencies:
                        if dep not in all_services:
                            error_msg = f"服务 {service_name} 依赖的服务 {dep} 未注册"
                            validation_errors.append(error_msg)
                            self.logger.error(error_msg)
            
            if validation_errors:
                self.logger.error(f"发现 {len(validation_errors)} 个依赖关系错误")
                return False
            else:
                self.logger.info("服务依赖关系验证通过")
                return True
                
        except Exception as e:
            self.logger.error(f"验证服务依赖关系失败: {e}")
            return False


# 全局服务注册器实例
_service_registry = None


def get_service_registry() -> ServiceRegistry:
    """
    获取全局服务注册器实例
    
    Returns:
        ServiceRegistry: 服务注册器实例
    """
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
    return _service_registry


def auto_register_all_services() -> bool:
    """
    自动注册所有服务的便捷函数
    
    Returns:
        bool: 注册是否成功
    """
    registry = get_service_registry()
    if registry.register_all_services():
        return registry.validate_service_dependencies()
    return False