# -*- coding: utf-8 -*-
"""
HonyGo 轻量化任务执行服务
提供轻量化的任务执行功能
@author: Mr.Rey Copyright © 2025
"""

import base64
import time
import threading
from io import BytesIO
from typing import Any, Dict
from PIL import ImageGrab
from PySide6.QtCore import QObject, QTimer, Signal
from src.core.ocr.optimization.gpu_accelerator import GPUAccelerator
from src.core.ocr.optimization.image_preprocessor import ImagePreprocessor
from src.core.ocr.optimization.ocr_cache_manager import OCRCacheManager
from src.core.ocr.optimization.performance_optimizer import PerformanceOptimizer
from src.core.ocr.optimization.smart_region_predictor import SmartRegionPredictor
from src.core.ocr.services.ocr_pool_manager import get_pool_manager
from src.core.ocr.utils.keyword_matcher import KeywordMatcher, MatchStrategy
from src.ui.services.coordinate_service import get_coordinate_service
from src.ui.services.image_preprocessing_service import ImagePreprocessingService
from src.ui.services.logging_service import get_logger
from src.ui.services.roi_service import ROIService
from src.ui.services.unified_timer_service import get_timer_service


class LightweightTaskExecutionService(QObject):
    """
    轻量化任务执行服务
    """
    
    # 信号定义
    log_message = Signal(str)
    ocr_test_completed = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("LightweightTaskExecutionService", "Application")
        self.coordinate_service = get_coordinate_service()
        self.keyword_matcher = KeywordMatcher()
        self.ocr_host = "127.0.0.1"
        self.ocr_port = 8900
        
    def execute_ocr_test(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行OCR识别测试
        """
        try:
            start_time = time.time()
            target_text = config.get('target_text', '测试文本')
            
            self.logger.info(f"开始OCR识别测试 - 使用统一OCR池服务 {self.ocr_host}:{self.ocr_port}")
            self.log_message.emit("正在进行全屏截图...")
            
            # 1. 全屏截图
            screenshot_start = time.time()
            screenshot = ImageGrab.grab()
            if not screenshot:
                self.log_message.emit("截图失败")
                return {'success': False, 'error': '截图失败'}
            
            screenshot_time = time.time() - screenshot_start
            self.log_message.emit(f"截图完成，开始OCR识别...")
            
            # 2. OCR识别（使用统一OCR池服务）
            ocr_start = time.time()
            
            # 将截图转换为base64
            buffer = BytesIO()
            screenshot.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # 通过OCR池管理器进行识别
            try:
                pool_manager = get_pool_manager()
                ocr_data = pool_manager.process_ocr_request(image_base64)
                
                if not ocr_data or not ocr_data.get('success'):
                    error_msg = ocr_data.get('error', 'OCR处理失败') if ocr_data else 'OCR池管理器不可用'
                    self.logger.error(f"OCR服务请求失败: {error_msg}")
                    self.log_message.emit(f"OCR服务请求失败: {error_msg}")
                    return {'success': False, 'error': f'OCR服务请求失败: {error_msg}'}
                
                ocr_results = ocr_data.get('result', [])
            except Exception as e:
                self.logger.error(f"OCR池管理器调用失败: {str(e)}")
                self.log_message.emit(f"OCR池管理器调用失败: {str(e)}")
                return {'success': False, 'error': f'OCR池管理器调用失败: {str(e)}'}
            
            if not ocr_results:
                self.logger.warning("OCR识别未找到任何文本")
                self.log_message.emit("OCR识别失败或未识别到文本")
                return {'success': False, 'error': 'OCR识别失败'}
            
            ocr_time = time.time() - ocr_start
            self.logger.info(f"OCR识别完成，检测到 {len(ocr_results)} 个文本区域")
            self.log_message.emit(f"OCR识别完成，检测到 {len(ocr_results)} 个文本区域")
            
            # 3. 关键字匹配（使用统一关键字匹配器）
            match_start = time.time()
            match_result = self.keyword_matcher.match_keyword(
                target_keyword=target_text,
                ocr_results=ocr_results,
                strategy=MatchStrategy.CONTAINS,
                min_confidence=0.5
            )
            
            match_time = time.time() - match_start
            total_time = time.time() - start_time
            
            if match_result.found:
                self.logger.info(f"关键字匹配成功 - 总耗时: {total_time:.3f}秒")
                self.log_message.emit(
                    f"[MATCH] 匹配成功！检测到关键字 '{target_text}' "
                    f"匹配文本: '{match_result.matched_text}'"
                )
                self.log_message.emit(f"[SUCCESS] 测试成功！总耗时: {total_time:.3f}秒")
                
                # 构建成功结果
                result_data = {
                    'success': True,
                    'target_text': target_text,
                    'matched_text': match_result.matched_text,
                    'total_time': total_time,
                    'screenshot_time': screenshot_time,
                    'ocr_time': ocr_time,
                    'match_time': match_time,
                    'ocr_results_count': len(ocr_results)
                }
                if match_result.position:
                    # 计算逻辑坐标中心点
                    logical_center_x = match_result.position[0] + match_result.position[2] // 2
                    logical_center_y = match_result.position[1] + match_result.position[3] // 2
                    
                    self.logger.info(f"计算逻辑坐标中心点: ({logical_center_x}, {logical_center_y})")
                    
                    result_data['position'] = (logical_center_x, logical_center_y)  # 逻辑坐标
                    result_data['bbox'] = match_result.position  # 原始边界框
                
                self.ocr_test_completed.emit(result_data)
                return result_data
            else:
                self.logger.warning(f"关键字匹配失败 - 未找到目标文本: '{target_text}'")
                self.log_message.emit(f"❌ 测试失败：未找到目标文本 '{target_text}'")
                self.log_message.emit(f"总耗时: {total_time:.3f}秒，共识别到 {len(ocr_results)} 个文本块")
                
                # 构建失败结果
                result_data = {
                    'success': False,
                    'target_text': target_text,
                    'total_time': total_time,
                    'screenshot_time': screenshot_time,
                    'ocr_time': ocr_time,
                    'match_time': match_time,
                    'error': f'未找到目标文本: {target_text}',
                    'ocr_results_count': len(ocr_results)
                }
                self.ocr_test_completed.emit(result_data)
                return result_data
                
        except Exception as e:
            total_time = time.time() - start_time if 'start_time' in locals() else 0
            
            self.logger.error(f"OCR识别测试异常 - 耗时: {total_time:.3f}秒, 错误: {e}", exc_info=True)
            self.log_message.emit(f"测试异常 (耗时: {total_time:.3f}秒): {str(e)}")
            
            # 构建异常结果
            result_data = {
                'success': False,
                'error': str(e),
                'total_time': total_time
            }
            self.ocr_test_completed.emit(result_data)
            return result_data