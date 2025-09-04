#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统管理协调器服务

统一管理所有系统服务的初始化、启动、停止和关闭流程，
确保服务按正确顺序启动和关闭，提供服务状态监控和健康检查。

@author: Mr.Rey Copyright © 2025
"""

from typing import (
    Any,
    Dict,
    List,
    Optional
)
import threading
import time

from enum import Enum

from src.ui.services.logging_service import get_logger
















class ServiceStatus(Enum):
    """服务状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class ServicePriority(Enum):
    """服务优先级枚举"""
    CRITICAL = 1    # 关键服务（日志、配置等）
    HIGH = 2        # 高优先级服务（信号处理、定时器等）
    NORMAL = 3      # 普通服务（进程监控、Supervisor等）
    LOW = 4         # 低优先级服务（OCR、UI等）


class ServiceInfo:
    """服务信息类"""
    
    def __init__(self, name: str, service_instance: Any, 
                 priority: ServicePriority = ServicePriority.NORMAL,
                 init_method: str = "initialize",
                 start_method: str = "start",
                 stop_method: str = "stop",
                 cleanup_method: str = "cleanup",
                 health_check_method: str = "is_healthy",
                 dependencies: List[str] = None):
        self.name = name
        self.service_instance = service_instance
        self.priority = priority
        self.init_method = init_method
        self.start_method = start_method
        self.stop_method = stop_method
        self.cleanup_method = cleanup_method
        self.health_check_method = health_check_method
        self.status = ServiceStatus.STOPPED
        self.last_error = None
        self.start_time = None
        self.dependencies = dependencies or []
        
    def has_method(self, method_name: str) -> bool:
        """检查服务是否有指定方法"""
        return hasattr(self.service_instance, method_name)
        
    def call_method(self, method_name: str, *args, **kwargs) -> Any:
        """调用服务方法"""
        if self.has_method(method_name):
            method = getattr(self.service_instance, method_name)
            return method(*args, **kwargs)
        return None


class SystemManagerService:
    """系统管理协调器服务"""
    
    def __init__(self):
        self.logger = get_logger("SystemManagerService", "System")
        
        # 服务注册表
        self.services: Dict[str, ServiceInfo] = {}
        
        # 兼容性属性：service_registry作为services的别名
        self.service_registry = self.services
        
        # 服务状态映射
        self.service_states: Dict[str, str] = {}
        
        # 系统状态
        self.is_initialized = False
        self.is_running = False
        self.initialization_lock = threading.Lock()
        
        # 服务依赖关系
        self.service_dependencies: Dict[str, List[str]] = {}
        
        # 健康检查配置
        self.health_check_enabled = True
        self.health_check_interval = 30  # 秒
        self.health_check_thread = None
        self.health_check_running = False
        
        # 统计信息
        self.stats = {
            "total_services": 0,
            "running_services": 0,
            "failed_services": 0,
            "system_uptime": 0,
            "last_health_check": None
        }
        
        self.logger.info("系统管理协调器初始化完成")
    
    def register_service(self, service_info: ServiceInfo, dependencies: List[str] = None) -> bool:
        """
        注册服务
        
        Args:
            service_info: 服务信息
            dependencies: 服务依赖列表（可选，如果ServiceInfo中已设置dependencies则忽略此参数）
            
        Returns:
            bool: 注册是否成功
        """
        try:
            if service_info.name in self.services:
                self.logger.warning(f"服务 {service_info.name} 已存在，将覆盖")
            
            self.services[service_info.name] = service_info
            
            # 设置依赖关系：优先使用ServiceInfo中的dependencies，其次使用方法参数
            final_dependencies = service_info.dependencies or dependencies
            if final_dependencies:
                self.service_dependencies[service_info.name] = final_dependencies
            
            self.stats["total_services"] = len(self.services)
            self.logger.info(f"服务 {service_info.name} 注册成功，优先级: {service_info.priority.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"注册服务 {service_info.name} 失败: {e}")
            return False
    
    def unregister_service(self, service_name: str) -> bool:
        """
        注销服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            bool: 注销是否成功
        """
        try:
            if service_name in self.services:
                # 先停止服务
                self.stop_service(service_name)
                
                # 移除服务
                del self.services[service_name]
                
                # 移除依赖关系
                if service_name in self.service_dependencies:
                    del self.service_dependencies[service_name]
                
                # 移除其他服务对此服务的依赖
                for deps in self.service_dependencies.values():
                    if service_name in deps:
                        deps.remove(service_name)
                
                self.stats["total_services"] = len(self.services)
                self.logger.info(f"服务 {service_name} 注销成功")
                return True
            else:
                self.logger.warning(f"服务 {service_name} 不存在")
                return False
                
        except Exception as e:
            self.logger.error(f"注销服务 {service_name} 失败: {e}")
            return False
    
    def _get_service_start_order(self) -> List[str]:
        """
        根据优先级和依赖关系计算服务启动顺序
        
        Returns:
            List[str]: 服务启动顺序列表
        """
        # 按优先级分组
        priority_groups = {}
        for name, service in self.services.items():
            priority = service.priority.value
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(name)
        
        # 按优先级排序（数值越小优先级越高）
        start_order = []
        for priority in sorted(priority_groups.keys()):
            # 在同一优先级内，根据依赖关系排序
            group_services = priority_groups[priority]
            ordered_group = self._resolve_dependencies(group_services)
            start_order.extend(ordered_group)
        
        return start_order
    
    def _resolve_dependencies(self, service_names: List[str]) -> List[str]:
        """
        解析服务依赖关系，返回正确的启动顺序
        
        Args:
            service_names: 服务名称列表
            
        Returns:
            List[str]: 解析后的服务顺序
        """
        # 简单的拓扑排序实现
        ordered = []
        remaining = service_names.copy()
        
        while remaining:
            # 找到没有未满足依赖的服务
            ready_services = []
            for service_name in remaining:
                dependencies = self.service_dependencies.get(service_name, [])
                # 检查依赖是否都已启动或不在当前组中
                deps_satisfied = all(
                    dep in ordered or dep not in service_names 
                    for dep in dependencies
                )
                if deps_satisfied:
                    ready_services.append(service_name)
            
            if not ready_services:
                # 如果没有可启动的服务，可能存在循环依赖
                self.logger.warning(f"检测到可能的循环依赖，剩余服务: {remaining}")
                # 强制添加剩余服务
                ready_services = remaining
            
            # 添加就绪的服务到顺序中
            for service_name in ready_services:
                ordered.append(service_name)
                remaining.remove(service_name)
        
        return ordered
    
    def initialize_all_services(self) -> bool:
        """
        初始化所有服务
        
        Returns:
            bool: 初始化是否成功
        """
        with self.initialization_lock:
            if self.is_initialized:
                self.logger.warning("系统已初始化，跳过重复初始化")
                return True
            
            try:
                self.logger.info("开始初始化所有系统服务...")
                start_time = time.time()
                
                # 获取启动顺序
                start_order = self._get_service_start_order()
                self.logger.info(f"服务启动顺序: {start_order}")
                
                # 按顺序初始化服务
                initialized_services = []
                for service_name in start_order:
                    if self._initialize_service(service_name):
                        initialized_services.append(service_name)
                    else:
                        self.logger.error(f"服务 {service_name} 初始化失败，停止后续初始化")
                        # 回滚已初始化的服务
                        self._rollback_services(initialized_services)
                        return False
                
                duration = time.time() - start_time
                self.is_initialized = True
                self.stats["system_uptime"] = time.time()
                
                self.logger.info(f"所有服务初始化完成，耗时: {duration:.2f}秒")
                return True
                
            except Exception as e:
                self.logger.error(f"系统初始化失败: {e}")
                return False
    
    def start_all_services(self) -> bool:
        """
        启动所有服务
        
        Returns:
            bool: 启动是否成功
        """
        try:
            if not self.is_initialized:
                self.logger.error("系统未初始化，无法启动服务")
                return False
            
            if self.is_running:
                self.logger.warning("系统已在运行，跳过重复启动")
                return True
            
            self.logger.info("启动所有系统服务...")
            
            # 获取启动顺序
            start_order = self._get_service_start_order()
            
            # 按顺序启动服务
            for service_name in start_order:
                service_info = self.services.get(service_name)
                if service_info and service_info.status == ServiceStatus.RUNNING:
                    # 如果服务已在运行状态，调用start方法（如果存在）
                    if service_info.has_method(service_info.start_method):
                        try:
                            result = service_info.call_method(service_info.start_method)
                            if result is False:
                                self.logger.warning(f"服务 {service_name} 启动方法返回False")
                        except Exception as e:
                            self.logger.warning(f"服务 {service_name} 启动方法调用失败: {e}")
            
            self.is_running = True
            self.logger.info("所有服务启动完成")
            return True
            
        except Exception as e:
            self.logger.error(f"服务启动失败: {e}")
            return False
    
    def cleanup_all_services(self) -> bool:
        """
        清理所有服务
        
        Returns:
            bool: 清理是否成功
        """
        try:
            self.logger.info("开始清理所有服务...")
            
            # 获取关闭顺序（启动顺序的逆序）
            start_order = self._get_service_start_order()
            cleanup_order = list(reversed(start_order))
            
            # 按顺序清理服务
            for service_name in cleanup_order:
                try:
                    service_info = self.services.get(service_name)
                    if service_info and service_info.has_method(service_info.cleanup_method):
                        self.logger.info(f"清理服务: {service_name}")
                        service_info.call_method(service_info.cleanup_method)
                        service_info.status = ServiceStatus.STOPPED
                        self.logger.info(f"服务 {service_name} 清理完成")
                except Exception as e:
                    self.logger.error(f"清理服务 {service_name} 失败: {e}")
            
            # 重置系统状态
            self.is_initialized = False
            self.stats["system_uptime"] = 0
            
            self.logger.info("所有服务清理完成")
            return True
            
        except Exception as e:
            self.logger.error(f"清理所有服务失败: {e}")
            return False
    
    def _initialize_service(self, service_name: str) -> bool:
        """
        初始化单个服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            service_info = self.services.get(service_name)
            if not service_info:
                self.logger.error(f"服务 {service_name} 不存在")
                return False
            
            self.logger.info(f"正在初始化服务: {service_name}")
            service_info.status = ServiceStatus.STARTING
            self.service_states[service_name] = "starting"
            
            # 调用初始化方法
            if service_info.has_method(service_info.init_method):
                result = service_info.call_method(service_info.init_method)
                if result is False:
                    raise Exception(f"服务初始化方法返回False")
            
            # 调用启动方法
            if service_info.has_method(service_info.start_method):
                result = service_info.call_method(service_info.start_method)
                if result is False:
                    raise Exception(f"服务启动方法返回False")
            
            service_info.status = ServiceStatus.RUNNING
            service_info.start_time = time.time()
            self.service_states[service_name] = "initialized"
            service_info.last_error = None
            
            self.stats["running_services"] += 1
            self.logger.info(f"服务 {service_name} 初始化成功")
            return True
            
        except Exception as e:
            service_info.status = ServiceStatus.ERROR
            service_info.last_error = str(e)
            self.stats["failed_services"] += 1
            self.logger.error(f"服务 {service_name} 初始化失败: {e}")
            return False
    
    def _rollback_services(self, service_names: List[str]):
        """
        回滚已初始化的服务
        
        Args:
            service_names: 需要回滚的服务名称列表
        """
        self.logger.warning(f"开始回滚服务: {service_names}")
        
        # 按相反顺序停止服务
        for service_name in reversed(service_names):
            try:
                self.stop_service(service_name)
            except Exception as e:
                self.logger.error(f"回滚服务 {service_name} 失败: {e}")
    
    def start_service(self, service_name: str) -> bool:
        """
        启动单个服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            bool: 启动是否成功
        """
        try:
            service_info = self.services.get(service_name)
            if not service_info:
                self.logger.error(f"服务 {service_name} 不存在")
                return False
            
            if service_info.status == ServiceStatus.RUNNING:
                self.logger.info(f"服务 {service_name} 已在运行")
                return True
            
            return self._initialize_service(service_name)
            
        except Exception as e:
            self.logger.error(f"启动服务 {service_name} 失败: {e}")
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """
        停止单个服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            bool: 停止是否成功
        """
        try:
            service_info = self.services.get(service_name)
            if not service_info:
                self.logger.error(f"服务 {service_name} 不存在")
                return False
            
            if service_info.status == ServiceStatus.STOPPED:
                self.logger.info(f"服务 {service_name} 已停止")
                return True
            
            self.logger.info(f"正在停止服务: {service_name}")
            service_info.status = ServiceStatus.STOPPING
            
            # 调用停止方法
            if service_info.has_method(service_info.stop_method):
                service_info.call_method(service_info.stop_method)
            
            # 调用清理方法
            if service_info.has_method(service_info.cleanup_method):
                service_info.call_method(service_info.cleanup_method)
            
            service_info.status = ServiceStatus.STOPPED
            service_info.start_time = None
            
            if self.stats["running_services"] > 0:
                self.stats["running_services"] -= 1
            
            self.logger.info(f"服务 {service_name} 停止成功")
            return True
            
        except Exception as e:
            service_info.status = ServiceStatus.ERROR
            service_info.last_error = str(e)
            self.logger.error(f"停止服务 {service_name} 失败: {e}")
            return False
    
    def stop_all_services(self) -> bool:
        """
        停止所有服务
        
        Returns:
            bool: 停止是否成功
        """
        try:
            self.logger.info("开始停止所有系统服务...")
            
            # 停止健康检查
            self._stop_health_check()
            
            # 按相反顺序停止服务
            start_order = self._get_service_start_order()
            stop_order = list(reversed(start_order))
            
            success_count = 0
            for service_name in stop_order:
                if self.stop_service(service_name):
                    success_count += 1
            
            self.is_running = False
            self.is_initialized = False
            
            self.logger.info(f"服务停止完成，成功停止 {success_count}/{len(stop_order)} 个服务")
            return success_count == len(stop_order)
            
        except Exception as e:
            self.logger.error(f"停止所有服务失败: {e}")
            return False
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """
        获取服务实例
        
        Args:
            service_name: 服务名称
            
        Returns:
            Optional[Any]: 服务实例，如果服务不存在返回None
        """
        if service_name in self.services:
            return self.services[service_name].service_instance
        return None
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """
        获取服务统计信息
        
        Returns:
            Dict[str, Any]: 服务统计信息
        """
        return {
            "total_services": len(self.services),
            "running_services": len([s for s in self.services.values() if s.status == ServiceStatus.RUNNING]),
            "stopped_services": len([s for s in self.services.values() if s.status == ServiceStatus.STOPPED]),
            "error_services": len([s for s in self.services.values() if s.status == ServiceStatus.ERROR]),
            "system_uptime": self.stats.get("system_uptime", 0),
            "is_initialized": self.is_initialized,
            "services_by_status": {
                status.value: [name for name, info in self.services.items() if info.status == status]
                for status in ServiceStatus
            }
         }
    
    def list_services(self) -> List[str]:
        """
        获取所有已注册服务的名称列表
        
        Returns:
            List[str]: 服务名称列表
        """
        return list(self.services.keys())
     
    def get_service_status(self, service_name: str) -> Optional[ServiceStatus]:
        """
        获取服务状态
        
        Args:
            service_name: 服务名称
            
        Returns:
            Optional[ServiceStatus]: 服务状态
        """
        service_info = self.services.get(service_name)
        return service_info.status if service_info else None
    
    def get_all_services_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有服务状态
        
        Returns:
            Dict: 所有服务的状态信息
        """
        status_info = {}
        for name, service_info in self.services.items():
            status_info[name] = {
                "status": service_info.status.value,
                "priority": service_info.priority.name,
                "start_time": service_info.start_time,
                "last_error": service_info.last_error,
                "uptime": time.time() - service_info.start_time if service_info.start_time else 0
            }
        return status_info
    
    def start_health_check(self):
        """
        启动健康检查
        """
        if self.health_check_running:
            return
        
        self.health_check_running = True
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_check_thread.start()
        self.logger.info("健康检查已启动")
    
    def _stop_health_check(self):
        """
        停止健康检查
        """
        self.health_check_running = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
        self.logger.info("健康检查已停止")
    
    def _health_check_loop(self):
        """
        健康检查循环
        """
        while self.health_check_running:
            try:
                self._perform_health_check()
                time.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"健康检查异常: {e}")
                time.sleep(5)  # 异常时短暂等待
    
    def _perform_health_check(self):
        """
        执行健康检查
        """
        unhealthy_services = []
        
        for name, service_info in self.services.items():
            if service_info.status != ServiceStatus.RUNNING:
                continue
            
            try:
                # 调用健康检查方法
                if service_info.has_method(service_info.health_check_method):
                    is_healthy = service_info.call_method(service_info.health_check_method)
                    if not is_healthy:
                        unhealthy_services.append(name)
                        self.logger.warning(f"服务 {name} 健康检查失败")
            except Exception as e:
                unhealthy_services.append(name)
                self.logger.error(f"服务 {name} 健康检查异常: {e}")
        
        self.stats["last_health_check"] = time.time()
        
        if unhealthy_services:
            self.logger.warning(f"发现不健康的服务: {unhealthy_services}")
        else:
            self.logger.debug("所有服务健康检查通过")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        获取系统统计信息
        
        Returns:
            Dict: 系统统计信息
        """
        current_time = time.time()
        if self.stats["system_uptime"] > 0:
            self.stats["system_uptime"] = current_time - self.stats["system_uptime"]
        
        return self.stats.copy()
    
    def is_healthy(self) -> bool:
        """
        检查系统整体健康状态
        
        Returns:
            bool: 系统是否健康
        """
        if not self.is_initialized or not self.is_running:
            return False
        
        # 检查是否有失败的关键服务
        for service_info in self.services.values():
            if (service_info.priority == ServicePriority.CRITICAL and 
                service_info.status != ServiceStatus.RUNNING):
                return False
        
        return True


# 全局实例
_system_manager_service = None


def get_system_manager_service() -> SystemManagerService:
    """获取系统管理协调器服务实例"""
    global _system_manager_service
    if _system_manager_service is None:
        _system_manager_service = SystemManagerService()
    return _system_manager_service


def initialize_system_manager_service() -> SystemManagerService:
    """初始化系统管理协调器服务"""
    service = get_system_manager_service()
    return service