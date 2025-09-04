#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键字匹配OCR优化服务
专门针对关键字匹配场景的OCR结果优化和后处理
@author: Mr.Rey Copyright © 2025
"""

from typing import List, Tuple

from dataclasses import dataclass

from src.config.optimization_config_manager import OptimizationConfigManager
from src.core.ocr.utils.keyword_matcher import KeywordMatcher
from src.ui.services.logging_service import get_logger
















@dataclass
class OCRTextResult:
    """
    OCR文本结果数据类
    """
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    original_text: str = None
    processed_text: str = None
    keyword_matches: List[str] = None
    
    def __post_init__(self):
        if self.original_text is None:
            self.original_text = self.text
        if self.keyword_matches is None:
            self.keyword_matches = []


class KeywordOCROptimizer:
    """
    关键字匹配OCR优化器
    专门针对关键字匹配场景进行OCR结果优化和后处理
    """
    
    def __init__(self):
        self.logger = get_logger("KeywordOCROptimizer", "Application")
        self.config_manager = OptimizationConfigManager()
        self.config = self.config_manager.get_config()
        self.keyword_matcher = KeywordMatcher()
        
        # 关键字匹配优化配置
        self.keyword_config = self.config.keyword_matching_optimization
        
        # 常见OCR错误映射
        self._init_error_corrections()
        
        # 字符相似度映射
        self._init_similarity_mappings()
        
        self.logger.info("关键字匹配OCR优化器初始化完成")
    
    def _init_error_corrections(self):
        """
        初始化常见OCR错误修正映射
        """
        self.error_corrections = {
            # 数字常见错误
            'O': '0', 'o': '0', 'I': '1', 'l': '1', 'S': '5', 's': '5',
            'Z': '2', 'z': '2', 'B': '8', 'G': '6', 'g': '9',
            
            # 字母常见错误
            '0': 'O', '1': 'I', '5': 'S', '2': 'Z', '8': 'B', '6': 'G', '9': 'g',
            
            # 中文常见错误
            '入': '人', '刀': '力', '乂': '又', '丨': '丁', '亠': '亡',
            '冂': '冊', '匚': '匡', '卩': '卯', '厂': '厅', '厶': '厸',
            
            # 特殊字符
            '|': 'I', '!': '1', '@': 'a', '#': 'H', '$': 'S', '%': 'X',
            '^': 'A', '&': '8', '*': 'x', '(': 'C', ')': 'D',
            
            # 标点符号
            '，': ',', '。': '.', '；': ';', '：': ':', '？': '?', '！': '!'
        }
    
    def _init_similarity_mappings(self):
        """
        初始化字符相似度映射
        """
        self.similarity_mappings = {
            # 数字相似字符
            '0': ['O', 'o', 'Q', 'q'],
            '1': ['I', 'l', '|', '!'],
            '2': ['Z', 'z'],
            '5': ['S', 's'],
            '8': ['B'],
            '6': ['G'],
            '9': ['g', 'q'],
            
            # 字母相似字符
            'O': ['0', 'Q', 'o'],
            'I': ['1', 'l', '|'],
            'S': ['5', 's'],
            'Z': ['2', 'z'],
            'B': ['8'],
            'G': ['6'],
            
            # 中文相似字符
            '人': ['入', '八'],
            '力': ['刀'],
            '又': ['乂'],
            '丁': ['丨'],
        }
    
    def optimize_ocr_results_for_keywords(self, ocr_results: List[dict], target_keywords: List[str] = None) -> List[OCRTextResult]:
        """
        针对关键字匹配优化OCR结果
        
        Args:
            ocr_results: OCR原始结果列表
            target_keywords: 目标关键字列表
            
        Returns:
            List[OCRTextResult]: 优化后的OCR结果列表
        """
        try:
            self.logger.info(f"开始关键字OCR结果优化，目标关键字: {target_keywords}")
            
            optimized_results = []
            
            for result in ocr_results:
                # 解析OCR结果
                if isinstance(result, dict):
                    text = result.get('text', '')
                    confidence = result.get('confidence', 0.0)
                    bbox = result.get('bbox', (0, 0, 0, 0))
                elif isinstance(result, list) and len(result) >= 2:
                    bbox = result[0] if len(result) > 0 else (0, 0, 0, 0)
                    text = result[1] if len(result) > 1 else ''
                    confidence = result[2] if len(result) > 2 else 0.0
                else:
                    continue
                
                # 创建OCR文本结果对象
                ocr_text_result = OCRTextResult(
                    text=text,
                    confidence=confidence,
                    bbox=bbox,
                    original_text=text
                )
                
                # 文本预处理和错误修正
                processed_text = self._preprocess_text(text)
                ocr_text_result.processed_text = processed_text
                
                # 关键字匹配
                if target_keywords:
                    matched_keywords = []
                    for keyword in target_keywords:
                        match_result = self.keyword_matcher.match_keyword(
                            target_keyword=keyword,
                            ocr_results=[[bbox, text, confidence]]
                        )
                        if match_result.found:
                            matched_keywords.append(keyword)
                    
                    ocr_text_result.keyword_matches = matched_keywords
                
                optimized_results.append(ocr_text_result)
            
            self.logger.info(f"关键字OCR结果优化完成，处理了{len(optimized_results)}个文本块")
            return optimized_results
            
        except Exception as e:
            self.logger.error(f"关键字OCR结果优化失败: {e}")
            # 返回基础结果
            basic_results = []
            for result in ocr_results:
                if isinstance(result, dict):
                    text = result.get('text', '')
                    confidence = result.get('confidence', 0.0)
                    bbox = result.get('bbox', (0, 0, 0, 0))
                elif isinstance(result, list) and len(result) >= 2:
                    bbox = result[0] if len(result) > 0 else (0, 0, 0, 0)
                    text = result[1] if len(result) > 1 else ''
                    confidence = result[2] if len(result) > 2 else 0.0
                else:
                    continue
                
                basic_results.append(OCRTextResult(
                    text=text,
                    confidence=confidence,
                    bbox=bbox,
                    original_text=text
                ))
            
            return basic_results
    
    def _preprocess_text(self, text: str) -> str:
        """
        预处理文本，进行错误修正
        
        Args:
            text: 原始文本
            
        Returns:
            str: 处理后的文本
        """
        if not text:
            return text
        
        processed_text = text
        
        # 应用错误修正映射
        for error_char, correct_char in self.error_corrections.items():
            processed_text = processed_text.replace(error_char, correct_char)
        
        return processed_text


# 全局实例管理
_keyword_optimizer_instance = None


def get_keyword_optimizer() -> KeywordOCROptimizer:
    """
    获取关键字OCR优化器单例实例
    
    Returns:
        KeywordOCROptimizer: 关键字OCR优化器实例
    """
    global _keyword_optimizer_instance
    if _keyword_optimizer_instance is None:
        _keyword_optimizer_instance = KeywordOCROptimizer()
    return _keyword_optimizer_instance