#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR优化配置管理模块
统一管理所有OCR优化参数和开关
@author: Mr.Rey Copyright © 2025
"""

from pathlib import Path
from typing import Any, Dict, Optional
import json
import os

from dataclasses import asdict, dataclass
from src.ui.services.logging_service import get_logger
















@dataclass
class SmartRegionConfig:
    """智能区域预测配置"""
    enabled: bool = True
    max_regions: int = 3
    confidence_threshold: float = 0.6
    history_limit: int = 100
    region_expansion_ratio: float = 0.1
    use_window_detection: bool = True
    adaptive_threshold: bool = True
    region_merge_enabled: bool = True


@dataclass
class ImagePreprocessingConfig:
    """图像预处理配置"""
    enabled: bool = True
    resize_enabled: bool = True
    max_width: int = 1920
    max_height: int = 1080
    min_size: int = 20
    quality_optimization: bool = True
    noise_reduction: bool = True
    contrast_enhancement: bool = True
    binarization_enabled: bool = False
    dpi_optimization: int = 150
    gaussian_blur: bool = False
    sharpening: bool = True
    auto_rotate: bool = True
    padding_enabled: bool = True
    padding_size: int = 10


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    max_cache_size: int = 1000
    cache_ttl: int = 3600  # 秒
    memory_cache_enabled: bool = True
    disk_cache_enabled: bool = True
    cache_directory: str = "cache/ocr"
    hash_algorithm: str = "md5"
    cleanup_interval: int = 300  # 秒


@dataclass
class GPUConfig:
    """GPU配置"""
    enabled: bool = True
    auto_detect: bool = True
    preferred_device: str = "auto"  # auto, cuda, mps, cpu
    memory_fraction: float = 0.8
    allow_growth: bool = True
    fallback_to_cpu: bool = True
    benchmark_on_startup: bool = True
    cudnn_benchmark: bool = True
    mixed_precision: bool = True
    memory_pool_enabled: bool = True
    device_warmup: bool = True


@dataclass
class PerformanceConfig:
    """性能优化配置"""
    enabled: bool = True
    parallel_processing: bool = True
    max_workers: int = 4
    batch_processing: bool = True
    batch_size: int = 8
    timeout_seconds: int = 60
    retry_attempts: int = 2
    early_termination: bool = True
    quantization_enabled: bool = True
    model_optimization: bool = True
    memory_optimization: bool = True
    thread_pool_size: int = 8


@dataclass
class OCROptimizationConfig:
    """OCR优化总配置"""
    smart_region: SmartRegionConfig
    image_preprocessing: ImagePreprocessingConfig
    cache: CacheConfig
    gpu: GPUConfig
    performance: PerformanceConfig
    
    # 全局开关
    global_optimization_enabled: bool = True
    debug_mode: bool = False
    logging_level: str = "INFO"
    
    # 兼容性设置
    fallback_to_standard: bool = True
    compatibility_mode: bool = False


class OptimizationConfigManager:
    """优化配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        if config_path is None:
            # 默认配置文件路径 - 优先使用环境变量
            project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
            if project_root_env:
                project_root = Path(project_root_env)
            else:
                # 回退到基于文件路径的计算
                project_root = Path(__file__).parent.parent
            config_path = project_root / "src" / "config" / "ocr_optimization.json"
        
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self._config = self._load_config()
    
    def _load_config(self) -> OCROptimizationConfig:
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 从字典创建配置对象
                return self._dict_to_config(config_data)
            else:
                # 创建默认配置
                default_config = self._create_default_config()
                self.save_config(default_config)
                return default_config
                
        except Exception as e:
            logger = get_logger("OptimizationConfigManager", "CONFIG")
            logger.warning(f"加载配置文件失败: {e}，使用默认配置")
            return self._create_default_config()
    
    def _create_default_config(self) -> OCROptimizationConfig:
        """创建默认配置"""
        return OCROptimizationConfig(
            smart_region=SmartRegionConfig(),
            image_preprocessing=ImagePreprocessingConfig(),
            cache=CacheConfig(),
            gpu=GPUConfig(),
            performance=PerformanceConfig()
        )
    
    def _dict_to_config(self, config_data: Dict[str, Any]) -> OCROptimizationConfig:
        """从字典创建配置对象"""
        try:
            return OCROptimizationConfig(
                smart_region=SmartRegionConfig(**config_data.get('smart_region', {})),
                image_preprocessing=ImagePreprocessingConfig(**config_data.get('image_preprocessing', {})),
                cache=CacheConfig(**config_data.get('cache', {})),
                gpu=GPUConfig(**config_data.get('gpu', {})),
                performance=PerformanceConfig(**config_data.get('performance', {})),
                global_optimization_enabled=config_data.get('global_optimization_enabled', True),
                debug_mode=config_data.get('debug_mode', False),
                logging_level=config_data.get('logging_level', 'INFO'),
                fallback_to_standard=config_data.get('fallback_to_standard', True),
                compatibility_mode=config_data.get('compatibility_mode', False)
            )
        except Exception as e:
            logger = get_logger("OptimizationConfigManager", "CONFIG")
            logger.warning(f"配置解析失败: {e}，使用默认配置")
            return self._create_default_config()
    
    def get_config(self) -> OCROptimizationConfig:
        """获取当前配置"""
        return self._config
    
    def save_config(self, config: Optional[OCROptimizationConfig] = None) -> bool:
        """保存配置到文件"""
        try:
            if config is None:
                config = self._config
            
            # 转换为字典
            config_dict = {
                'smart_region': asdict(config.smart_region),
                'image_preprocessing': asdict(config.image_preprocessing),
                'cache': asdict(config.cache),
                'gpu': asdict(config.gpu),
                'performance': asdict(config.performance),
                'global_optimization_enabled': config.global_optimization_enabled,
                'debug_mode': config.debug_mode,
                'logging_level': config.logging_level,
                'fallback_to_standard': config.fallback_to_standard,
                'compatibility_mode': config.compatibility_mode
            }
            
            # 保存到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            self._config = config
            return True
            
        except Exception as e:
            logger = get_logger("OptimizationConfigManager", "CONFIG")
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def update_config(self, **kwargs) -> bool:
        """更新配置参数"""
        try:
            config_dict = asdict(self._config)
            
            # 更新参数
            for key, value in kwargs.items():
                if '.' in key:
                    # 支持嵌套参数更新，如 'gpu.enabled'
                    parts = key.split('.')
                    current = config_dict
                    for part in parts[:-1]:
                        if part in current:
                            current = current[part]
                        else:
                            break
                    else:
                        current[parts[-1]] = value
                else:
                    if key in config_dict:
                        config_dict[key] = value
            
            # 重新创建配置对象
            new_config = self._dict_to_config(config_dict)
            return self.save_config(new_config)
            
        except Exception as e:
            logger = get_logger("OptimizationConfigManager", "CONFIG")
            logger.error(f"更新配置失败: {e}")
            return False
    
    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        try:
            default_config = self._create_default_config()
            return self.save_config(default_config)
        except Exception as e:
            logger = get_logger("OptimizationConfigManager", "CONFIG")
            logger.error(f"重置配置失败: {e}")
            return False
    
    def is_optimization_enabled(self) -> bool:
        """检查优化是否启用"""
        return self._config.global_optimization_enabled
    
    def get_cache_directory(self) -> Path:
        """获取缓存目录路径"""
        cache_dir = Path(self._config.cache.cache_directory)
        if not cache_dir.is_absolute():
            # 相对路径，基于项目根目录 - 优先使用环境变量
            project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
            if project_root_env:
                project_root = Path(project_root_env)
            else:
                # 回退到基于文件路径的计算
                project_root = Path(__file__).parent.parent.parent.parent
            cache_dir = project_root / cache_dir
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置有效性"""
        issues = []
        warnings = []
        
        config = self._config
        
        # 验证智能区域配置
        if config.smart_region.max_regions <= 0:
            issues.append("智能区域最大数量必须大于0")
        if not 0 <= config.smart_region.confidence_threshold <= 1:
            issues.append("置信度阈值必须在0-1之间")
        
        # 验证图像预处理配置
        if config.image_preprocessing.max_width <= 0 or config.image_preprocessing.max_height <= 0:
            issues.append("图像最大尺寸必须大于0")
        
        # 验证缓存配置
        if config.cache.max_cache_size <= 0:
            issues.append("缓存最大大小必须大于0")
        if config.cache.cache_ttl <= 0:
            warnings.append("缓存TTL设置为0或负数，缓存将立即过期")
        
        # 验证GPU配置
        if config.gpu.memory_fraction <= 0 or config.gpu.memory_fraction > 1:
            issues.append("GPU内存占用比例必须在0-1之间")
        
        # 验证性能配置
        if config.performance.max_workers <= 0:
            issues.append("最大工作线程数必须大于0")
        if config.performance.timeout_seconds <= 0:
            warnings.append("超时时间设置过小，可能导致处理失败")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }


# 全局配置管理器实例
_config_manager = None


def get_config_manager() -> OptimizationConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = OptimizationConfigManager()
    return _config_manager


def get_optimization_config() -> OCROptimizationConfig:
    """获取优化配置"""
    return get_config_manager().get_config()


def is_optimization_enabled() -> bool:
    """检查优化是否启用"""
    return get_config_manager().is_optimization_enabled()


if __name__ == "__main__":
    # 测试配置管理器
    test_logger = get_logger("OptimizationConfigTest", "CONFIG")
    manager = OptimizationConfigManager()
    config = manager.get_config()
    
    test_logger.info("当前配置:")
    test_logger.info(f"全局优化启用: {config.global_optimization_enabled}")
    test_logger.info(f"智能区域预测启用: {config.smart_region.enabled}")
    test_logger.info(f"图像预处理启用: {config.image_preprocessing.enabled}")
    test_logger.info(f"缓存启用: {config.cache.enabled}")
    test_logger.info(f"GPU加速启用: {config.gpu.enabled}")
    
    # 验证配置
    validation = manager.validate_config()
    test_logger.info(f"配置验证: {'通过' if validation['valid'] else '失败'}")
    if validation['issues']:
        test_logger.warning(f"问题: {validation['issues']}")
    if validation['warnings']:
        test_logger.warning(f"警告: {validation['warnings']}")