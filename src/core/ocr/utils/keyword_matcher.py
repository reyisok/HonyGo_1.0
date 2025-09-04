#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR关键字匹配器
提供统一的关键字判断逻辑，支持多种匹配策略
优化版本：支持并行处理、预编译正则表达式、智能缓存、性能监控

@author: Mr.Rey Copyright © 2025
"""

from collections import defaultdict
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple
)
import hashlib
import re
import threading
import time

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum















class MatchStrategy(Enum):
    """匹配策略枚举"""
    EXACT = "exact"  # 精确匹配
    CONTAINS = "contains"  # 包含匹配
    FUZZY = "fuzzy"  # 模糊匹配
    REGEX = "regex"  # 正则表达式匹配
    SIMILARITY = "similarity"  # 相似度匹配

@dataclass
class MatchResult:
    """匹配结果"""
    found: bool
    matched_text: str
    confidence: float
    position: Optional[Tuple[int, int, int, int]]  # x, y, width, height
    strategy_used: MatchStrategy
    similarity_score: float = 0.0

class KeywordMatcher:
    """OCR关键字匹配器 - 优化版本"""
    
    def __init__(self, max_workers: int = 4):
        self.default_strategy = MatchStrategy.CONTAINS
        self.min_confidence = 0.5
        self.similarity_threshold = 0.8
        
        # 性能优化组件
        self.compiled_patterns = {}  # 预编译的正则表达式缓存
        self.similarity_cache = {}   # 相似度计算缓存
        self.access_frequency = defaultdict(int)  # 访问频率统计
        self.last_access_time = defaultdict(float)  # 最后访问时间
        
        # 线程池用于并行处理
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._cache_lock = threading.Lock()
        
        # 性能统计
        self.stats = {
            'total_matches': 0,
            'cache_hits': 0,
            'parallel_matches': 0,
            'avg_match_time': 0.0
        }
    
    def match_keyword(self, 
                     target_keyword: str, 
                     ocr_results: List[List[Any]], 
                     strategy: MatchStrategy = None,
                     min_confidence: float = None) -> MatchResult:
        """
        在OCR结果中匹配关键字 - 优化版本
        
        Args:
            target_keyword: 目标关键字
            ocr_results: OCR识别结果列表
            strategy: 匹配策略
            min_confidence: 最小置信度阈值
            
        Returns:
            MatchResult: 匹配结果
        """
        start_time = time.time()
        
        if not target_keyword or not ocr_results:
            return MatchResult(
                found=False,
                matched_text="",
                confidence=0.0,
                position=None,
                strategy_used=strategy or self.default_strategy
            )
        
        strategy = strategy or self.default_strategy
        min_confidence = min_confidence or self.min_confidence
        
        # 更新访问统计
        self.access_frequency[target_keyword] += 1
        self.last_access_time[target_keyword] = time.time()
        
        # 检查缓存
        cache_key = self._generate_cache_key(target_keyword, ocr_results, strategy)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            self.stats['cache_hits'] += 1
            return cached_result
        
        best_match = None
        best_score = 0.0
        
        for item in ocr_results:
            if not isinstance(item, list) or len(item) < 2:
                continue
                
            # 解析OCR结果项
            bbox = item[0] if len(item) > 0 else None
            text = item[1] if len(item) > 1 else ""
            confidence = item[2] if len(item) > 2 else 0.0
            
            # 根据策略进行匹配
            match_result = self._apply_strategy(target_keyword, text, strategy, confidence, bbox)
            
            # 如果找到匹配，检查是否是更好的匹配
            if match_result.found:
                # 对于低置信度但完全匹配的结果，给予更高的权重
                score = match_result.similarity_score
                if confidence < min_confidence:
                    # 低置信度的结果需要更高的相似度才能被接受
                    if match_result.similarity_score >= 0.9:  # 只接受高相似度的低置信度结果
                        score = match_result.similarity_score * 0.8  # 降低权重但仍然考虑
                    else:
                        continue  # 跳过低置信度且低相似度的结果
                else:
                    # 高置信度结果正常处理
                    score = match_result.similarity_score
                
                if score > best_score:
                    best_match = match_result
                    best_score = score
        
        result = best_match or MatchResult(
            found=False,
            matched_text="",
            confidence=0.0,
            position=None,
            strategy_used=strategy
        )
        
        # 缓存结果
        self._cache_result(cache_key, result)
        
        # 更新性能统计
        self.stats['total_matches'] += 1
        processing_time = time.time() - start_time
        self.stats['avg_match_time'] = (
            (self.stats['avg_match_time'] * (self.stats['total_matches'] - 1) + processing_time) / 
            self.stats['total_matches']
        )
        
        return result
    
    def _apply_strategy(self, 
                       target: str, 
                       text: str, 
                       strategy: MatchStrategy, 
                       confidence: float,
                       bbox: List) -> MatchResult:
        """
        应用匹配策略 - 优化版本
        
        Args:
            target: 目标关键字
            text: OCR识别的文本
            strategy: 匹配策略
            confidence: OCR置信度
            bbox: 边界框坐标
            
        Returns:
            MatchResult: 匹配结果
        """
        position = self._parse_bbox(bbox) if bbox else None
        
        if strategy == MatchStrategy.EXACT:
            found = target == text
            similarity = 1.0 if found else 0.0
        elif strategy == MatchStrategy.CONTAINS:
            found = target.lower() in text.lower()
            similarity = len(target) / len(text) if found and text else 0.0
        elif strategy == MatchStrategy.FUZZY:
            similarity = self._calculate_fuzzy_similarity_cached(target, text)
            found = similarity >= self.similarity_threshold
        elif strategy == MatchStrategy.REGEX:
            try:
                # 使用预编译的正则表达式
                pattern = self._get_compiled_pattern(target)
                found = bool(pattern.search(text))
                similarity = 1.0 if found else 0.0
            except re.error:
                found = False
                similarity = 0.0
        elif strategy == MatchStrategy.SIMILARITY:
            similarity = self._calculate_similarity_cached(target, text)
            # 对于相似度匹配，如果是包含关系且目标词较短，降低阈值要求
            if target.lower() in text.lower() and len(target) <= 4:
                # 对于短关键字的包含匹配，使用更宽松的阈值
                effective_threshold = min(self.similarity_threshold, 0.2)
            else:
                effective_threshold = self.similarity_threshold
            found = similarity >= effective_threshold
        else:
            found = False
            similarity = 0.0
        
        return MatchResult(
            found=found,
            matched_text=text if found else "",
            confidence=confidence,
            position=position,
            strategy_used=strategy,
            similarity_score=similarity
        )
    
    def _parse_bbox(self, bbox: List) -> Optional[Tuple[int, int, int, int]]:
        """
        解析边界框坐标
        
        Args:
            bbox: 边界框数据
            
        Returns:
            Tuple: (x, y, width, height) 或 None
        """
        try:
            if isinstance(bbox, list) and len(bbox) >= 4:
                # 处理不同格式的边界框
                if isinstance(bbox[0], list):  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    x = int(min(x_coords))
                    y = int(min(y_coords))
                    width = int(max(x_coords) - x)
                    height = int(max(y_coords) - y)
                else:  # [x, y, width, height]
                    x, y, width, height = map(int, bbox[:4])
                
                return (x, y, width, height)
        except (ValueError, IndexError, TypeError):
            pass
        
        return None
    
    def _generate_cache_key(self, target_keyword: str, ocr_results: List[List[Any]], strategy: MatchStrategy) -> str:
        """
        生成缓存键
        
        Args:
            target_keyword: 目标关键字
            ocr_results: OCR结果
            strategy: 匹配策略
            
        Returns:
            str: 缓存键
        """
        # 简化OCR结果用于缓存键生成
        simplified_results = [(item[1] if len(item) > 1 else "") for item in ocr_results if isinstance(item, list)]
        content = f"{target_keyword}_{strategy.value}_{str(simplified_results)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[MatchResult]:
        """
        获取缓存结果
        
        Args:
            cache_key: 缓存键
            
        Returns:
            Optional[MatchResult]: 缓存的匹配结果
        """
        with self._cache_lock:
            return self.similarity_cache.get(cache_key)
    
    def _cache_result(self, cache_key: str, result: MatchResult) -> None:
        """
        缓存结果
        
        Args:
            cache_key: 缓存键
            result: 匹配结果
        """
        with self._cache_lock:
            # 限制缓存大小，移除最少使用的项
            if len(self.similarity_cache) > 1000:
                # 移除访问频率最低的项
                oldest_key = min(self.similarity_cache.keys(), 
                               key=lambda k: self.access_frequency.get(k, 0))
                del self.similarity_cache[oldest_key]
            
            self.similarity_cache[cache_key] = result
    
    def _get_compiled_pattern(self, pattern: str) -> re.Pattern:
        """
        获取预编译的正则表达式
        
        Args:
            pattern: 正则表达式模式
            
        Returns:
            re.Pattern: 编译后的正则表达式
        """
        if pattern not in self.compiled_patterns:
            try:
                self.compiled_patterns[pattern] = re.compile(pattern, re.IGNORECASE)
            except re.error:
                # 如果正则表达式无效，创建一个永远不匹配的模式
                self.compiled_patterns[pattern] = re.compile(r'(?!.*)', re.IGNORECASE)
        
        return self.compiled_patterns[pattern]
    
    def _calculate_fuzzy_similarity_cached(self, s1: str, s2: str) -> float:
        """
        计算模糊相似度（带缓存）
        
        Args:
            s1: 字符串1
            s2: 字符串2
            
        Returns:
            float: 相似度分数 (0-1)
        """
        cache_key = f"fuzzy_{s1}_{s2}"
        
        with self._cache_lock:
            if cache_key in self.similarity_cache:
                return self.similarity_cache[cache_key]
        
        similarity = self._calculate_fuzzy_similarity(s1, s2)
        
        with self._cache_lock:
            self.similarity_cache[cache_key] = similarity
        
        return similarity
    
    def _calculate_similarity_cached(self, s1: str, s2: str) -> float:
        """
        计算字符串相似度（带缓存）
        
        Args:
            s1: 字符串1
            s2: 字符串2
            
        Returns:
            float: 相似度分数 (0-1)
        """
        cache_key = f"sim_{s1}_{s2}"
        
        with self._cache_lock:
            if cache_key in self.similarity_cache:
                return self.similarity_cache[cache_key]
        
        similarity = self._calculate_similarity(s1, s2)
        
        with self._cache_lock:
            self.similarity_cache[cache_key] = similarity
        
        return similarity
    
    def _calculate_fuzzy_similarity(self, target: str, text: str) -> float:
        """
        计算模糊相似度（基于编辑距离）
        
        Args:
            target: 目标字符串
            text: 比较字符串
            
        Returns:
            float: 相似度分数 (0-1)
        """
        if not target or not text:
            return 0.0
        
        # 简单的编辑距离算法
        len_target = len(target)
        len_text = len(text)
        
        if len_target == 0:
            return 0.0 if len_text > 0 else 1.0
        if len_text == 0:
            return 0.0
        
        # 创建距离矩阵
        matrix = [[0] * (len_text + 1) for _ in range(len_target + 1)]
        
        # 初始化第一行和第一列
        for i in range(len_target + 1):
            matrix[i][0] = i
        for j in range(len_text + 1):
            matrix[0][j] = j
        
        # 计算编辑距离
        for i in range(1, len_target + 1):
            for j in range(1, len_text + 1):
                if target[i-1] == text[j-1]:
                    cost = 0
                else:
                    cost = 1
                
                matrix[i][j] = min(
                    matrix[i-1][j] + 1,      # 删除
                    matrix[i][j-1] + 1,      # 插入
                    matrix[i-1][j-1] + cost  # 替换
                )
        
        # 计算相似度
        max_len = max(len_target, len_text)
        distance = matrix[len_target][len_text]
        similarity = 1.0 - (distance / max_len)
        
        return max(0.0, similarity)
    
    def _calculate_similarity(self, target: str, text: str) -> float:
        """
        计算字符串相似度（基于字符匹配）
        
        Args:
            target: 目标字符串
            text: 比较字符串
            
        Returns:
            float: 相似度分数 (0-1)
        """
        if not target or not text:
            return 0.0
        
        target_lower = target.lower()
        text_lower = text.lower()
        
        # 如果完全匹配
        if target_lower == text_lower:
            return 1.0
        
        # 如果包含匹配
        if target_lower in text_lower:
            return len(target_lower) / len(text_lower)
        
        # 计算字符重叠度
        target_chars = set(target_lower)
        text_chars = set(text_lower)
        
        intersection = target_chars.intersection(text_chars)
        union = target_chars.union(text_chars)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def match_multiple_keywords(self, 
                               keywords: List[str], 
                               ocr_results: List[List[Any]], 
                               strategy: MatchStrategy = None,
                               min_confidence: float = None,
                               parallel: bool = True) -> Dict[str, MatchResult]:
        """
        批量匹配多个关键字 - 支持并行处理
        
        Args:
            keywords: 关键字列表
            ocr_results: OCR识别结果列表
            strategy: 匹配策略
            min_confidence: 最小置信度阈值
            parallel: 是否使用并行处理
            
        Returns:
            Dict[str, MatchResult]: 关键字到匹配结果的映射
        """
        if not keywords:
            return {}
        
        if parallel and len(keywords) > 1:
            # 并行处理
            self.stats['parallel_matches'] += 1
            
            def match_single_keyword(keyword):
                return keyword, self.match_keyword(
                    target_keyword=keyword,
                    ocr_results=ocr_results,
                    strategy=strategy,
                    min_confidence=min_confidence
                )
            
            # 使用线程池并行处理
            futures = [self.executor.submit(match_single_keyword, keyword) for keyword in keywords]
            results = {}
            
            for future in futures:
                keyword, result = future.result()
                results[keyword] = result
            
            return results
        else:
            # 串行处理
            results = {}
            for keyword in keywords:
                results[keyword] = self.match_keyword(
                    target_keyword=keyword,
                    ocr_results=ocr_results,
                    strategy=strategy,
                    min_confidence=min_confidence
                )
            
            return results
    
    def get_best_match(self, 
                      target_keyword: str, 
                      ocr_results: List[List[Any]]) -> MatchResult:
        """
        使用多种策略找到最佳匹配
        
        Args:
            target_keyword: 目标关键字
            ocr_results: OCR识别结果
            
        Returns:
            MatchResult: 最佳匹配结果
        """
        strategies = [MatchStrategy.EXACT, MatchStrategy.CONTAINS, 
                     MatchStrategy.SIMILARITY, MatchStrategy.FUZZY]
        
        best_match = None
        best_score = 0.0
        
        for strategy in strategies:
            match_result = self.match_keyword(target_keyword, ocr_results, strategy)
            
            if match_result.found:
                # 计算综合分数（置信度 + 相似度）
                score = (match_result.confidence + match_result.similarity_score) / 2
                
                if score > best_score:
                    best_match = match_result
                    best_score = score
        
        return best_match or MatchResult(
            found=False,
            matched_text="",
            confidence=0.0,
            position=None,
            strategy_used=MatchStrategy.CONTAINS
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        
        Returns:
            Dict[str, Any]: 性能统计数据
        """
        return {
            'total_matches': self.stats['total_matches'],
            'cache_hits': self.stats['cache_hits'],
            'parallel_matches': self.stats['parallel_matches'],
            'avg_match_time': self.stats['avg_match_time'],
            'cache_hit_rate': self.stats['cache_hits'] / max(1, self.stats['total_matches']),
            'cache_size': len(self.similarity_cache),
            'compiled_patterns_count': len(self.compiled_patterns),
            'most_accessed_keywords': dict(sorted(self.access_frequency.items(), 
                                                key=lambda x: x[1], reverse=True)[:10])
        }
    
    def clear_cache(self) -> None:
        """
        清空缓存
        """
        with self._cache_lock:
            self.similarity_cache.clear()
            self.compiled_patterns.clear()
            self.access_frequency.clear()
            self.last_access_time.clear()
    
    def optimize_cache(self) -> None:
        """
        优化缓存 - 移除长时间未访问的项
        """
        current_time = time.time()
        cache_timeout = 3600  # 1小时超时
        
        with self._cache_lock:
            # 移除超时的缓存项
            expired_keys = [
                key for key, last_access in self.last_access_time.items()
                if current_time - last_access > cache_timeout
            ]
            
            for key in expired_keys:
                self.similarity_cache.pop(key, None)
                self.access_frequency.pop(key, None)
                self.last_access_time.pop(key, None)
    
    def find_matches(self, ocr_results: List[List[Any]], target_text: str, strategy: MatchStrategy = None) -> List[Dict[str, Any]]:
        """
        查找匹配的文字（兼容性方法）
        
        Args:
            ocr_results: OCR识别结果列表，格式为 [bbox, text, confidence]
            target_text: 目标文字
            strategy: 匹配策略
            
        Returns:
            List[Dict]: 匹配结果列表
        """
        matches = []
        strategy = strategy or self.default_strategy
        
        for item in ocr_results:
            if len(item) >= 3:
                bbox, text, confidence = item[0], item[1], item[2]
                
                # 应用匹配策略
                match_result = self._apply_strategy(target_text, text, strategy, confidence, bbox)
                
                if match_result.found:
                    match_dict = {
                        'text': text,
                        'confidence': confidence,
                        'similarity': match_result.similarity_score,
                        'position': match_result.position,
                        'bbox': bbox
                    }
                    matches.append(match_dict)
        
        # 按相似度排序
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        return matches
    
    def __del__(self):
        """
        析构函数 - 清理线程池
        """
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)