#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR性能优化服务
实现模型预热机制和GPU加速支持

@author: Mr.Rey Copyright © 2025
"""

import base64
import gc
import io
import os
import sys
import threading
import time
from typing import Any, Dict, List
import GPUtil
import psutil
import pynvml
import tensorflow as tf
import torch
from PIL import Image
from PySide6.QtCore import QObject, QTimer, Signal
from src.config.optimization_config import get_config_manager, get_optimization_config
from src.core.ocr.services.ocr_pool_manager import get_pool_manager
from src.ui.services.logging_service import get_logger
from src.ui.services.unified_timer_service import get_timer_service


class OCRPerformanceService(QObject):
    """
    OCR性能优化服务
    """
    
    # 信号定义
    model_prewarmed = Signal(str)
    performance_optimized = Signal(dict)
    gpu_status_changed = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("OCRPerformanceService", "Performance")
        
        # 性能配置
        self.config = get_optimization_config()
        
        # 模型预热状态
        self.model_warmup_status = {
            "easyocr_warmed": False,
            "warmup_time": 0.0,
            "last_warmup": 0.0
        }
        
        # 性能统计
        self.performance_stats = {
            "total_requests": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "min_processing_time": float('inf'),
            "max_processing_time": 0.0,
            "recent_times": []
        }
        
        # GPU状态
        self.gpu_status = {
            "available": False,
            "device_count": 0,
            "memory_usage": {},
            "utilization": {}
        }
        
        # 初始化GPU监控
        self._initialize_gpu_monitoring()
    
    def _initialize_gpu_monitoring(self):
        """
        初始化GPU监控
        """
        try:
            # 检查CUDA可用性
            if torch.cuda.is_available():
                self.gpu_status["available"] = True
                self.gpu_status["device_count"] = torch.cuda.device_count()
                
                # 初始化NVIDIA-ML
                try:
                    pynvml.nvmlInit()
                    self.logger.info(f"GPU监控初始化成功，检测到 {self.gpu_status['device_count']} 个GPU设备")
                except Exception as e:
                    self.logger.warning(f"NVIDIA-ML初始化失败: {e}")
            else:
                self.logger.info("未检测到可用的GPU设备")
                
        except Exception as e:
            self.logger.error(f"GPU监控初始化失败: {e}")
    
    def warmup_models(self):
        """
        预热OCR模型
        """
        try:
            self.logger.info("开始OCR模型预热...")
            start_time = time.time()
            
            # 创建测试图像
            try:
                # 创建一个简单的测试图像
                test_image = Image.new('RGB', (200, 100), color='white')
                
                # 转换为字节数据
                img_buffer = io.BytesIO()
                test_image.save(img_buffer, format='PNG')
                test_image_data = img_buffer.getvalue()
                
                # 将测试图像转换为base64
                test_image_base64 = base64.b64encode(test_image_data).decode('utf-8')
                
                # 通过OCR池管理器进行预热测试
                try:
                    pool_manager = get_pool_manager()
                    result = pool_manager.process_ocr_request(test_image_base64)
                    
                    if result and result.get('success'):
                        # 预热成功
                        warmup_time = time.time() - start_time
                        self.model_warmup_status.update({
                            "easyocr_warmed": True,
                            "warmup_time": warmup_time,
                            "last_warmup": time.time()
                        })
                        
                        self.model_prewarmed.emit(f"OCR池服务模型预热完成，耗时: {warmup_time:.2f}秒")
                        self.logger.info(f"OCR池服务模型预热完成，耗时: {warmup_time:.2f}秒")
                    else:
                        error_msg = result.get('error', '预热失败') if result else 'OCR池管理器不可用'
                        self.logger.error(f"模型预热失败: {error_msg}")
                        return
                        
                except Exception as e:
                    self.logger.error(f"OCR池管理器调用失败: {str(e)}")
                    return
                    
            except Exception as e:
                self.logger.error(f"OCR预热请求处理失败: {str(e)}")
                return
            
        except Exception as e:
            self.logger.error(f"模型预热执行失败: {e}")
    
    def optimize_for_realtime(self):
        """
        为实时处理优化配置
        """
        try:
            realtime_config = {
                "batch_size": 1,
                "num_threads": min(4, os.cpu_count()),
                "use_gpu": self.gpu_status["available"],
                "precision": "fp16" if self.gpu_status["available"] else "fp32",
                "cache_enabled": True,
                "preprocessing": {
                    "resize_method": "fast",
                    "quality_enhancement": False
                }
            }
            
            # 应用配置
            config_manager = get_config_manager()
            config_manager.update_config(realtime_config)
            
            self.performance_optimized.emit({
                "mode": "realtime",
                "config": realtime_config
            })
            
            self.logger.info("已优化为实时处理模式")
            
        except Exception as e:
            self.logger.error(f"实时优化配置失败: {e}")
    
    def optimize_for_accuracy(self):
        """
        为准确性优化配置
        """
        try:
            accuracy_config = {
                "batch_size": 4,
                "num_threads": os.cpu_count(),
                "use_gpu": self.gpu_status["available"],
                "precision": "fp32",
                "cache_enabled": True,
                "preprocessing": {
                    "resize_method": "high_quality",
                    "quality_enhancement": True,
                    "noise_reduction": True
                }
            }
            
            # 应用配置
            config_manager = get_config_manager()
            config_manager.update_config(accuracy_config)
            
            self.performance_optimized.emit({
                "mode": "accuracy",
                "config": accuracy_config
            })
            
            self.logger.info("已优化为准确性模式")
            
        except Exception as e:
            self.logger.error(f"准确性优化配置失败: {e}")
    
    def record_processing_time(self, processing_time: float):
        """
        记录处理时间
        
        Args:
            processing_time: 处理时间（秒）
        """
        try:
            self.performance_stats["total_requests"] += 1
            self.performance_stats["total_processing_time"] += processing_time
            
            # 更新最小和最大处理时间
            self.performance_stats["min_processing_time"] = min(
                self.performance_stats["min_processing_time"], processing_time
            )
            self.performance_stats["max_processing_time"] = max(
                self.performance_stats["max_processing_time"], processing_time
            )
            
            # 计算平均处理时间
            self.performance_stats["average_processing_time"] = (
                self.performance_stats["total_processing_time"] / 
                self.performance_stats["total_requests"]
            )
            
            # 保持最近100次的处理时间
            self.performance_stats["recent_times"].append(processing_time)
            if len(self.performance_stats["recent_times"]) > 100:
                self.performance_stats["recent_times"].pop(0)
            
        except Exception as e:
            self.logger.error(f"处理时间记录失败: {e}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        获取性能报告
        
        Returns:
            Dict[str, Any]: 性能报告
        """
        try:
            # 更新GPU状态
            self._update_gpu_status()
            
            return {
                "model_warmup": self.model_warmup_status,
                "performance_stats": self.performance_stats,
                "gpu_status": self.gpu_status,
                "system_info": {
                    "cpu_count": os.cpu_count(),
                    "memory_usage": psutil.virtual_memory()._asdict(),
                    "cpu_usage": psutil.cpu_percent()
                },
                "recommendations": self._generate_recommendations()
            }
            
        except Exception as e:
            self.logger.error(f"性能报告生成失败: {e}")
            return {}
    
    def _generate_recommendations(self) -> List[str]:
        """
        生成性能优化建议
        
        Returns:
            List[str]: 优化建议列表
        """
        recommendations = []
        
        try:
            # 检查平均处理时间
            avg_time = self.performance_stats.get("average_processing_time", 0)
            if avg_time > 2.0:
                recommendations.append("平均处理时间较长，建议启用GPU加速或降低图像分辨率")
            
            # 检查GPU可用性
            if not self.gpu_status["available"]:
                recommendations.append("未检测到GPU，建议使用支持CUDA的显卡以提升性能")
            
            # 检查内存使用
            memory = psutil.virtual_memory()
            if memory.percent > 80:
                recommendations.append("系统内存使用率较高，建议关闭其他应用程序")
            
            # 检查模型预热状态
            if not self.model_warmup_status["easyocr_warmed"]:
                recommendations.append("建议进行模型预热以提升首次识别速度")
            
            # 检查处理时间变化
            recent_times = self.performance_stats.get("recent_times", [])
            if len(recent_times) > 10:
                recent_avg = sum(recent_times[-10:]) / 10
                if recent_avg > avg_time * 1.5:
                    recommendations.append("最近处理速度下降，建议检查系统资源使用情况")
            
        except Exception as e:
            self.logger.error(f"生成优化建议失败: {e}")
        
        return recommendations
    
    def _update_gpu_status(self):
        """
        更新GPU状态信息
        """
        try:
            if not self.gpu_status["available"]:
                return
            
            # 更新GPU内存和利用率信息
            for i in range(self.gpu_status["device_count"]):
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    
                    # 内存信息
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    self.gpu_status["memory_usage"][i] = {
                        "total": mem_info.total,
                        "used": mem_info.used,
                        "free": mem_info.free,
                        "usage_percent": (mem_info.used / mem_info.total) * 100
                    }
                    
                    # 利用率信息
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    self.gpu_status["utilization"][i] = {
                        "gpu": util.gpu,
                        "memory": util.memory
                    }
                    
                except Exception as e:
                    self.logger.warning(f"获取GPU {i} 状态失败: {e}")
            
        except Exception as e:
            self.logger.error(f"GPU状态更新失败: {e}")
    
    def update_config(self, config: Dict[str, Any]):
        """
        更新性能配置
        
        Args:
            config: 新的配置
        """
        try:
            self.config.update(config)
            
            # 应用新配置
            config_manager = get_config_manager()
            config_manager.update_config(config)
            
            self.logger.info(f"性能配置已更新: {config}")
            
        except Exception as e:
            self.logger.error(f"配置更新失败: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            Dict[str, Any]: 当前配置
        """
        return self.config.copy()
    
    def cleanup(self):
        """
        清理服务资源
        """
        try:
            # 清理GPU监控资源
            if self.gpu_status["available"]:
                try:
                    pynvml.nvmlShutdown()
                except Exception as e:
                    self.logger.warning(f"NVIDIA-ML清理失败: {e}")
            
            # 清理统计数据
            self.performance_stats["recent_times"].clear()
            
            self.logger.info("OCR性能优化服务资源清理完成")
            
        except Exception as e:
            self.logger.error(f"OCR性能优化服务清理失败: {e}")