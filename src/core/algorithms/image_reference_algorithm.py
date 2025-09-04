#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片参照算法核心模块
实现屏幕截图与参照图片的相似度比对算法

@author: Mr.Rey Copyright © 2025
@created: 2025-01-13 15:30:00
@modified: 2025-01-03 03:37:00
@version: 1.0.0
"""

from pathlib import Path
import time
import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
import hashlib
import time
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Tuple, Any, Optional, List, Dict

from src.ui.services.logging_service import get_logger
from src.ui.services.coordinate_service import get_coordinate_service














class MatchMethod(Enum):
    """图像匹配方法枚举"""
    TEMPLATE_MATCHING = "template_matching"
    FEATURE_MATCHING = "feature_matching"
    HISTOGRAM_COMPARISON = "histogram_comparison"
    STRUCTURAL_SIMILARITY = "structural_similarity"


@dataclass
class MatchResult:
    """匹配结果数据类"""
    similarity: float
    position: Optional[Tuple[int, int]]
    confidence: float
    method: MatchMethod
    execution_time: float
    scale: float = 1.0  # DPI缩放比例，默认为1.0
    

class ImageReferenceAlgorithm:
    """
    图片参照算法类
    
    提供多种图像匹配算法，用于屏幕截图与参照图片的相似度比对
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化算法"""
        self.logger = get_logger("ImageReferenceAlgorithm")
        self._coordinate_service = get_coordinate_service()
        
        # 默认配置
        self.config = {
            "similarity_threshold": 0.8,
            "match_method": MatchMethod.TEMPLATE_MATCHING,
            "resize_factor": 1.0,
            "enable_preprocessing": True,
            "max_features": 1000,
            "feature_detector": "SIFT",
            "enable_caching": True,
            "cache_size": 50,
            "enable_parallel_processing": True,
            "max_workers": 4,
            "optimize_scales": True,
            "fast_mode": False
        }
        
        if config:
            self.config.update(config)
        
        # 性能优化组件
        self._image_cache = {} if self.config["enable_caching"] else None
        self._preprocessed_cache = {} if self.config["enable_caching"] else None
        self._thread_pool = ThreadPoolExecutor(max_workers=self.config["max_workers"]) if self.config["enable_parallel_processing"] else None
        
        self.logger.info("图片参照算法初始化完成")
        self.logger.debug(f"算法配置: {self.config}")
        
        # 性能统计
        self._performance_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "total_matches": 0,
            "avg_match_time": 0.0
        }
    
    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """
        DPI感知屏幕截图
        
        Args:
            region: 截图区域 (x, y, width, height)，None表示全屏
            
        Returns:
            截图的numpy数组，失败返回None
        """
        try:
            self.logger.debug(f"开始DPI感知屏幕截图 - 区域: {region}")
            
            # 使用DPI感知的坐标服务进行截图
            screenshot = self._coordinate_service.capture_screen(region)
            if screenshot is None:
                self.logger.error("DPI感知截图失败")
                return None
            
            # 转换为OpenCV格式 (BGR)
            image = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            self.logger.debug(f"DPI感知屏幕截图完成 - 尺寸: {image.shape[:2]}, 区域: {region}")
            return image
            
        except Exception as e:
            self.logger.error(f"DPI感知屏幕截图失败: {e}")
            return None
    
    def _calculate_image_hash(self, image: np.ndarray) -> str:
        """计算图像哈希值用于缓存
        
        Args:
            image: 输入图像
            
        Returns:
            str: 图像哈希值
        """
        try:
            # 使用图像内容和形状计算哈希
            image_bytes = image.tobytes()
            shape_str = str(image.shape)
            combined = image_bytes + shape_str.encode()
            return hashlib.md5(combined).hexdigest()[:16]
        except Exception as e:
            self.logger.warning(f"计算图像哈希失败: {e}")
            return str(time.time())  # 回退到时间戳
    
    def _get_cached_image(self, image_path: str) -> Optional[np.ndarray]:
        """从缓存获取图像
        
        Args:
            image_path: 图像路径
            
        Returns:
            Optional[np.ndarray]: 缓存的图像，None表示未命中
        """
        if not self.config["enable_caching"] or not self._image_cache:
            return None
            
        cache_key = f"img_{image_path}_{os.path.getmtime(image_path) if os.path.exists(image_path) else 0}"
        
        if cache_key in self._image_cache:
            self._performance_stats["cache_hits"] += 1
            return self._image_cache[cache_key]
        
        self._performance_stats["cache_misses"] += 1
        return None
    
    def _cache_image(self, image_path: str, image: np.ndarray):
        """缓存图像
        
        Args:
            image_path: 图像路径
            image: 图像数据
        """
        if not self.config["enable_caching"] or not self._image_cache:
            return
            
        cache_key = f"img_{image_path}_{os.path.getmtime(image_path) if os.path.exists(image_path) else 0}"
        
        # 限制缓存大小
        if len(self._image_cache) >= self.config["cache_size"]:
            # 移除最旧的缓存项
            oldest_key = next(iter(self._image_cache))
            del self._image_cache[oldest_key]
        
        self._image_cache[cache_key] = image.copy()
    
    def _get_optimized_scales(self, dpi_scale: float) -> List[float]:
        """获取优化的缩放比例列表
        
        Args:
            dpi_scale: DPI缩放比例
            
        Returns:
            List[float]: 优化的缩放比例列表
        """
        if self.config["fast_mode"]:
            # 快速模式：只使用关键缩放比例
            return [1.0, dpi_scale]
        elif self.config["optimize_scales"]:
            # 优化模式：智能选择缩放比例
            base_scales = [1.0, dpi_scale, 1.0/dpi_scale]
            if dpi_scale > 1.5:
                base_scales.extend([0.8, 1.2])
            elif dpi_scale < 0.8:
                base_scales.extend([0.9, 1.1])
            return sorted(list(set(base_scales)))
        else:
            # 完整模式：使用所有缩放比例
            scales = [1.0, dpi_scale, 1.0/dpi_scale, 0.8, 1.2, 0.9, 1.1]
            return sorted(list(set(scales)))
    
    def load_reference_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        加载参照图片（支持缓存）
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            图片的numpy数组，失败返回None
        """
        try:
            path = Path(image_path)
            if not path.exists():
                self.logger.error(f"参照图片不存在: {image_path}")
                return None
            
            # 尝试从缓存获取
            cached_image = self._get_cached_image(str(path))
            if cached_image is not None:
                self.logger.debug(f"从缓存加载参照图片: {image_path}")
                return cached_image
            
            # 从文件加载
            image = cv2.imread(str(path))
            if image is None:
                self.logger.error(f"无法读取参照图片: {image_path}")
                return None
            
            # 缓存图像
            self._cache_image(str(path), image)
            
            self.logger.debug(f"参照图片加载成功 - 尺寸: {image.shape[:2]}, 路径: {image_path}")
            return image
            
        except Exception as e:
            self.logger.error(f"加载参照图片失败: {e}")
            return None
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        图像预处理
        
        Args:
            image: 输入图像
            
        Returns:
            预处理后的图像
        """
        if not self.config["enable_preprocessing"]:
            return image
        
        try:
            # 调整大小
            if self.config["resize_factor"] != 1.0:
                height, width = image.shape[:2]
                new_height = int(height * self.config["resize_factor"])
                new_width = int(width * self.config["resize_factor"])
                image = cv2.resize(image, (new_width, new_height))
            
            # 高斯模糊去噪
            image = cv2.GaussianBlur(image, (3, 3), 0)
            
            return image
            
        except Exception as e:
            self.logger.error(f"图像预处理失败: {e}")
            return image
    
    def template_matching(self, screen_image: np.ndarray, reference_image: np.ndarray) -> MatchResult:
        """
        DPI感知的多尺度模板匹配算法（支持并行处理和缓存）
        
        Args:
            screen_image: 屏幕截图
            reference_image: 参照图片
            
        Returns:
            匹配结果
        """
        start_time = time.time()
        
        try:
            # 预处理
            screen_processed = self.preprocess_image(screen_image)
            reference_processed = self.preprocess_image(reference_image)
            
            # 转换为灰度图
            screen_gray = cv2.cvtColor(screen_processed, cv2.COLOR_BGR2GRAY)
            reference_gray = cv2.cvtColor(reference_processed, cv2.COLOR_BGR2GRAY)
            
            # 获取DPI缩放比例
            dpi_scale = self._coordinate_service.get_primary_screen_dpi_scale()
            
            # 计算缓存键 - 只使用参照图片哈希，避免屏幕截图变化影响缓存
            reference_hash = self._calculate_image_hash(reference_gray)
            reference_shape = f"{reference_gray.shape[0]}x{reference_gray.shape[1]}"
            cache_key = f"template_{reference_hash}_{reference_shape}_{dpi_scale}"
            
            # 尝试从缓存获取结果
            self.logger.debug(f"缓存键: {cache_key}")
            self.logger.debug(f"缓存启用: {self.config.get('enable_caching', False)}")
            self.logger.debug(f"缓存大小: {len(self._preprocessed_cache) if self._preprocessed_cache else 0}")
            
            if (self.config.get("enable_caching", False) and 
                hasattr(self, '_preprocessed_cache') and 
                self._preprocessed_cache is not None and 
                cache_key in self._preprocessed_cache):
                self._performance_stats["cache_hits"] += 1
                self.logger.debug(f"从缓存获取模板匹配结果，键: {cache_key}")
                cached_result = self._preprocessed_cache[cache_key]
                # 创建新的结果对象，更新执行时间
                return MatchResult(
                    similarity=cached_result.similarity,
                    position=cached_result.position,
                    confidence=cached_result.confidence,
                    method=cached_result.method,
                    execution_time=time.time() - start_time,
                    scale=cached_result.scale
                )
            
            self._performance_stats["cache_misses"] += 1
            self.logger.debug(f"缓存未命中，键: {cache_key}")
            
            # 获取优化的缩放比例
            scales = self._get_optimized_scales(dpi_scale)
            
            best_match = None
            best_confidence = 0.0
            
            # 并行处理多尺度匹配
            if (self.config.get("enable_parallel_processing", False) and 
                hasattr(self, '_thread_pool') and 
                self._thread_pool and 
                len(scales) > 2):
                best_match, best_confidence = self._parallel_template_match(screen_gray, reference_gray, scales)
            else:
                best_match, best_confidence = self._sequential_template_match(screen_gray, reference_gray, scales)
            
            execution_time = time.time() - start_time
            
            if best_match:
                result = MatchResult(
                    similarity=best_match['confidence'],
                    position=best_match['position'],
                    confidence=best_match['confidence'],
                    method=MatchMethod.TEMPLATE_MATCHING,
                    execution_time=execution_time,
                    scale=best_match['scale']
                )
                
                # 缓存结果
                if (self.config.get("enable_caching", False) and 
                    hasattr(self, '_preprocessed_cache') and 
                    self._preprocessed_cache is not None):
                    self._cache_template_result(cache_key, result)
                    self.logger.debug(f"结果已缓存，键: {cache_key}，缓存大小: {len(self._preprocessed_cache)}")
                
                # 更新性能统计
                self._performance_stats["total_matches"] += 1
                self._performance_stats["avg_match_time"] = (
                    (self._performance_stats["avg_match_time"] * (self._performance_stats["total_matches"] - 1) + execution_time) /
                    self._performance_stats["total_matches"]
                )
                
                self.logger.info(f"多尺度匹配完成，最佳尺度: {best_match['scale']:.2f}, 置信度: {best_match['confidence']:.3f}")
                return result
            else:
                result = MatchResult(
                    similarity=0.0,
                    position=None,
                    confidence=0.0,
                    method=MatchMethod.TEMPLATE_MATCHING,
                    execution_time=execution_time,
                    scale=1.0
                )
                
                # 更新性能统计（即使匹配失败）
                self._performance_stats["total_matches"] += 1
                self._performance_stats["avg_match_time"] = (
                    (self._performance_stats["avg_match_time"] * (self._performance_stats["total_matches"] - 1) + execution_time) /
                    self._performance_stats["total_matches"]
                )
                
                self.logger.warning("多尺度匹配未找到有效结果")
                return result
            
        except Exception as e:
            self.logger.error(f"DPI感知模板匹配失败: {e}")
            execution_time = time.time() - start_time
            return MatchResult(
                similarity=0.0,
                position=None,
                confidence=0.0,
                method=MatchMethod.TEMPLATE_MATCHING,
                execution_time=execution_time,
                scale=1.0
            )
    
    def feature_matching(self, screen_image: np.ndarray, reference_image: np.ndarray) -> MatchResult:
        """
        特征匹配算法
        
        Args:
            screen_image: 屏幕截图
            reference_image: 参照图片
            
        Returns:
            匹配结果
        """
        start_time = time.time()
        
        try:
            # 预处理
            screen_processed = self.preprocess_image(screen_image)
            reference_processed = self.preprocess_image(reference_image)
            
            # 转换为灰度图
            screen_gray = cv2.cvtColor(screen_processed, cv2.COLOR_BGR2GRAY)
            reference_gray = cv2.cvtColor(reference_processed, cv2.COLOR_BGR2GRAY)
            
            # 创建特征检测器
            if self.config["feature_detector"] == "SIFT":
                detector = cv2.SIFT_create(nfeatures=self.config["max_features"])
            elif self.config["feature_detector"] == "ORB":
                detector = cv2.ORB_create(nfeatures=self.config["max_features"])
            else:
                detector = cv2.SIFT_create(nfeatures=self.config["max_features"])
            
            # 检测关键点和描述符
            kp1, des1 = detector.detectAndCompute(screen_gray, None)
            kp2, des2 = detector.detectAndCompute(reference_gray, None)
            
            if des1 is None or des2 is None:
                raise ValueError("无法检测到足够的特征点")
            
            # 特征匹配
            if self.config["feature_detector"] == "SIFT":
                matcher = cv2.FlannBasedMatcher()
                matches = matcher.knnMatch(des1, des2, k=2)
                
                # 应用比率测试
                good_matches = []
                for match_pair in matches:
                    if len(match_pair) == 2:
                        m, n = match_pair
                        if m.distance < 0.7 * n.distance:
                            good_matches.append(m)
            else:
                matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                matches = matcher.match(des1, des2)
                good_matches = sorted(matches, key=lambda x: x.distance)[:50]
            
            # 计算相似度
            similarity = len(good_matches) / max(len(kp1), len(kp2))
            
            # 计算匹配位置（如果有足够的匹配点）
            position = None
            if len(good_matches) >= 4:
                src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                
                # 计算单应性矩阵
                M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
                if M is not None:
                    h, w = reference_gray.shape
                    pts = np.float32([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0]]).reshape(-1, 1, 2)
                    dst = cv2.perspectiveTransform(pts, M)
                    
                    # 计算中心点（物理坐标）
                    physical_center_x = int(np.mean(dst[:, 0, 0]))
                    physical_center_y = int(np.mean(dst[:, 0, 1]))
                    
                    # 将物理坐标转换为逻辑坐标
                    # 因为截图是基于物理像素的，所以匹配结果也是物理坐标
                    dpi_scale = self._coordinate_service.get_primary_screen_dpi_scale()
                    logical_center_x = int(physical_center_x / dpi_scale)
                    logical_center_y = int(physical_center_y / dpi_scale)
                    
                    self.logger.debug(
                        f"特征匹配坐标转换: 物理({physical_center_x}, {physical_center_y}) -> "
                        f"逻辑({logical_center_x}, {logical_center_y}), DPI缩放={dpi_scale}"
                    )
                    
                    position = (logical_center_x, logical_center_y)  # 返回逻辑坐标
            
            execution_time = time.time() - start_time
            
            return MatchResult(
                similarity=similarity,
                position=position,
                confidence=min(similarity, 1.0),
                method=MatchMethod.FEATURE_MATCHING,
                execution_time=execution_time,
                scale=1.0
            )
            
        except Exception as e:
            self.logger.error(f"特征匹配失败: {e}")
            execution_time = time.time() - start_time
            return MatchResult(
                similarity=0.0,
                position=None,
                confidence=0.0,
                method=MatchMethod.FEATURE_MATCHING,
                execution_time=execution_time,
                scale=1.0
            )
    
    def compare_images(self, screen_image: np.ndarray, reference_image: np.ndarray) -> MatchResult:
        """
        比较两张图片的相似度
        
        Args:
            screen_image: 屏幕截图
            reference_image: 参照图片
            
        Returns:
            匹配结果
        """
        method = self.config["match_method"]
        
        if method == MatchMethod.TEMPLATE_MATCHING:
            return self.template_matching(screen_image, reference_image)
        elif method == MatchMethod.FEATURE_MATCHING:
            return self.feature_matching(screen_image, reference_image)
        else:
            self.logger.warning(f"不支持的匹配方法: {method}，使用默认模板匹配")
            return self.template_matching(screen_image, reference_image)
    
    def find_image_on_screen(self, reference_image_path: str, 
                           region: Optional[Tuple[int, int, int, int]] = None) -> MatchResult:
        """
        在屏幕上查找参照图片
        
        Args:
            reference_image_path: 参照图片路径
            region: 搜索区域
            
        Returns:
            匹配结果
        """
        try:
            # 加载参照图片
            reference_image = self.load_reference_image(reference_image_path)
            if reference_image is None:
                return MatchResult(
                    similarity=0.0,
                    position=None,
                    confidence=0.0,
                    method=self.config["match_method"],
                    execution_time=0.0,
                    scale=1.0
                )
            
            # 屏幕截图
            screen_image = self.capture_screen(region)
            if screen_image is None:
                return MatchResult(
                    similarity=0.0,
                    position=None,
                    confidence=0.0,
                    method=self.config["match_method"],
                    execution_time=0.0,
                    scale=1.0
                )
            
            # 比较图片
            result = self.compare_images(screen_image, reference_image)
            
            self.logger.info(f"图片匹配完成 - 相似度: {result.similarity:.3f}, "
                           f"位置: {result.position}, 耗时: {result.execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"屏幕图片查找失败: {e}")
            return MatchResult(
                similarity=0.0,
                position=None,
                confidence=0.0,
                method=self.config["match_method"],
                execution_time=0.0,
                scale=1.0
            )
    
    def is_image_present(self, reference_image_path: str, 
                        region: Optional[Tuple[int, int, int, int]] = None) -> bool:
        """
        检查图片是否在屏幕上存在
        
        Args:
            reference_image_path: 参照图片路径
            region: 搜索区域
            
        Returns:
            是否存在
        """
        result = self.find_image_on_screen(reference_image_path, region)
        return result.similarity >= self.config["similarity_threshold"]
    
    def update_config(self, config_updates: Dict[str, Any]):
        """更新算法配置"""
        old_config = self.config.copy()
        self.config.update(config_updates)
        
        self.logger.info(f"算法配置已更新: {config_updates}")
        self.logger.debug(f"配置变更: {old_config} -> {self.config}")
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self.config.copy()
    
    def find_image_matches(self, screen_image: np.ndarray, reference_image: np.ndarray, 
                          method: MatchMethod = None, min_confidence: float = None) -> List[MatchResult]:
        """在屏幕图像中查找参照图像的所有匹配项
        
        Args:
            screen_image: 屏幕截图
            reference_image: 参照图片
            method: 匹配方法，None使用默认配置
            min_confidence: 最小置信度，None使用默认配置
            
        Returns:
            匹配结果列表
        """
        try:
            # 使用默认配置如果未指定
            if method is None:
                method = self.config["match_method"]
            if min_confidence is None:
                min_confidence = self.config["similarity_threshold"]
            
            # 执行单次匹配
            result = self.compare_images(screen_image, reference_image)
            
            # 检查是否满足最小置信度要求
            matches = []
            if result.confidence >= min_confidence:
                # 为匹配结果添加边界框信息
                if result.position:
                    h, w = reference_image.shape[:2]
                    center_x, center_y = result.position
                    # 计算边界框的左上角坐标
                    bbox_x = center_x - w // 2
                    bbox_y = center_y - h // 2
                    # 创建一个扩展的MatchResult，包含边界框信息
                    enhanced_result = MatchResult(
                        similarity=result.similarity,
                        position=result.position,
                        confidence=result.confidence,
                        method=result.method,
                        execution_time=result.execution_time,
                        scale=result.scale
                    )
                    # 添加边界框属性（x, y, width, height）
                    enhanced_result.bounding_box = (bbox_x, bbox_y, w, h)
                    matches.append(enhanced_result)
                else:
                    matches.append(result)
            
            # 更新性能统计
            self._performance_stats["total_matches"] += 1
            
            self.logger.info(f"图像匹配完成，找到 {len(matches)} 个匹配项")
            return matches
            
        except Exception as e:
            self.logger.error(f"图像匹配失败: {e}")
            return []
    
    def _parallel_template_match(self, screen_gray: np.ndarray, reference_gray: np.ndarray, scales: List[float]) -> Tuple[Optional[Dict], float]:
        """并行执行多尺度模板匹配
        
        Args:
            screen_gray: 屏幕灰度图
            reference_gray: 参照灰度图
            scales: 缩放比例列表
            
        Returns:
            最佳匹配结果和置信度
        """
        try:
            from concurrent.futures import as_completed
            
            best_match = None
            best_confidence = 0.0
            
            # 提交并行任务
            future_to_scale = {}
            for scale in scales:
                future = self._thread_pool.submit(self._single_scale_match, screen_gray, reference_gray, scale)
                future_to_scale[future] = scale
            
            # 收集结果
            for future in as_completed(future_to_scale):
                scale = future_to_scale[future]
                try:
                    match_result = future.result()
                    if match_result and match_result['confidence'] > best_confidence:
                        best_match = match_result
                        best_confidence = match_result['confidence']
                        self.logger.debug(f"并行匹配 - 尺度 {scale:.2f} 匹配度: {match_result['confidence']:.3f}")
                except Exception as scale_error:
                    self.logger.debug(f"并行匹配 - 尺度 {scale:.2f} 失败: {scale_error}")
            
            return best_match, best_confidence
            
        except Exception as e:
            self.logger.error(f"并行模板匹配失败: {e}")
            # 回退到顺序匹配
            return self._sequential_template_match(screen_gray, reference_gray, scales)
    
    def _sequential_template_match(self, screen_gray: np.ndarray, reference_gray: np.ndarray, scales: List[float]) -> Tuple[Optional[Dict], float]:
        """顺序执行多尺度模板匹配
        
        Args:
            screen_gray: 屏幕灰度图
            reference_gray: 参照灰度图
            scales: 缩放比例列表
            
        Returns:
            最佳匹配结果和置信度
        """
        best_match = None
        best_confidence = 0.0
        
        for scale in scales:
            try:
                match_result = self._single_scale_match(screen_gray, reference_gray, scale)
                if match_result and match_result['confidence'] > best_confidence:
                    best_match = match_result
                    best_confidence = match_result['confidence']
                    self.logger.debug(f"顺序匹配 - 尺度 {scale:.2f} 匹配度: {match_result['confidence']:.3f}")
            except Exception as scale_error:
                self.logger.debug(f"顺序匹配 - 尺度 {scale:.2f} 失败: {scale_error}")
                continue
        
        return best_match, best_confidence
    
    def _single_scale_match(self, screen_gray: np.ndarray, reference_gray: np.ndarray, scale: float) -> Optional[Dict]:
        """
        单一尺度模板匹配
        
        Args:
            screen_gray: 屏幕灰度图
            reference_gray: 参照灰度图
            scale: 缩放比例
            
        Returns:
            匹配结果字典或None
        """
        try:
            # 缩放参照图片
            if scale != 1.0:
                h, w = reference_gray.shape
                new_h, new_w = int(h * scale), int(w * scale)
                if new_h > 0 and new_w > 0 and new_h < screen_gray.shape[0] and new_w < screen_gray.shape[1]:
                    scaled_reference = cv2.resize(reference_gray, (new_w, new_h))
                else:
                    return None
            else:
                scaled_reference = reference_gray
            
            # 模板匹配
            result = cv2.matchTemplate(screen_gray, scaled_reference, cv2.TM_CCOEFF_NORMED)
            
            # 获取最佳匹配位置
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # 计算中心点坐标（物理坐标）
            h, w = scaled_reference.shape
            physical_center_x = max_loc[0] + w // 2
            physical_center_y = max_loc[1] + h // 2
            
            # 将物理坐标转换为逻辑坐标
            # 因为截图是基于物理像素的，所以匹配结果也是物理坐标
            dpi_scale = self._coordinate_service.get_primary_screen_dpi_scale()
            logical_center_x = int(physical_center_x / dpi_scale)
            logical_center_y = int(physical_center_y / dpi_scale)
            
            self.logger.debug(
                f"坐标转换: 物理({physical_center_x}, {physical_center_y}) -> "
                f"逻辑({logical_center_x}, {logical_center_y}), DPI缩放={dpi_scale}"
            )
            
            return {
                'confidence': max_val,
                'position': (logical_center_x, logical_center_y),  # 返回逻辑坐标
                'scale': scale
            }
            
        except Exception as e:
            self.logger.debug(f"单尺度匹配失败 (scale={scale}): {e}")
            return None
    
    def _cache_template_result(self, cache_key: str, result: MatchResult):
        """缓存模板匹配结果
        
        Args:
            cache_key: 缓存键
            result: 匹配结果
        """
        if self._preprocessed_cache is None:
            return
            
        # 限制缓存大小
        if len(self._preprocessed_cache) >= self.config["cache_size"]:
            # 移除最旧的缓存项
            oldest_key = next(iter(self._preprocessed_cache))
            del self._preprocessed_cache[oldest_key]
        
        self._preprocessed_cache[cache_key] = result
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息
        
        Returns:
            性能统计字典
        """
        stats = self._performance_stats.copy()
        if stats["cache_hits"] + stats["cache_misses"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / (stats["cache_hits"] + stats["cache_misses"])
        else:
            stats["cache_hit_rate"] = 0.0
        return stats
    
    def clear_cache(self):
        """清空缓存"""
        if self._image_cache:
            self._image_cache.clear()
        if self._preprocessed_cache:
            self._preprocessed_cache.clear()
        self.logger.info("缓存已清空")
    
    def __del__(self):
        """析构函数，清理资源"""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=True)