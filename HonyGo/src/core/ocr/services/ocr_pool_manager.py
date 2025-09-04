#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR实例池管理器
负责OCR实例的创建、管理、调度和资源分配
"""

import threading
import time
import uuid
import gc
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor, Future
import psutil
import torch
from src.core.ocr.port_manager import get_port_manager
from src.ui.services.logging_service import get_logger
from src.config.optimization_config_manager import OptimizationConfigManager
from src.config.ocr_pool_config import get_ocr_pool_config, OCRPoolConfig
from src.config.ocr_pool_validator import validate_ocr_pool_config, parameter_validator, config_consistency_checker
from src.config.ocr_logging_config import OCRLoggerMixin, log_ocr_operation
from src.core.ocr.services.comprehensive_ocr_optimizer import get_comprehensive_optimizer, OptimizationMode
from src.core.ocr.services.easyocr_service import EasyOCRService
from src.ui.services.cross_process_log_bridge import create_cross_process_handler

# 获取日志记录器 - 输出到主程序运行日志
logger = get_logger('OCRPoolManager', 'Application')

# 为OCR池管理器添加跨进程日志处理器
try:
    cross_process_handler = create_cross_process_handler(source="OCRPoolManager")
    logger.addHandler(cross_process_handler)
except Exception as e:
    logger.warning(f"添加跨进程日志处理器失败: {e}")

class OCRInstanceStatus(Enum):
    """OCR实例状态枚举"""
    STARTING = "starting"
    READY = "ready"
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"      # 实例正在处理请求
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"

@dataclass
class OCRInstanceInfo:
    """OCR实例信息"""
    instance_id: str
    port: int
    service: Optional[EasyOCRService] = None
    status: OCRInstanceStatus = OCRInstanceStatus.STARTING
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    processed_requests: int = 0
    request_count: int = 0  # 总请求数
    error_count: int = 0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    response_times: List[float] = field(default_factory=list)
    
    def update_usage_stats(self):
        """更新使用统计"""
        try:
            process = psutil.Process()
            self.memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            self.cpu_usage = process.cpu_percent()
        except Exception as e:
            logger.warning(f"更新实例 {self.instance_id} 使用统计失败: {e}")
    
    def get_average_response_time(self) -> float:
        """获取平均响应时间"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    def add_response_time(self, response_time: float):
        """添加响应时间记录"""
        self.response_times.append(response_time)
        # 只保留最近100次记录
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]
    
    def get_load_score(self) -> float:
        """计算实例负载评分（越低越好）"""
        # 基础负载评分
        base_score = self.processed_requests * 0.3
        
        # 响应时间权重
        avg_response_time = self.get_average_response_time()
        response_score = avg_response_time * 0.4
        
        # 错误率权重
        error_rate = self.error_count / max(self.processed_requests, 1)
        error_score = error_rate * 0.2
        
        # 内存使用权重
        memory_score = self.memory_usage * 0.1
        
        return base_score + response_score + error_score + memory_score
    
    def optimize_memory(self):
        """优化实例内存使用"""
        try:
            if self.service and hasattr(self.service, 'optimize_memory') and callable(getattr(self.service, 'optimize_memory')):
                self.service.optimize_memory()
            
            # 强制垃圾回收
            gc.collect()
            
            # 更新内存使用统计
            self.update_usage_stats()
            
        except Exception as e:
            logger.warning(f"实例 {self.instance_id} 内存优化失败: {e}")
    
    def get_memory_info(self) -> Dict[str, float]:
        """获取实例内存信息"""
        if self.service and hasattr(self.service, 'get_memory_usage'):
            return self.service.get_memory_usage()
        return {}

@dataclass
class PoolStatus:
    """实例池状态"""
    total_instances: int = 0
    running_instances: int = 0
    idle_instances: int = 0
    stopped_instances: int = 0
    error_instances: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0

class OCRPoolManager(OCRLoggerMixin):
    """OCR实例池管理器"""
    
    def __init__(self, config: Optional[OCRPoolConfig] = None):
        # 初始化父类OCRLoggerMixin
        super().__init__()
        
        # 手动初始化_logger属性（防止多重继承问题）
        self._logger = None
        
        # 使用配置文件或默认配置
        if config is None:
            config = get_ocr_pool_config()
        
        # 验证配置参数
        validate_ocr_pool_config(config)
        
        self.config = config
        self.min_instances = config.min_instances
        self.max_instances = config.max_instances
        self.instances: Dict[str, OCRInstanceInfo] = {}
        self.port_manager = get_port_manager()
        
        # 初始化OCR专用日志记录器（通过OCRLoggerMixin自动处理）
        
        # 保持向后兼容的日志记录器
        self._legacy_logger = get_logger("OCRPoolManager", "Application")
        
        # 加载优化配置
        self.config_manager = OptimizationConfigManager()
        self.optimization_config = self.config_manager.get_config()
        
        # 初始化综合优化器
        self.comprehensive_optimizer = get_comprehensive_optimizer()
        
        # 线程安全锁
        self._lock = threading.RLock()
        
        # 请求队列和线程池
        self._request_queue = Queue(maxsize=100)  # 请求队列，最大100个待处理请求
        self._executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="OCR-Worker")
        self._queue_processor_running = False
        
        # 统计信息
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self._queue_length = 0
        
        # 动态扩容管理器（延迟初始化避免循环导入）
        self._scaling_manager = None
        
        # API服务器相关属性
        self._api_server_thread = None
        self._api_server_running = False
        
        # 启动队列处理器
        self._start_queue_processor()
        
        # 初始化实例池
        self._initialize_pool()
        
        self.log_info(f"OCR实例池管理器初始化完成，最小实例数: {self.min_instances}, 最大实例数: {self.max_instances}")
        self._legacy_logger.info(f"OCR实例池管理器初始化完成，最小实例数: {self.min_instances}, 最大实例数: {self.max_instances}")
    
    def reload_config(self, config: Optional[OCRPoolConfig] = None) -> None:
        """重新加载配置
        
        Args:
            config: 新的配置对象，如果为None则重新加载默认配置
        """
        with self._lock:
            if config is None:
                from src.config.ocr_pool_config import reload_ocr_pool_config
                config = reload_ocr_pool_config()
            
            # 验证新配置
            validate_ocr_pool_config(config)
            
            old_min = self.min_instances
            old_max = self.max_instances
            
            # 更新配置
            self.config = config
            self.min_instances = config.min_instances
            self.max_instances = config.max_instances
            
            self.log_info(f"配置已重新加载: min_instances {old_min}->{self.min_instances}, max_instances {old_max}->{self.max_instances}")
            
            # 根据新配置调整实例数量
            self._adjust_instances_for_new_config()
    
    def _adjust_instances_for_new_config(self) -> None:
        """根据新配置调整实例数量"""
        current_count = len([info for info in self.instances.values() if info.status == InstanceStatus.RUNNING])
        
        if current_count < self.min_instances:
            # 需要增加实例
            needed = self.min_instances - current_count
            self.log_info(f"根据新配置需要增加 {needed} 个实例")
            for _ in range(needed):
                self.create_instance()
        
        elif current_count > self.max_instances:
            # 需要减少实例
            excess = current_count - self.max_instances
            self.log_info(f"根据新配置需要减少 {excess} 个实例")
            running_instances = [id for id, info in self.instances.items() if info.status == InstanceStatus.RUNNING]
            for i in range(min(excess, len(running_instances))):
                self.remove_instance(running_instances[i])
    
    def _start_queue_processor(self):
        """启动队列处理器"""
        if not self._queue_processor_running:
            self._queue_processor_running = True
            self._executor.submit(self._queue_processor)
            self.log_info("队列处理器已启动")
    
    def _queue_processor(self):
        """队列处理器线程"""
        while self._queue_processor_running:
            try:
                # 从队列中获取请求
                request_data = self._request_queue.get(timeout=1.0)
                if request_data is None:  # 停止信号
                    break
                
                # 处理请求
                self._process_queued_request(request_data)
                
            except Empty:
                continue
            except Exception as e:
                self.log_error(f"队列处理器错误: {e}")
    
    def _process_queued_request(self, request_data):
        """处理队列中的请求"""
        try:
            image_data = request_data.get('image_data')
            request_type = request_data.get('request_type', 'recognize')
            kwargs = request_data.get('kwargs', {})
            future = request_data.get('future')
            
            # 处理OCR请求
            result = self.process_ocr_request(image_data, request_type, **kwargs)
            
            # 设置结果
            if future and not future.cancelled():
                future.set_result(result)
                
        except Exception as e:
            # 设置异常
            if 'future' in request_data and not request_data['future'].cancelled():
                request_data['future'].set_exception(e)
    
    def _initialize_pool(self):
        """初始化实例池"""
        try:
            for _ in range(self.min_instances):
                self.create_instance()
            self.log_info(f"实例池初始化完成，创建了 {self.min_instances} 个实例")
        except Exception as e:
            self.log_error(f"实例池初始化失败: {e}")
    

    
    @config_consistency_checker
    def create_instance(self) -> Optional[str]:
        """创建新的OCR实例"""
        with self._lock:
            if len(self.instances) >= self.max_instances:
                self.log_warning("已达到最大实例数限制，无法创建新实例")
                return None
            
            try:
                # 生成实例ID
                instance_id = f"ocr_instance_{uuid.uuid4().hex[:8]}"
                
                # 分配端口
                port = self.port_manager.allocate_port(instance_id)
                if port is None:
                    self.log_error("无法分配端口，创建实例失败")
                    return None
                
                # 创建实例信息
                instance_info = OCRInstanceInfo(
                    instance_id=instance_id,
                    port=port
                )
                
                # 创建EasyOCR服务
                try:
                    self.log_info(f"开始创建EasyOCR服务，实例ID: {instance_id}")
                    
                    # 使用优化配置创建服务
                    service = EasyOCRService(
                        languages=['ch_sim', 'en'],
                        gpu=self.optimization_config.gpu.enabled,
                        model_storage_directory=self.optimization_config.model_config.model_storage_directory
                    )
                    
                    self.log_info(f"EasyOCR服务创建成功，实例ID: {instance_id}")
                    
                    instance_info.service = service
                    instance_info.status = OCRInstanceStatus.READY
                    
                    # 执行初始内存优化
                    instance_info.optimize_memory()
                    
                    # 添加到实例池
                    self.instances[instance_id] = instance_info
                    
                    self.log_info(f"成功创建OCR实例: {instance_id}, 端口: {port}")
                    return instance_id
                    
                except Exception as e:
                    # 创建服务失败，释放端口
                    self.port_manager.release_port(port)
                    self.log_error(f"创建OCR服务失败: {e}")
                    import traceback
                    self.log_error(f"详细错误堆栈: {traceback.format_exc()}")
                    return None
                    
            except Exception as e:
                self.log_error(f"创建OCR实例失败: {e}")
                return None
    
    @parameter_validator
    def remove_instance(self, instance_id: str) -> bool:
        """移除OCR实例"""
        with self._lock:
            if instance_id not in self.instances:
                self.log_warning(f"实例 {instance_id} 不存在")
                return False
            
            try:
                instance = self.instances[instance_id]
                
                # 标记为停止状态
                instance.status = OCRInstanceStatus.STOPPING
                
                # 释放端口
                self.port_manager.release_port(instance.port)
                
                # 从实例池中移除
                del self.instances[instance_id]
                
                self.log_info(f"成功移除OCR实例: {instance_id}")
                return True
                
            except Exception as e:
                self.log_error(f"移除OCR实例失败: {e}")
                return False
    
    def get_instance(self, instance_id: str) -> Optional[OCRInstanceInfo]:
        """获取指定实例信息"""
        with self._lock:
            return self.instances.get(instance_id)
    
    def get_all_instances(self) -> List[OCRInstanceInfo]:
        """获取所有实例信息"""
        with self._lock:
            return list(self.instances.values())
    
    def get_available_instance(self) -> Optional[OCRInstanceInfo]:
        """获取可用的实例（智能负载均衡）"""
        with self._lock:
            available_instances = [
                inst for inst in self.instances.values()
                if inst.status in [OCRInstanceStatus.READY, OCRInstanceStatus.IDLE]
            ]
            
            if not available_instances:
                return None
            
            # 智能负载均衡：使用实例的负载评分方法
            # 选择负载评分最低的实例（评分越低表示负载越轻）
            best_instance = min(available_instances, key=lambda inst: inst.get_load_score())
            
            # 更新实例使用统计
            best_instance.update_usage_stats()
            
            return best_instance
    
    @parameter_validator
    def process_ocr_request(self, image_data, request_type: str = "recognize", 
                           optimization_mode: OptimizationMode = OptimizationMode.COMPREHENSIVE,
                           keywords: List[str] = None, enable_precise_positioning: bool = True, **kwargs):
        """处理OCR请求（使用综合优化和精确定位）"""
        self.total_requests += 1
        
        # 获取最佳实例
        instance = self.get_available_instance()
        if not instance:
            self.failed_requests += 1
            raise Exception("无可用OCR实例")

        try:
            # 标记实例为运行状态
            instance.status = OCRInstanceStatus.RUNNING
            instance.processed_requests += 1
            instance.last_activity = datetime.now()
            
            start_time = time.time()
            
            # 1. 图像预处理优化（如果是识别请求且有关键字）
            optimized_image_data = image_data
            optimization_info = {}
            
            if request_type == "recognize" and keywords:
                try:
                    optimization_result = self.comprehensive_optimizer.optimize_for_screenshot_keyword_matching(
                        image_data, keywords, optimization_mode
                    )
                    optimized_image_data = optimization_result.optimized_image
                    optimization_info = {
                        'mode': optimization_mode.value,
                        'preprocessing_time': optimization_result.optimization_time,
                        'performance_metrics': optimization_result.performance_metrics
                    }
                    # 合并优化参数
                    kwargs.update(optimization_result.ocr_params)
                except Exception as e:
                    self.logger.warning(f"图像预处理优化失败，使用原始图像: {e}")
            
            # 执行OCR请求
            if request_type == "recognize":
                # 过滤掉不支持的参数 - 只保留EasyOCR readtext方法支持的参数
                supported_params = {
                    'detail', 'paragraph', 'min_size', 'text_threshold', 'low_text', 
                    'link_threshold', 'canvas_size', 'mag_ratio', 'slope_ths', 
                    'ycenter_ths', 'height_ths', 'width_ths', 'y_ths', 'x_ths', 
                    'decoder', 'beamWidth', 'batch_size', 'workers', 'allowlist', 
                    'blocklist', 'rotation_info'
                }
                valid_kwargs = {k: v for k, v in kwargs.items() if k in supported_params}
                # 如果image_data是base64字符串，转换为bytes
                if isinstance(optimized_image_data, str):
                    try:
                        import base64
                        # 验证是否为有效的base64字符串
                        if len(optimized_image_data) % 4 == 0 and optimized_image_data.replace('+', '').replace('/', '').replace('=', '').isalnum():
                            image_bytes = base64.b64decode(optimized_image_data)
                            result = instance.service.recognize_text(image_bytes, **valid_kwargs)
                        else:
                            # 如果不是base64格式，检查是否为文件路径
                            if os.path.exists(optimized_image_data):
                                result = instance.service.recognize_text(optimized_image_data, **valid_kwargs)
                            else:
                                raise ValueError(f"无效的图像数据：既不是有效的base64编码，也不是存在的文件路径: {optimized_image_data[:50]}...")
                    except base64.binascii.Error as e:
                        # base64解码错误，检查是否为文件路径
                        if os.path.exists(optimized_image_data):
                            result = instance.service.recognize_text(optimized_image_data, **valid_kwargs)
                        else:
                            raise ValueError(f"base64解码失败且文件不存在: {optimized_image_data[:50]}..., 错误: {e}")
                    except Exception as e:
                        self.log_error(f"OCR识别失败: {e}")
                        raise
                else:
                    result = instance.service.recognize_text(optimized_image_data, **valid_kwargs)
                
                # 2. OCR结果后处理优化和精确定位
                if keywords and result:
                    try:
                        processed_results = self.comprehensive_optimizer.post_process_ocr_results(
                            result, keywords, optimization_mode
                        )
                        # 添加关键字匹配信息
                        keyword_matches = []
                        for processed_result in processed_results:
                            if hasattr(processed_result, 'keyword_matches') and processed_result.keyword_matches:
                                keyword_matches.extend(processed_result.keyword_matches)
                        
                        # 3. 精确定位增强（如果启用）
                        precise_positions = []
                        if enable_precise_positioning and keyword_matches:
                            try:
                                from src.core.ocr.services.precise_ocr_positioning_service import get_precise_ocr_positioning_service
                                precise_service = get_precise_ocr_positioning_service()
                                
                                for keyword in set(keyword_matches):
                                    precise_position = precise_service.find_precise_text_position(
                                        image_data=optimized_image_data,
                                        target_text=keyword
                                    )
                                    if precise_position:
                                        precise_positions.append(precise_position)
                                        self.logger.info(f"OCR池精确定位成功: '{keyword}' -> ({precise_position['center_x']}, {precise_position['center_y']})")
                                
                            except Exception as e:
                                self.logger.warning(f"OCR精确定位失败: {e}")
                        
                        # 创建增强的结果
                        enhanced_result = {
                            'original_result': result,
                            'processed_result': result,  # 保持兼容性
                            'keyword_matches': list(set(keyword_matches)),
                            'precise_positions': precise_positions,
                            'optimization_info': optimization_info
                        }
                        result = enhanced_result
                    except Exception as e:
                        self.logger.warning(f"OCR结果后处理优化失败: {e}")
                        # 添加基本的优化信息
                        if isinstance(result, list):
                            result = {
                                'original_result': result,
                                'processed_result': result,
                                'optimization_info': optimization_info
                            }
                        
            elif request_type == "detect":
                # 过滤掉不支持的参数
                valid_kwargs = {k: v for k, v in kwargs.items() if k != 'languages'}
                # 如果image_data是base64字符串，转换为bytes
                if isinstance(optimized_image_data, str):
                    try:
                        import base64
                        # 验证是否为有效的base64字符串
                        if len(optimized_image_data) % 4 == 0 and optimized_image_data.replace('+', '').replace('/', '').replace('=', '').isalnum():
                            image_bytes = base64.b64decode(optimized_image_data)
                            result = instance.service.detect(image_bytes, **valid_kwargs)
                        else:
                            # 如果不是base64格式，检查是否为文件路径
                            if os.path.exists(optimized_image_data):
                                result = instance.service.detect(optimized_image_data, **valid_kwargs)
                            else:
                                raise ValueError(f"无效的图像数据：既不是有效的base64编码，也不是存在的文件路径: {optimized_image_data[:50]}...")
                    except base64.binascii.Error as e:
                        # base64解码错误，检查是否为文件路径
                        if os.path.exists(optimized_image_data):
                            result = instance.service.detect(optimized_image_data, **valid_kwargs)
                        else:
                            raise ValueError(f"base64解码失败且文件不存在: {optimized_image_data[:50]}..., 错误: {e}")
                    except Exception as e:
                        self.log_error(f"文本检测失败: {e}")
                        raise
                else:
                    result = instance.service.detect(optimized_image_data, **valid_kwargs)
            else:
                raise ValueError(f"不支持的请求类型: {request_type}")
            
            # 记录响应时间
            response_time = time.time() - start_time
            instance.add_response_time(response_time)
            
            # 更新统计信息
            instance.update_usage_stats()
            self.successful_requests += 1
            
            # 记录精确定位统计
            if enable_precise_positioning and isinstance(result, dict) and 'precise_positions' in result:
                precise_count = len(result['precise_positions'])
                if precise_count > 0:
                    self.logger.info(f"OCR池请求完成，包含 {precise_count} 个精确定位结果")
            
            # 定期内存优化（每处理50个请求优化一次）
            if instance.processed_requests % 50 == 0:
                instance.optimize_memory()
                self.log_debug(f"实例 {instance.instance_id} 执行定期内存优化")
            
            # 记录请求时间（用于动态扩容）
            if self._scaling_manager:
                import uuid
                request_id = str(uuid.uuid4())[:8]  # 生成简短的请求ID
                self._scaling_manager.record_request_time(request_id, response_time)
            
            # 标准化返回格式
            if isinstance(result, dict) and ('original_result' in result or 'processed_result' in result):
                # 如果已经是增强结果格式，提取实际的OCR数据
                ocr_data = result.get('processed_result', result.get('original_result', []))
            else:
                # 原始EasyOCR结果
                ocr_data = result
            
            return {
                'success': True,
                'data': ocr_data,
                'response_time': response_time,
                'instance_id': instance.instance_id
            }
            
        except Exception as e:
            instance.error_count += 1
            self.failed_requests += 1
            self.log_error(f"处理OCR请求失败 - 实例: {instance.instance_id}, 错误: {e}")
            return {
                'success': False,
                'error': str(e),
                'instance_id': instance.instance_id if instance else 'unknown'
            }
        
        finally:
            # 恢复实例为空闲状态
            instance.status = OCRInstanceStatus.IDLE
    
    def get_pool_status(self) -> PoolStatus:
        """获取实例池状态"""
        with self._lock:
            status = PoolStatus()
            status.total_instances = len(self.instances)
            status.total_requests = self.total_requests
            status.successful_requests = self.successful_requests
            status.failed_requests = self.failed_requests
            
            # 统计各状态实例数
            for instance in self.instances.values():
                if instance.status in [OCRInstanceStatus.RUNNING, OCRInstanceStatus.READY]:
                    status.running_instances += 1
                elif instance.status == OCRInstanceStatus.IDLE:
                    status.idle_instances += 1
                elif instance.status == OCRInstanceStatus.ERROR:
                    status.error_instances += 1
                elif instance.status == OCRInstanceStatus.STOPPED:
                    status.stopped_instances += 1
            
            # 计算平均响应时间
            all_response_times = []
            total_memory = 0.0
            total_cpu = 0.0
            
            for instance in self.instances.values():
                all_response_times.extend(instance.response_times)
                total_memory += instance.memory_usage
                total_cpu += instance.cpu_usage
            
            if all_response_times:
                status.average_response_time = sum(all_response_times) / len(all_response_times)
            
            if self.instances:
                status.memory_usage = total_memory / len(self.instances)
                status.cpu_usage = total_cpu / len(self.instances)
            
            return status
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        with self._lock:
            status = self.get_pool_status()
            
            # 计算队列长度
            queue_length = self._request_queue.qsize() if hasattr(self._request_queue, 'qsize') else 0
            
            # 获取详细的实例信息
            instance_details = []
            for instance_id, instance in self.instances.items():
                instance_details.append({
                    'instance_id': instance_id,
                    'status': instance.status.value,
                    'memory_usage': instance.memory_usage,
                    'cpu_usage': instance.cpu_usage,
                    'request_count': instance.request_count,
                    'error_count': instance.error_count,
                    'last_used': instance.last_used.isoformat() if instance.last_used else None,
                    'response_times': instance.response_times[-10:] if instance.response_times else []  # 最近10次响应时间
                })
            
            return {
                'pool_status': {
                    'total_instances': status.total_instances,
                    'running_instances': status.running_instances,
                    'idle_instances': status.idle_instances,
                    'stopped_instances': status.stopped_instances,
                    'error_instances': status.error_instances,
                    'total_requests': status.total_requests,
                    'successful_requests': status.successful_requests,
                    'failed_requests': status.failed_requests,
                    'average_response_time': status.average_response_time,
                    'memory_usage': status.memory_usage,
                    'cpu_usage': status.cpu_usage
                },
                'queue_metrics': {
                    'queue_length': queue_length,
                    'max_queue_size': 100
                },
                'instance_details': instance_details,
                'config': {
                    'min_instances': self.min_instances,
                    'max_instances': self.max_instances,
                    'dynamic_scaling_enabled': hasattr(self, '_scaling_manager') and self._scaling_manager is not None
                }
            }
    
    @parameter_validator
    def process_batch_ocr_requests(self, image_data_list: List, request_type: str = "recognize", **kwargs):
        """批量处理OCR请求"""
        if not image_data_list:
            return []
        
        self.log_info(f"开始批量处理OCR请求 - 数量: {len(image_data_list)}, 类型: {request_type}")
        
        # 获取最佳实例
        instance = self.get_available_instance()
        if not instance:
            raise RuntimeError("没有可用的OCR实例")
        
        try:
            # 标记实例为运行状态
            instance.status = OCRInstanceStatus.RUNNING
            instance.last_activity = datetime.now()
            
            start_time = time.time()
            
            # 使用EasyOCR的批处理功能
            if request_type == "recognize":
                # 处理base64编码的图像数据
                processed_images = []
                for image_data in image_data_list:
                    if isinstance(image_data, str):
                        try:
                            import base64
                            image_bytes = base64.b64decode(image_data)
                            processed_images.append(image_bytes)
                        except Exception:
                            processed_images.append(image_data)
                    else:
                        processed_images.append(image_data)
                
                # 使用批处理方法
                if hasattr(instance.service, 'recognize_text_batched'):
                    result = instance.service.recognize_text_batched(processed_images, **kwargs)
                else:
                    # 如果不支持批处理，逐个处理
                    result = []
                    for img_data in processed_images:
                        img_result = instance.service.recognize_text(img_data, **kwargs)
                        result.append(img_result)
            else:
                raise ValueError(f"批处理暂不支持请求类型: {request_type}")
            
            # 记录响应时间
            response_time = time.time() - start_time
            instance.add_response_time(response_time)
            
            # 更新统计信息
            instance.processed_requests += len(image_data_list)
            instance.update_usage_stats()
            self.successful_requests += len(image_data_list)
            
            # 批处理后执行内存优化
            instance.optimize_memory()
            
            self.log_info(f"批量OCR处理完成 - 处理{len(image_data_list)}个请求，耗时: {response_time:.2f}秒")
            
            return result
            
        except Exception as e:
            instance.error_count += 1
            self.failed_requests += len(image_data_list)
            self.log_error(f"批量处理OCR请求失败 - 实例: {instance.instance_id}, 错误: {e}")
            raise
        
        finally:
            # 恢复实例为空闲状态
            instance.status = OCRInstanceStatus.IDLE
    
    def optimize_all_instances(self):
        """优化所有实例的内存使用"""
        with self._lock:
            for instance in self.instances.values():
                if instance.status in [OCRInstanceStatus.IDLE, OCRInstanceStatus.READY]:
                    try:
                        instance.optimize_memory()
                        self.log_debug(f"优化实例 {instance.instance_id} 内存")
                    except Exception as e:
                        self.log_warning(f"优化实例 {instance.instance_id} 内存失败: {e}")
    
    def get_memory_statistics(self) -> Dict[str, float]:
        """获取所有实例的内存统计信息"""
        total_system_memory = 0.0
        total_gpu_memory = 0.0
        instance_count = 0
        
        with self._lock:
            for instance in self.instances.values():
                if instance.status != OCRInstanceStatus.STOPPED:
                    memory_info = instance.get_memory_info()
                    if memory_info:
                        total_system_memory += memory_info.get('system_memory_mb', 0)
                        total_gpu_memory += memory_info.get('gpu_memory_allocated_mb', 0)
                        instance_count += 1
        
        return {
            'total_system_memory_mb': total_system_memory,
            'total_gpu_memory_mb': total_gpu_memory,
            'average_system_memory_mb': total_system_memory / max(instance_count, 1),
            'average_gpu_memory_mb': total_gpu_memory / max(instance_count, 1),
            'active_instances': instance_count
        }
    
    def get_idle_instances(self) -> List[str]:
        """获取空闲实例ID列表"""
        with self._lock:
            return [instance_id for instance_id, instance in self.instances.items() 
                   if instance.status == OCRInstanceStatus.IDLE or instance.status == OCRInstanceStatus.READY]
    
    def health_check(self):
        """健康检查"""
        with self._lock:
            for instance in self.instances.values():
                try:
                    # 更新实例统计信息
                    instance.update_usage_stats()
                    
                    # 检查实例是否响应正常
                    if instance.service and instance.status != OCRInstanceStatus.ERROR:
                        # 这里可以添加更详细的健康检查逻辑
                        pass
                        
                except Exception as e:
                    self.log_warning(f"实例 {instance.instance_id} 健康检查失败: {e}")
                    instance.status = OCRInstanceStatus.ERROR
    
    def enable_dynamic_scaling(self, scaling_manager):
        """启用动态扩容"""
        self._scaling_manager = scaling_manager
        self.log_info("动态扩容已启用")
    
    def disable_dynamic_scaling(self):
        """禁用动态扩容"""
        self._scaling_manager = None
        self.log_info("动态扩容已禁用")
    
    def is_dynamic_scaling_enabled(self) -> bool:
        """检查动态扩容是否启用"""
        return self._scaling_manager is not None
    
    def is_pool_running(self) -> bool:
        """检查OCR实例池是否正在运行
        
        Returns:
            bool: 如果有任何实例处于运行状态则返回True，否则返回False
        """
        with self._lock:
            # 检查是否有任何实例处于运行状态
            for instance in self.instances.values():
                if instance.status in [OCRInstanceStatus.READY, OCRInstanceStatus.BUSY, OCRInstanceStatus.IDLE]:
                    return True
            return False
    
    def get_scaling_status(self) -> Dict:
        """获取动态扩容状态"""
        if self._scaling_manager:
            return self._scaling_manager.get_scaling_status()
        return {"enabled": False, "message": "动态扩容未启用"}
    
    def record_request_time(self, response_time: float):
        """记录请求响应时间（用于动态扩容决策）"""
        if self._scaling_manager:
            import uuid
            request_id = str(uuid.uuid4())[:8]  # 生成简短的请求ID
            self._scaling_manager.record_request_time(request_id, response_time)
    
    def start_service(self):
        """启动OCR池服务"""
        try:
            self.log_info("正在启动OCR池服务...")
            self._legacy_logger.info("正在启动OCR池服务...")
            
            # 检查现有实例数量，只创建不足的实例
            min_instances = self.config.min_instances
            current_instances = len(self.instances)
            needed_instances = max(0, min_instances - current_instances)
            
            self.log_info(f"目标最小实例数: {min_instances}, 当前实例数: {current_instances}, 需要创建: {needed_instances}")
            
            # 只创建不足的实例数
            for i in range(needed_instances):
                instance_id = self.create_instance()
                if instance_id:
                    success = self.start_instance(instance_id)
                    if success:
                        self.log_info(f"实例 {instance_id} 启动成功")
                    else:
                        self.log_error(f"实例 {instance_id} 启动失败")
                else:
                    self.log_error(f"创建第 {i+1} 个实例失败")
            
            running_count = len([inst for inst in self.instances.values() 
                               if inst.status == OCRInstanceStatus.READY])
            
            if running_count > 0:
                self.log_info(f"OCR池服务启动成功，运行中实例数: {running_count}")
                self._legacy_logger.info(f"OCR池服务启动成功，运行中实例数: {running_count}")
                
                # 启动API服务器
                self._start_api_server()
                
            else:
                self.log_error("OCR池服务启动失败，没有可用实例")
                self._legacy_logger.error("OCR池服务启动失败，没有可用实例")
                raise RuntimeError("无法启动任何OCR实例")
                
        except Exception as e:
            self.log_error(f"启动OCR池服务失败: {e}")
            self._legacy_logger.error(f"启动OCR池服务失败: {e}")
            raise
    
    def _start_api_server(self):
        """启动API服务器"""
        try:
            if self._api_server_running:
                self.log_info("API服务器已在运行")
                return
            
            from src.core.ocr.services.ocr_api_server import create_app
            
            # 创建Flask应用，传递当前池管理器实例
            app = create_app(self.config.host, self.config.port, self)
            
            # 在单独线程中启动API服务器
            def run_api_server():
                try:
                    self.log_info(f"启动API服务器 - {self.config.host}:{self.config.port}")
                    self._legacy_logger.info(f"启动API服务器 - {self.config.host}:{self.config.port}")
                    
                    # 先尝试启动服务器
                    app.run(host=self.config.host, port=self.config.port, debug=False, threaded=True, use_reloader=False)
                except Exception as e:
                    self.log_error(f"API服务器运行失败: {e}")
                    self._legacy_logger.error(f"API服务器运行失败: {e}")
                    import traceback
                    self.log_error(f"API服务器异常详情: {traceback.format_exc()}")
                    self._api_server_running = False
            
            # 启动API服务器线程
            self._api_server_thread = threading.Thread(target=run_api_server, daemon=True)
            self._api_server_running = True  # 先设置为True，如果启动失败会在线程中设置为False
            self._api_server_thread.start()
            
            # 等待服务器启动并验证
            time.sleep(3)
            
            # 验证服务器是否真的在监听
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((self.config.host, self.config.port))
                sock.close()
                
                if result == 0:
                    self.log_info(f"API服务器启动成功，监听 {self.config.host}:{self.config.port}")
                    self._legacy_logger.info(f"API服务器启动成功，监听 {self.config.host}:{self.config.port}")
                else:
                    self._api_server_running = False
                    self.log_error(f"API服务器启动失败，端口 {self.config.port} 无法连接")
                    self._legacy_logger.error(f"API服务器启动失败，端口 {self.config.port} 无法连接")
            except Exception as e:
                self._api_server_running = False
                self.log_error(f"API服务器连接验证失败: {e}")
                self._legacy_logger.error(f"API服务器连接验证失败: {e}")
            
        except Exception as e:
            self.log_error(f"启动API服务器失败: {e}")
            self._legacy_logger.error(f"启动API服务器失败: {e}")
            self._api_server_running = False
    
    def _stop_api_server(self):
        """停止API服务器"""
        try:
            if self._api_server_running:
                self.log_info("正在停止API服务器...")
                self._api_server_running = False
                
                if self._api_server_thread and self._api_server_thread.is_alive():
                    # 等待线程结束
                    self._api_server_thread.join(timeout=5)
                
                self.log_info("API服务器已停止")
                self._legacy_logger.info("API服务器已停止")
        except Exception as e:
            self.log_error(f"停止API服务器失败: {e}")
            self._legacy_logger.error(f"停止API服务器失败: {e}")
    
    def wait_for_shutdown(self):
        """等待服务关闭信号"""
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.log_info("收到关闭信号")
            self._legacy_logger.info("收到关闭信号")
    
    def _convert_processed_results_to_standard(self, processed_results) -> List:
        """
        将处理后的结果转换为标准格式
        
        Args:
            processed_results: 处理后的OCR结果列表
            
        Returns:
            标准格式的结果列表
        """
        try:
            standard_results = []
            
            for result in processed_results:
                if hasattr(result, 'bbox') and hasattr(result, 'processed_text') and hasattr(result, 'confidence'):
                    # 转换为EasyOCR标准格式: [bbox, text, confidence]
                    bbox_list = [
                        [result.bbox[0], result.bbox[1]],  # 左上角
                        [result.bbox[2], result.bbox[1]],  # 右上角
                        [result.bbox[2], result.bbox[3]],  # 右下角
                        [result.bbox[0], result.bbox[3]]   # 左下角
                    ]
                    standard_results.append([
                        bbox_list,
                        result.processed_text or result.text,
                        result.confidence
                    ])
                else:
                    # 如果不是处理后的结果对象，直接添加
                    standard_results.append(result)
            
            return standard_results
            
        except Exception as e:
            self.log_warning(f"结果格式转换失败: {e}")
            return processed_results if isinstance(processed_results, list) else []
    
    def start_instance(self, instance_id: str) -> bool:
        """启动指定实例"""
        with self._lock:
            if instance_id not in self.instances:
                self.log_warning(f"实例 {instance_id} 不存在")
                return False
            
            instance = self.instances[instance_id]
            
            try:
                if instance.status == OCRInstanceStatus.STOPPED:
                    # 重新创建服务
                    service = EasyOCRService(
                        languages=['ch_sim', 'en'],
                        gpu=self.optimization_config.gpu.enabled,
                        model_storage_directory=self.optimization_config.model_config.model_storage_directory
                    )
                    instance.service = service
                
                instance.status = OCRInstanceStatus.READY
                instance.last_activity = datetime.now()
                
                self.log_info(f"成功启动实例: {instance_id}")
                return True
                
            except Exception as e:
                instance.status = OCRInstanceStatus.ERROR
                self.log_error(f"启动实例失败: {instance_id}, 错误: {e}")
                return False
    
    def stop_instance(self, instance_id: str) -> bool:
        """停止指定实例"""
        with self._lock:
            if instance_id not in self.instances:
                self.log_warning(f"实例 {instance_id} 不存在")
                return False
            
            instance = self.instances[instance_id]
            
            try:
                instance.status = OCRInstanceStatus.STOPPING
                
                # 清理服务资源
                if instance.service:
                    instance.service = None
                
                instance.status = OCRInstanceStatus.STOPPED
                instance.last_activity = datetime.now()
                
                self.log_info(f"成功停止实例: {instance_id}")
                return True
                
            except Exception as e:
                instance.status = OCRInstanceStatus.ERROR
                self.log_error(f"停止实例失败: {instance_id}, 错误: {e}")
                return False
    
    def restart_instance(self, instance_id: str) -> bool:
        """重启指定实例"""
        with self._lock:
            if instance_id not in self.instances:
                self.log_warning(f"实例 {instance_id} 不存在")
                return False
            
            try:
                # 先停止实例
                if not self.stop_instance(instance_id):
                    return False
                
                # 等待一小段时间
                time.sleep(0.5)
                
                # 再启动实例
                return self.start_instance(instance_id)
                
            except Exception as e:
                self.log_error(f"重启实例失败: {instance_id}, 错误: {e}")
                return False
    
    def shutdown(self):
        """关闭实例池"""
        with self._lock:
            self.log_info("开始关闭OCR实例池")
            
            # 停止API服务器
            self._stop_api_server()
            
            # 禁用动态扩容
            self.disable_dynamic_scaling()
            
            # 停止所有实例
            instance_ids = list(self.instances.keys())
            for instance_id in instance_ids:
                self.remove_instance(instance_id)
            
            # 停止队列处理器
            self._queue_processor_running = False
            self._request_queue.put(None)  # 发送停止信号
            
            # 关闭线程池
            self._executor.shutdown(wait=True)
            
            self.log_info("OCR实例池已关闭")

# 全局实例池管理器
_pool_manager_instance = None
_pool_manager_lock = threading.Lock()

def get_pool_manager(config: Optional[OCRPoolConfig] = None, force_reload: bool = False) -> OCRPoolManager:
    """获取OCR实例池管理器单例
    
    Args:
        config: OCR池配置对象，如果为None则使用默认配置
        force_reload: 是否强制重新加载配置
    """
    global _pool_manager_instance
    
    if _pool_manager_instance is None or force_reload:
        with _pool_manager_lock:
            if _pool_manager_instance is None or force_reload:
                # 如果需要重新加载，先关闭现有实例
                if _pool_manager_instance and force_reload:
                    _pool_manager_instance.shutdown()
                
                _pool_manager_instance = OCRPoolManager(config)
    
    return _pool_manager_instance

def shutdown_pool_manager():
    """关闭实例池管理器"""
    global _pool_manager_instance
    
    if _pool_manager_instance:
        with _pool_manager_lock:
            if _pool_manager_instance:
                _pool_manager_instance.shutdown()
                _pool_manager_instance = None

if __name__ == "__main__":
    # 测试代码
    manager = get_pool_manager()
    
    test_logger = get_logger("OCRPoolManagerTest", "OCR")
    test_logger.info("OCR实例池管理器测试")
    test_logger.info(f"当前实例数: {len(manager.get_all_instances())}")
    
    # 获取状态
    status = manager.get_pool_status()
    test_logger.info(f"实例池状态: 总数={status.total_instances}, 运行={status.running_instances}, 空闲={status.idle_instances}")
    
    # 清理
    manager.shutdown()
    test_logger.info("测试完成")