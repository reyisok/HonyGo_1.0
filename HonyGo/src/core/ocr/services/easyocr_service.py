#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EasyOCR服务类
基于EasyOCR官方API实现统一的OCR接口
支持文本检测、识别、批量处理等功能
@author: Mr.Rey Copyright © 2025
@created: 2025-01-14 15:30:00
@modified: 2025-01-14 15:30:00
@version: 1.0.0
"""

import base64
import gc
import io
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import easyocr
import numpy as np
import psutil
import torch
from PIL import Image

from src.core.ocr.utils.ocr_download_interceptor import (
    get_model_status,
    start_download_interception,
    stop_download_interception
)
from src.ui.services.logging_service import get_logger
from src.ui.services.cross_process_log_bridge import create_cross_process_handler


class EasyOCRService:
    """
    EasyOCR服务类
    提供统一的OCR识别接口，支持多种图像格式和优化选项
    """
    
    def __init__(self, languages: List[str] = None, gpu: bool = True, model_storage_directory: str = None):
        """
        初始化EasyOCR服务
        
        Args:
            languages: 支持的语言列表，默认为['ch_sim', 'en']
            gpu: 是否使用GPU加速
            model_storage_directory: 模型存储目录
        """
        self.logger = get_logger("EasyOCRService", "OCR")
        
        # 为EasyOCR服务添加跨进程日志处理器
        try:
            cross_process_handler = create_cross_process_handler(source="EasyOCRService")
            self.logger.addHandler(cross_process_handler)
        except Exception as e:
            self.logger.warning(f"EasyOCR服务添加跨进程日志处理器失败: {e}")
        self.languages = languages or ['ch_sim', 'en']
        self.gpu = gpu and torch.cuda.is_available()
        self.model_storage_directory = model_storage_directory
        self.reader = None
        self._initialize_reader()
    
    def _initialize_reader(self) -> None:
        """
        初始化EasyOCR读取器
        """
        try:
            self.logger.info("开始初始化EasyOCR读取器")
            
            # 启动下载拦截
            start_download_interception()
            
            # 检查模型存储目录
            if self.model_storage_directory:
                if not os.path.exists(self.model_storage_directory):
                    self.logger.warning(f"模型存储目录不存在: {self.model_storage_directory}")
                    os.makedirs(self.model_storage_directory, exist_ok=True)
                    self.logger.info(f"已创建模型存储目录: {self.model_storage_directory}")
                else:
                    self.logger.info(f"使用模型存储目录: {self.model_storage_directory}")
            
            # 检查模型状态
            model_status = get_model_status()
            if not model_status.get('all_models_available', False):
                self.logger.warning("部分OCR模型不可用，可能影响识别效果")
            
            # 初始化EasyOCR读取器
            kwargs = {
                'lang_list': self.languages,
                'gpu': self.gpu
            }
            
            if self.model_storage_directory:
                kwargs['model_storage_directory'] = self.model_storage_directory
            
            self.logger.info(f"正在创建EasyOCR Reader，参数: {kwargs}")
            self.reader = easyocr.Reader(**kwargs)
            self.logger.info(f"EasyOCR服务初始化成功，语言: {self.languages}, GPU: {self.gpu}")
            
        except Exception as e:
            self.logger.error(f"EasyOCR服务初始化失败: {e}")
            import traceback
            self.logger.error(f"详细错误堆栈: {traceback.format_exc()}")
            raise
        finally:
            # 停止下载拦截
            stop_download_interception()
    
    def recognize_text(self, image_data: Union[str, bytes, np.ndarray, Image.Image], **kwargs) -> List[Tuple[List[List[int]], str, float]]:
        """
        识别图像中的文本
        
        Args:
            image_data: 图像数据，支持多种格式
            **kwargs: EasyOCR的其他参数
        
        Returns:
            识别结果列表，每个元素包含 (边界框, 文本, 置信度)
        """
        if not self.reader:
            raise RuntimeError("EasyOCR读取器未初始化")
        
        try:
            # 处理不同格式的图像数据
            processed_image = self._process_image_data(image_data)
            
            # 执行OCR识别
            start_time = time.time()
            results = self.reader.readtext(processed_image, **kwargs)
            end_time = time.time()
            
            self.logger.debug(f"OCR识别完成，耗时: {end_time - start_time:.3f}秒，识别到 {len(results)} 个文本区域")
            
            return results
            
        except Exception as e:
            self.logger.error(f"OCR识别失败: {e}")
            raise
    
    def _process_image_data(self, image_data: Union[str, bytes, np.ndarray, Image.Image]) -> Union[str, np.ndarray]:
        """
        处理不同格式的图像数据
        
        Args:
            image_data: 输入的图像数据
        
        Returns:
            处理后的图像数据
        """
        if isinstance(image_data, str):
            # 如果是base64字符串，解码为numpy数组
            if image_data.startswith('data:image'):
                # 处理data URL格式
                header, data = image_data.split(',', 1)
                image_bytes = base64.b64decode(data)
            else:
                # 直接是base64编码
                image_bytes = base64.b64decode(image_data)
            
            # 转换为PIL Image再转为numpy数组
            pil_image = Image.open(io.BytesIO(image_bytes))
            return np.array(pil_image)
            
        elif isinstance(image_data, bytes):
            # 字节数据转换为numpy数组
            pil_image = Image.open(io.BytesIO(image_data))
            return np.array(pil_image)
            
        elif isinstance(image_data, Image.Image):
            # PIL Image转换为numpy数组
            return np.array(image_data)
            
        elif isinstance(image_data, np.ndarray):
            # 直接返回numpy数组
            return image_data
            
        else:
            raise ValueError(f"不支持的图像数据格式: {type(image_data)}")
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        获取内存使用情况
        
        Returns:
            内存使用信息字典
        """
        memory_info = {}
        
        try:
            process = psutil.Process()
            memory_info['system_memory_mb'] = process.memory_info().rss / 1024 / 1024
            
            if self.gpu and torch.cuda.is_available():
                memory_info['gpu_memory_allocated_mb'] = torch.cuda.memory_allocated() / 1024 / 1024
                memory_info['gpu_memory_cached_mb'] = torch.cuda.memory_reserved() / 1024 / 1024
                memory_info['gpu_memory_free_mb'] = (torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_reserved()) / 1024 / 1024
            
        except Exception as e:
            self.logger.warning(f"获取内存使用情况失败: {e}")
        
        return memory_info
    
    def cleanup(self) -> None:
        """
        清理资源
        """
        try:
            if self.reader:
                del self.reader
                self.reader = None
            
            # 清理GPU内存
            if self.gpu and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # 强制垃圾回收
            gc.collect()
            
            self.logger.info("EasyOCR服务资源清理完成")
            
        except Exception as e:
            # 防止在析构时logger不可用的情况
            try:
                self.logger.error(f"EasyOCR服务资源清理失败: {e}")
            except:
                try:
                    self.logger.error(f"EasyOCR服务资源清理失败: {e}")
                except:
                    pass
    
    def __del__(self):
        """
        析构函数，确保资源被正确释放
        """
        self.cleanup()


if __name__ == "__main__":
    # EasyOCRService类仅供OCR池服务内部使用
    # 请使用OCR池管理器进行OCR识别
    test_logger = get_logger("EasyOCRServiceTest", "OCR")
    test_logger.info("EasyOCRService类仅供OCR池服务内部使用")
    test_logger.info("请使用OCR池管理器进行OCR识别")