#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一系统配置管理服务

@author: Mr.Rey Copyright © 2025

功能:
1. 配置中心化管理
2. 配置热更新
3. 配置验证机制
4. 配置变更通知
5. 配置备份和恢复
"""

import json
import shutil
import threading
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from src.ui.services.logging_service import get_logger
from jsonschema import ValidationError
from jsonschema import validate
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class ConfigChangeType(Enum):
    """配置变更类型"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    RELOADED = "reloaded"


@dataclass
class ConfigChangeEvent:
    """配置变更事件"""
    config_name: str
    change_type: ConfigChangeType
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)


class UnifiedConfigService:
    """统一配置管理服务"""
    
    def __init__(self, config_dir: Path = None, backup_dir: Path = None):
        self.logger = get_logger("UnifiedConfigService")
        self.config_dir = config_dir or Path("src/config")
        self.backup_dir = backup_dir or Path("src/config/backups")
        
        # 确保目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置存储
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._config_files: Dict[str, Path] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}
        
        # 监听器
        self._change_listeners: Dict[str, List[Callable[[ConfigChangeEvent], None]]] = {}
        self._global_listeners: List[Callable[[ConfigChangeEvent], None]] = []
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 文件监控
        self._observer = None
        
    def create_backup(self, config_name: str):
        """创建配置备份"""
        try:
            if config_name not in self._config_files:
                return
                
            source_file = self._config_files[config_name]
            if not source_file.exists():
                return
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{config_name}_{timestamp}.json"
            
            shutil.copy2(source_file, backup_file)
            
            # 清理旧备份（保留最近10个）
            self._cleanup_backups(config_name)
            
        except Exception as e:
            self.logger.warning(f"创建配置备份失败 {config_name}: {e}")
    
    def _cleanup_backups(self, config_name: str, keep_count: int = 10):
        """清理旧备份"""
        try:
            backup_files = list(self.backup_dir.glob(f"{config_name}_*.json"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for backup_file in backup_files[keep_count:]:
                backup_file.unlink()
                
        except Exception as e:
            self.logger.warning(f"清理备份文件失败: {e}")
    
    def reload_config(self, config_name: str):
        """重新加载配置"""
        if config_name not in self._config_files:
            self.logger.warning(f"配置文件不存在: {config_name}")
            return
        
        config_file = self._config_files[config_name]
        
        try:
            self._load_config_file(config_name, config_file)
            
            # 触发重新加载事件
            event = ConfigChangeEvent(
                config_name=config_name,
                change_type=ConfigChangeType.RELOADED,
                new_value=self._configs[config_name]
            )
            self._notify_listeners(event)
            
        except Exception as e:
            self.logger.error(f"重新加载配置失败 {config_name}: {e}")
            raise
    
    def add_change_listener(self, config_name: str, listener: Callable[[ConfigChangeEvent], None]):
        """添加配置变更监听器"""
        with self._lock:
            if config_name not in self._change_listeners:
                self._change_listeners[config_name] = []
            self._change_listeners[config_name].append(listener)
    
    def add_global_listener(self, listener: Callable[[ConfigChangeEvent], None]):
        """添加全局变更监听器"""
        with self._lock:
            self._global_listeners.append(listener)
    
    def _notify_listeners(self, event: ConfigChangeEvent):
        """通知监听器"""
        try:
            # 通知特定配置监听器
            if event.config_name in self._change_listeners:
                for listener in self._change_listeners[event.config_name]:
                    try:
                        listener(event)
                    except Exception as e:
                        self.logger.error(f"配置变更监听器执行失败: {e}")
            
            # 通知全局监听器
            for listener in self._global_listeners:
                try:
                    listener(event)
                except Exception as e:
                    self.logger.error(f"全局配置变更监听器执行失败: {e}")
                    
        except Exception as e:
            self.logger.error(f"通知配置变更监听器失败: {e}")
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有配置"""
        with self._lock:
            return self._configs.copy()
    
    def get_config_names(self) -> List[str]:
        """获取所有配置名称"""
        with self._lock:
            return list(self._configs.keys())
    
    def load_all_configs(self) -> bool:
        """加载所有配置文件
        
        Returns:
            bool: 是否成功加载所有配置
        """
        try:
            self.logger.info("开始加载所有配置文件...")
            
            # 确保配置目录存在
            if not self.config_dir.exists():
                self.logger.warning(f"配置目录不存在: {self.config_dir}")
                self.config_dir.mkdir(parents=True, exist_ok=True)
                return True  # 空目录也算成功
            
            # 扫描配置目录中的所有JSON文件
            config_files = list(self.config_dir.glob("*.json"))
            if not config_files:
                self.logger.info("配置目录中没有找到配置文件")
                return True
            
            success_count = 0
            for config_file in config_files:
                config_name = config_file.stem
                try:
                    self._load_config_file(config_name, config_file)
                    success_count += 1
                    self.logger.debug(f"配置文件加载成功: {config_name}")
                except Exception as e:
                    self.logger.error(f"配置文件加载失败 {config_name}: {e}")
            
            self.logger.info(f"配置加载完成，成功: {success_count}/{len(config_files)}")
            return success_count > 0 or len(config_files) == 0
            
        except Exception as e:
            self.logger.error(f"加载所有配置失败: {e}")
            return False
    
    def get_all_config_keys(self) -> List[str]:
        """获取所有配置的键名列表
        
        Returns:
            List[str]: 所有配置的键名列表
        """
        with self._lock:
            all_keys = []
            for config_name, config_data in self._configs.items():
                if isinstance(config_data, dict):
                    for key in config_data.keys():
                        all_keys.append(f"{config_name}.{key}")
                else:
                    all_keys.append(config_name)
            return all_keys
    
    def export_config(self, config_name: str, export_path: str):
        """导出配置"""
        if config_name not in self._configs:
            raise ValueError(f"配置不存在: {config_name}")
        
        export_file = Path(export_path)
        export_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(self._configs[config_name], f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"配置导出成功: {config_name} -> {export_path}")
    
    def import_config(self, config_name: str, import_path: str, validate: bool = True):
        """导入配置"""
        import_file = Path(import_path)
        
        if not import_file.exists():
            raise FileNotFoundError(f"导入文件不存在: {import_path}")
        
        with open(import_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        if validate and config_name in self._config_schemas:
            self._validate_config(config_name, config_data)
        
        old_config = self._configs.get(config_name)
        self._configs[config_name] = config_data
        
        # 保存到文件
        if config_name in self._config_files:
            self._save_config_file(config_name)
        
        # 触发变更事件
        event = ConfigChangeEvent(
            config_name=config_name,
            change_type=ConfigChangeType.MODIFIED,
            old_value=old_config,
            new_value=config_data,
            source="import"
        )
        self._notify_listeners(event)
        
        self.logger.info(f"配置导入成功: {config_name} <- {import_path}")
    
    def cleanup(self):
        """清理资源"""
        try:
            self.logger.info("清理配置管理服务")
            
            # 停止文件监控
            if self._observer:
                self._observer.stop()
                self._observer.join()
            
            # 清理监听器
            with self._lock:
                self._change_listeners.clear()
                self._global_listeners.clear()
            
            self.logger.info("配置管理服务清理完成")
            
        except Exception as e:
            self.logger.error(f"清理配置管理服务失败: {e}")


# 全局配置服务实例
_config_service: Optional[UnifiedConfigService] = None
_config_lock = threading.Lock()


def get_config_service() -> UnifiedConfigService:
    """获取配置服务实例"""
    global _config_service
    
    if _config_service is None:
        with _config_lock:
            if _config_service is None:
                _config_service = UnifiedConfigService()
    
    return _config_service


def initialize_config_service(config_dir: str = None) -> UnifiedConfigService:
    """初始化配置服务"""
    global _config_service
    
    with _config_lock:
        if _config_service is not None:
            _config_service.cleanup()
        
        _config_service = UnifiedConfigService(config_dir)
    
    return _config_service


def cleanup_config_service():
    """清理配置服务"""
    global _config_service
    
    with _config_lock:
        if _config_service is not None:
            _config_service.cleanup()
            _config_service = None


# 便捷函数
def get_config(config_name: str, path: str = None, default: Any = None) -> Any:
    """获取配置值"""
    return get_config_service().get_config(config_name, path, default)


def set_config(config_name: str, path: str, value: Any, save: bool = True):
    """设置配置值"""
    return get_config_service().set_config(config_name, path, value, save)


def reload_config(config_name: str):
    """重新加载配置"""
    return get_config_service().reload_config(config_name)


def add_config_listener(config_name: str, listener: Callable[[ConfigChangeEvent], None]):
    """添加配置变更监听器"""
    return get_config_service().add_change_listener(config_name, listener)