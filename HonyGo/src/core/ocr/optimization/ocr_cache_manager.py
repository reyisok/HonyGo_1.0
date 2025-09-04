#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR缓存管理器
提供OCR识别结果的缓存功能，提高重复识别的性能

@author: Mr.Rey Copyright © 2025
@created: 2025-09-04 21:36:00
@modified: 2025-09-04 21:36:00
@version: 1.0.0
"""

import hashlib
import time
from typing import Dict, Optional, Any, Tuple
from threading import Lock
import logging

class OCRCacheManager:
    """
    OCR缓存管理器
    管理OCR识别结果的缓存，提高重复识别的性能
    """
    
    def __init__(self, max_cache_size: int = 1000, cache_ttl: int = 3600):
        """
        初始化OCR缓存管理器
        
        Args:
            max_cache_size: 最大缓存条目数
            cache_ttl: 缓存生存时间（秒）
        """
        self.max_cache_size = max_cache_size
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = Lock()
        self.logger = logging.getLogger(__name__)
        
    def _generate_cache_key(self, image_data: bytes, ocr_config: Dict = None) -> str:
        """
        生成缓存键
        
        Args:
            image_data: 图像数据
            ocr_config: OCR配置
            
        Returns:
            缓存键
        """
        hasher = hashlib.md5()
        hasher.update(image_data)
        if ocr_config:
            config_str = str(sorted(ocr_config.items()))
            hasher.update(config_str.encode('utf-8'))
        return hasher.hexdigest()
    
    def get(self, image_data: bytes, ocr_config: Dict = None) -> Optional[Any]:
        """
        从缓存获取OCR结果
        
        Args:
            image_data: 图像数据
            ocr_config: OCR配置
            
        Returns:
            缓存的OCR结果，如果不存在或已过期则返回None
        """
        cache_key = self._generate_cache_key(image_data, ocr_config)
        
        with self._lock:
            if cache_key in self._cache:
                result, timestamp = self._cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    self.logger.debug(f"缓存命中: {cache_key}")
                    return result
                else:
                    # 缓存已过期，删除
                    del self._cache[cache_key]
                    self.logger.debug(f"缓存过期已删除: {cache_key}")
        
        return None
    
    def put(self, image_data: bytes, ocr_result: Any, ocr_config: Dict = None) -> None:
        """
        将OCR结果存入缓存
        
        Args:
            image_data: 图像数据
            ocr_result: OCR识别结果
            ocr_config: OCR配置
        """
        cache_key = self._generate_cache_key(image_data, ocr_config)
        current_time = time.time()
        
        with self._lock:
            # 如果缓存已满，删除最旧的条目
            if len(self._cache) >= self.max_cache_size:
                oldest_key = min(self._cache.keys(), 
                               key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
                self.logger.debug(f"缓存已满，删除最旧条目: {oldest_key}")
            
            self._cache[cache_key] = (ocr_result, current_time)
            self.logger.debug(f"缓存已存储: {cache_key}")
    
    def clear(self) -> None:
        """
        清空所有缓存
        """
        with self._lock:
            self._cache.clear()
            self.logger.info("缓存已清空")
    
    def cleanup_expired(self) -> int:
        """
        清理过期的缓存条目
        
        Returns:
            清理的条目数量
        """
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, (_, timestamp) in self._cache.items():
                if current_time - timestamp >= self.cache_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
        
        if expired_keys:
            self.logger.info(f"清理了 {len(expired_keys)} 个过期缓存条目")
        
        return len(expired_keys)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        with self._lock:
            return {
                'cache_size': len(self._cache),
                'max_cache_size': self.max_cache_size,
                'cache_ttl': self.cache_ttl,
                'cache_usage_ratio': len(self._cache) / self.max_cache_size if self.max_cache_size > 0 else 0
            }

# 全局缓存管理器实例
_cache_manager = None

def get_cache_manager() -> OCRCacheManager:
    """
    获取全局缓存管理器实例
    
    Returns:
        OCR缓存管理器实例
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = OCRCacheManager()
    return _cache_manager

def initialize_cache_manager(max_cache_size: int = 1000, cache_ttl: int = 3600) -> OCRCacheManager:
    """
    初始化全局缓存管理器
    
    Args:
        max_cache_size: 最大缓存条目数
        cache_ttl: 缓存生存时间（秒）
        
    Returns:
        OCR缓存管理器实例
    """
    global _cache_manager
    _cache_manager = OCRCacheManager(max_cache_size, cache_ttl)
    return _cache_manager