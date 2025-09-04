#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU加速器模块

@author: Mr.Rey Copyright © 2025
@description: 提供GPU加速配置和检测功能，优化OCR模型使用GPU进行加速处理
@version: 1.0.0
@created: 2025-01-31
@modified: 2025-09-03
"""

import json
import logging
import os
import platform
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2
import pynvml
import tensorflow as tf
import torch
from src.ui.services.logging_service import get_logger


class AccelerationType(Enum):
    """加速类型枚举"""
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"
    OPENCL = "opencl"


class GPUVendor(Enum):
    """GPU厂商枚举"""
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    APPLE = "apple"
    UNKNOWN = "unknown"


@dataclass
class GPUInfo:
    """GPU信息数据类"""
    vendor: GPUVendor
    name: str
    memory_total: int  # MB
    memory_free: int   # MB
    compute_capability: Optional[str] = None
    device_id: int = 0


@dataclass
class AccelerationConfig:
    """加速配置数据类"""
    enabled: bool = False
    acceleration_type: AccelerationType = AccelerationType.CPU
    device_id: int = 0
    precision: str = "fp32"
    batch_size: int = 1


class GPUAccelerator:
    """GPU加速器类"""
    
    def __init__(self):
        """初始化GPU加速器"""
        self.logger = get_logger(__name__)
        self.gpu_info: List[GPUInfo] = []
        self.available_accelerations: List[AccelerationType] = []
        self.current_config: Optional[AccelerationConfig] = None
        self.performance_stats = {
            'avg_inference_time': 0.0,
            'memory_usage': 0.0,
            'gpu_utilization': 0.0
        }
        
        # 检测可用的GPU和加速类型
        self._detect_gpus()
        self._detect_accelerations()
    
    def _detect_gpus(self):
        """检测可用的GPU"""
        try:
            # 检测NVIDIA GPU
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    gpu_info = GPUInfo(
                        vendor=GPUVendor.NVIDIA,
                        name=props.name,
                        memory_total=props.total_memory // (1024 * 1024),
                        memory_free=props.total_memory // (1024 * 1024),
                        compute_capability=f"{props.major}.{props.minor}",
                        device_id=i
                    )
                    self.gpu_info.append(gpu_info)
            
            # 检测Apple MPS
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                gpu_info = GPUInfo(
                    vendor=GPUVendor.APPLE,
                    name="Apple Silicon GPU",
                    memory_total=8192,  # 估算值
                    memory_free=8192,
                    device_id=0
                )
                self.gpu_info.append(gpu_info)
                
        except Exception as e:
            self.logger.error(f"GPU detection failed: {e}")
    
    def _detect_accelerations(self):
        """检测可用的加速类型"""
        self.available_accelerations = [AccelerationType.CPU]
        
        try:
            # 检测CUDA
            if torch.cuda.is_available():
                self.available_accelerations.append(AccelerationType.CUDA)
            
            # 检测MPS
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                self.available_accelerations.append(AccelerationType.MPS)
                
        except Exception as e:
            self.logger.error(f"Acceleration detection failed: {e}")
    
    def get_device_string(self) -> str:
        """获取设备字符串"""
        if not self.current_config or not self.current_config.enabled:
            return "cpu"
        
        if self.current_config.acceleration_type == AccelerationType.CUDA:
            return f"cuda:{self.current_config.device_id}"
        elif self.current_config.acceleration_type == AccelerationType.MPS:
            return "mps"
        else:
            return "cpu"
    
    def get_easyocr_gpu_config(self) -> Dict[str, Any]:
        """获取EasyOCR GPU配置"""
        if not self.current_config or not self.current_config.enabled:
            return {'gpu': False}
        
        if self.current_config.acceleration_type == AccelerationType.CUDA:
            return {
                'gpu': True,
                'device': self.current_config.device_id
            }
        else:
            return {'gpu': False}
    
    def get_opencv_gpu_config(self) -> Dict[str, Any]:
        """获取OpenCV GPU配置"""
        if not self.current_config or not self.current_config.enabled:
            return {'use_gpu': False}
        
        if self.current_config.acceleration_type == AccelerationType.CUDA:
            return {
                'use_gpu': True,
                'gpu_device_id': self.current_config.device_id
            }
        else:
            return {'use_gpu': False}
    
    def monitor_gpu_usage(self) -> Dict[str, Any]:
        """监控GPU使用情况"""
        usage_info = {
            'gpu_utilization': 0.0,
            'memory_used': 0.0,
            'memory_total': 0.0,
            'temperature': 0.0,
            'power_usage': 0.0
        }
        
        try:
            if not self.current_config or not self.current_config.enabled:
                return usage_info
            
            device_id = self.current_config.device_id
            
            if self.current_config.acceleration_type == AccelerationType.CUDA:
                # PyTorch CUDA内存信息
                if torch.cuda.is_available() and device_id < torch.cuda.device_count():
                    memory_allocated = torch.cuda.memory_allocated(device_id) / (1024 ** 3)  # GB
                    memory_reserved = torch.cuda.memory_reserved(device_id) / (1024 ** 3)   # GB
                    memory_total = torch.cuda.get_device_properties(device_id).total_memory / (1024 ** 3)  # GB
                    
                    usage_info['memory_used'] = memory_allocated
                    usage_info['memory_total'] = memory_total
                
                # NVML详细信息
                try:
                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)
                    
                    # GPU利用率
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    usage_info['gpu_utilization'] = util.gpu
                    
                    # 温度
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    usage_info['temperature'] = temp
                    
                    # 功耗
                    power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW to W
                    usage_info['power_usage'] = power
                    
                except ImportError:
                    pass  # pynvml not available
                except Exception as e:
                    self.logger.error(f"Failed to get detailed GPU info: {e}")
            
        except Exception as e:
            self.logger.error(f"GPU monitoring failed: {e}")
        
        return usage_info
    
    def optimize_for_ocr(self) -> Dict[str, Any]:
        """为OCR任务优化GPU配置"""
        try:
            recommendations = {
                'batch_size': 1,
                'precision': 'fp32',
                'memory_optimization': [],
                'performance_tips': []
            }
            
            if not self.current_config or not self.current_config.enabled:
                recommendations['performance_tips'].append("Consider enabling GPU acceleration for better performance")
                return recommendations
            
            acc_type = self.current_config.acceleration_type
            
            if acc_type == AccelerationType.CUDA:
                # CUDA优化建议
                gpu_info = next((gpu for gpu in self.gpu_info if gpu.device_id == self.current_config.device_id), None)
                
                if gpu_info:
                    # 根据GPU内存调整批处理大小
                    if gpu_info.memory_total > 8000:  # > 8GB
                        recommendations['batch_size'] = 4
                    elif gpu_info.memory_total > 4000:  # > 4GB
                        recommendations['batch_size'] = 2
                    
                    # 根据计算能力调整精度
                    if gpu_info.compute_capability and gpu_info.compute_capability >= '7.0':
                        recommendations['precision'] = 'fp16'  # Tensor Cores支持
                    
                    recommendations['memory_optimization'].extend([
                        "Enable CUDA memory caching",
                        "Use memory mapping for large images",
                        "Clear GPU cache between batches"
                    ])
                    
                    recommendations['performance_tips'].extend([
                        "Use CUDA streams for async processing",
                        "Consider TensorRT optimization for production",
                        "Profile memory usage to avoid OOM errors"
                    ])
            
            elif acc_type == AccelerationType.MPS:
                # MPS优化建议
                recommendations['batch_size'] = 2
                recommendations['precision'] = 'fp32'  # MPS目前主要支持fp32
                
                recommendations['performance_tips'].extend([
                    "Use unified memory for better performance",
                    "Avoid frequent CPU-GPU transfers",
                    "Consider image preprocessing on GPU"
                ])
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"OCR optimization failed: {e}")
            return {'batch_size': 1, 'precision': 'fp32', 'memory_optimization': [], 'performance_tips': []}
    
    def get_acceleration_info(self) -> Dict[str, Any]:
        """获取加速信息"""
        return {
            'available_accelerations': [acc.value for acc in self.available_accelerations],
            'current_acceleration': self.current_config.acceleration_type.value if self.current_config else 'cpu',
            'gpu_info': [{
                'vendor': gpu.vendor.value,
                'name': gpu.name,
                'memory_total': gpu.memory_total,
                'compute_capability': gpu.compute_capability,
                'device_id': gpu.device_id
            } for gpu in self.gpu_info],
            'performance_stats': self.performance_stats.copy(),
            'config': {
                'enabled': self.current_config.enabled if self.current_config else False,
                'device_id': self.current_config.device_id if self.current_config else 0,
                'precision': self.current_config.precision if self.current_config else 'fp32',
                'batch_size': self.current_config.batch_size if self.current_config else 1
            }
        }
    
    def close(self):
        """关闭GPU加速器"""
        try:
            # 清理GPU内存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as e:
            self.logger.error(f"GPU cleanup failed: {e}")


if __name__ == '__main__':
    # 测试GPU加速器
    logger = get_logger("GPUAcceleratorTest", "OCR")
    accelerator = GPUAccelerator()
    
    logger.info("GPU Acceleration Info:")
    info = accelerator.get_acceleration_info()
    logger.info(f"  Available: {info['available_accelerations']}")
    logger.info(f"  Current: {info['current_acceleration']}")
    logger.info(f"  Device: {accelerator.get_device_string()}")
    
    logger.info(f"EasyOCR Config: {accelerator.get_easyocr_gpu_config()}")
    logger.info(f"OpenCV Config: {accelerator.get_opencv_gpu_config()}")
    
    logger.info(f"OCR Optimization: {accelerator.optimize_for_ocr()}")
    
    logger.info(f"GPU Usage: {accelerator.monitor_gpu_usage()}")
    
    accelerator.close()