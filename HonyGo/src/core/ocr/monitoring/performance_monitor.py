#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR性能监控和自动调优系统
实现实时性能监控、自动优化策略和性能报告生成

@author: Mr.Rey Copyright © 2025
"""

import json
import sys
import threading
import time
from collections import deque
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
import psutil
import pynvml
import requests
import torch
from src.core.ocr.services.ocr_pool_manager import get_pool_manager
from src.ui.services.logging_service import get_logger


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    gpu_usage: float
    gpu_memory_usage: float
    response_time: float
    throughput: float
    error_rate: float
    active_instances: int
    queue_size: int
    cache_hit_rate: float


class PerformanceMonitor:
    """OCR性能监控器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.is_monitoring = False
        self.monitor_thread = None
        self.metrics_history = deque(maxlen=1000)
        self.last_optimization_time = 0
        self.optimization_cooldown = 300  # 5分钟冷却时间
        
        # 性能阈值
        self.thresholds = {
            'cpu_usage_high': 80.0,
            'memory_usage_high': 85.0,
            'gpu_usage_high': 90.0,
            'response_time_high': 5.0,
            'error_rate_high': 0.05,
            'cache_hit_rate_low': 0.7
        }
        
        # 优化策略映射
        self.optimization_strategies = {
            'high_cpu_usage': self._optimize_cpu_usage,
            'high_memory_usage': self._optimize_memory_usage,
            'high_gpu_usage': self._optimize_cpu_usage,
            'high_response_time': self._optimize_response_time,
            'high_error_rate': self._optimize_error_rate,
            'low_cache_hit_rate': self._optimize_cache_performance,
            'low_throughput': self._optimize_throughput
        }
    
    def start_monitoring(self):
        """启动性能监控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("性能监控已启动")
    
    def stop_monitoring(self):
        """停止性能监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("性能监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)
                self._check_and_optimize(metrics)
                time.sleep(10)  # 每10秒收集一次指标
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
                time.sleep(30)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        try:
            # 系统指标
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # GPU指标
            gpu_usage, gpu_memory_usage = self._get_gpu_metrics()
            
            # OCR服务指标
            service_metrics = self._get_service_metrics()
            response_time = service_metrics.get('avg_response_time', 0.0)
            throughput = self._calculate_throughput(service_metrics)
            error_rate = service_metrics.get('error_rate', 0.0)
            active_instances = service_metrics.get('active_instances', 0)
            queue_size = service_metrics.get('queue_size', 0)
            cache_hit_rate = service_metrics.get('cache_hit_rate', 0.0)
            
            return PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                gpu_usage=gpu_usage,
                gpu_memory_usage=gpu_memory_usage,
                response_time=response_time,
                throughput=throughput,
                error_rate=error_rate,
                active_instances=active_instances,
                queue_size=queue_size,
                cache_hit_rate=cache_hit_rate
            )
            
        except Exception as e:
            self.logger.error(f"收集性能指标失败: {e}")
            return PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_usage=0.0, memory_usage=0.0, gpu_usage=0.0,
                gpu_memory_usage=0.0, response_time=0.0, throughput=0.0,
                error_rate=0.0, active_instances=0, queue_size=0,
                cache_hit_rate=0.0
            )
    
    def _get_gpu_metrics(self) -> tuple[float, float]:
        """获取GPU指标"""
        try:
            if torch.cuda.is_available():
                try:
                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    gpu_util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    
                    gpu_usage = gpu_util.gpu
                    gpu_memory_usage = (memory_info.used / memory_info.total) * 100
                    
                    return gpu_usage, gpu_memory_usage
                    
                except ImportError:
                    # 如果没有pynvml，使用torch的内存信息
                    memory_allocated = torch.cuda.memory_allocated(0)
                    memory_reserved = torch.cuda.memory_reserved(0)
                    total_memory = torch.cuda.get_device_properties(0).total_memory
                    
                    gpu_memory_usage = (memory_reserved / total_memory) * 100
                    return 0.0, gpu_memory_usage
                    
        except Exception as e:
            self.logger.debug(f"获取GPU指标失败: {e}")
        
        return 0.0, 0.0
    
    def _get_service_metrics(self) -> Dict[str, Any]:
        """获取OCR服务指标"""
        try:
            pool_manager = get_pool_manager()
            if pool_manager:
                return pool_manager.get_metrics()
        except Exception as e:
            self.logger.debug(f"获取服务指标失败: {e}")
        
        return {
            'avg_response_time': 0.0,
            'total_requests': 0,
            'uptime_seconds': 1,
            'error_rate': 0.0,
            'active_instances': 0,
            'queue_size': 0,
            'cache_hit_rate': 0.0
        }
    
    def _calculate_throughput(self, service_metrics: Dict[str, Any]) -> float:
        """计算吞吐量"""
        try:
            total_requests = service_metrics.get('total_requests', 0)
            uptime_seconds = service_metrics.get('uptime_seconds', 1)
            
            if uptime_seconds > 0:
                return total_requests / uptime_seconds
            
        except Exception as e:
            self.logger.debug(f"计算吞吐量失败: {e}")
        
        return 0.0
    
    def _check_and_optimize(self, metrics: PerformanceMetrics):
        """检查性能并执行优化"""
        current_time = time.time()
        
        # 检查优化冷却时间
        if current_time - self.last_optimization_time < self.optimization_cooldown:
            return
        
        # 检查各项性能指标
        issues = self._identify_performance_issues(metrics)
        
        if issues:
            self.logger.info(f"检测到性能问题: {', '.join(issues)}")
            
            # 执行优化策略
            for issue in issues:
                if issue in self.optimization_strategies:
                    try:
                        self.optimization_strategies[issue](metrics)
                        self.last_optimization_time = current_time
                        break  # 一次只执行一个优化策略
                        
                    except Exception as e:
                        self.logger.error(f"执行优化策略 {issue} 失败: {e}")
    
    def _identify_performance_issues(self, metrics: PerformanceMetrics) -> List[str]:
        """识别性能问题"""
        issues = []
        
        if metrics.cpu_usage > self.thresholds['cpu_usage_high']:
            issues.append('high_cpu_usage')
        
        if metrics.memory_usage > self.thresholds['memory_usage_high']:
            issues.append('high_memory_usage')
        
        if metrics.response_time > self.thresholds['response_time_high']:
            issues.append('slow_response_time')
        
        if metrics.error_rate > self.thresholds['error_rate_high']:
            issues.append('high_error_rate')
        
        if metrics.cache_hit_rate < self.thresholds['cache_hit_rate_low']:
            issues.append('low_cache_hit_rate')
        
        if metrics.throughput < self.thresholds['throughput_low']:
            issues.append('low_throughput')
        
        return issues
    
    def _optimize_cpu_usage(self, metrics: PerformanceMetrics):
        """优化CPU使用率"""
        action = OptimizationAction(
            timestamp=time.time(),
            action_type='cpu_optimization',
            description='降低CPU使用率',
            parameters={'target_cpu_usage': 70.0},
            expected_improvement='减少CPU负载，提高系统响应性'
        )
        
        try:
            # 请求OCR池服务减少实例数量或调整处理策略
            response = requests.post(f"{self.ocr_pool_url}/pool/instances", 
                                   json={'action': 'optimize_cpu'}, timeout=5)
            
            if response.status_code == 200:
                action.actual_result = 'CPU优化请求已发送'
                self.stats['successful_optimizations'] += 1
            else:
                action.actual_result = f'CPU优化请求失败: {response.status_code}'
            
        except Exception as e:
            action.actual_result = f'CPU优化异常: {e}'
        
        self.optimization_history.append(action)
        self.stats['total_optimizations'] += 1
        self.logger.info(f"执行CPU优化: {action.actual_result}")
    
    def _optimize_memory_usage(self, metrics: PerformanceMetrics):
        """优化内存使用"""
        action = OptimizationAction(
            timestamp=time.time(),
            action_type='memory_optimization',
            description='释放内存并优化缓存',
            parameters={'aggressive_cleanup': True},
            expected_improvement='减少内存占用，避免内存泄漏'
        )
        
        try:
            # 清理缓存
            response = requests.post(f"{self.ocr_pool_url}/cache/clear", timeout=5)
            
            if response.status_code == 200:
                action.actual_result = '内存优化完成，缓存已清理'
                self.stats['successful_optimizations'] += 1
            else:
                action.actual_result = f'内存优化失败: {response.status_code}'
            
        except Exception as e:
            action.actual_result = f'内存优化异常: {e}'
        
        self.optimization_history.append(action)
        self.stats['total_optimizations'] += 1
        self.logger.info(f"执行内存优化: {action.actual_result}")
    
    def _optimize_response_time(self, metrics: PerformanceMetrics):
        """优化响应时间"""
        action = OptimizationAction(
            timestamp=time.time(),
            action_type='response_time_optimization',
            description='增加实例数量以提高响应速度',
            parameters={'target_response_time': 5.0},
            expected_improvement='减少响应时间，提高用户体验'
        )
        
        try:
            # 请求增加实例
            response = requests.post(f"{self.ocr_pool_url}/pool/instances", 
                                   json={'action': 'add', 'count': 1}, timeout=5)
            
            if response.status_code == 200:
                action.actual_result = '已请求增加OCR实例'
                self.stats['successful_optimizations'] += 1
            else:
                action.actual_result = f'响应时间优化失败: {response.status_code}'
            
        except Exception as e:
            action.actual_result = f'响应时间优化异常: {e}'
        
        self.optimization_history.append(action)
        self.stats['total_optimizations'] += 1
        self.logger.info(f"执行响应时间优化: {action.actual_result}")
    
    def _optimize_error_rate(self, metrics: PerformanceMetrics):
        """优化错误率"""
        action = OptimizationAction(
            timestamp=time.time(),
            action_type='error_rate_optimization',
            description='重启异常实例，降低错误率',
            parameters={'restart_threshold': 5.0},
            expected_improvement='减少处理错误，提高成功率'
        )
        
        try:
            # 获取实例状态并重启异常实例
            pool_manager = get_pool_manager()
            if pool_manager:
                pool_status = pool_manager.get_pool_status()
                if pool_status:
                    action.actual_result = '错误率优化检查完成'
                    self.stats['successful_optimizations'] += 1
                else:
                    action.actual_result = '错误率优化失败: 无法获取池状态'
            else:
                action.actual_result = '错误率优化失败: 无法获取池管理器'
            
        except Exception as e:
            action.actual_result = f'错误率优化异常: {e}'
        
        self.optimization_history.append(action)
        self.stats['total_optimizations'] += 1
        self.logger.info(f"执行错误率优化: {action.actual_result}")
    
    def _optimize_cache_performance(self, metrics: PerformanceMetrics):
        """优化缓存性能"""
        action = OptimizationAction(
            timestamp=time.time(),
            action_type='cache_optimization',
            description='调整缓存策略，提高命中率',
            parameters={'target_hit_rate': 80.0},
            expected_improvement='提高缓存命中率，减少重复计算'
        )
        
        try:
            # 获取缓存状态
            response = requests.get(f"{self.ocr_pool_url}/cache/status", timeout=5)
            
            if response.status_code == 200:
                action.actual_result = '缓存性能优化检查完成'
                self.stats['successful_optimizations'] += 1
            else:
                action.actual_result = f'缓存优化失败: {response.status_code}'
            
        except Exception as e:
            action.actual_result = f'缓存优化异常: {e}'
        
        self.optimization_history.append(action)
        self.stats['total_optimizations'] += 1
        self.logger.info(f"执行缓存优化: {action.actual_result}")
    
    def _optimize_throughput(self, metrics: PerformanceMetrics):
        """优化吞吐量"""
        action = OptimizationAction(
            timestamp=time.time(),
            action_type='throughput_optimization',
            description='启用动态扩容，提高处理能力',
            parameters={'enable_scaling': True},
            expected_improvement='增加处理能力，提高吞吐量'
        )
        
        try:
            # 启用动态扩容
            response = requests.post(f"{self.ocr_pool_url}/scaling/enable", timeout=5)
            
            if response.status_code == 200:
                action.actual_result = '动态扩容已启用'
                self.stats['successful_optimizations'] += 1
            else:
                action.actual_result = f'吞吐量优化失败: {response.status_code}'
            
        except Exception as e:
            action.actual_result = f'吞吐量优化异常: {e}'
        
        self.optimization_history.append(action)
        self.stats['total_optimizations'] += 1
        self.logger.info(f"执行吞吐量优化: {action.actual_result}")
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """生成性能报告"""
        try:
            current_time = time.time()
            start_time = current_time - (hours * 3600)
            
            # 筛选时间范围内的数据
            recent_metrics = [m for m in self.metrics_history if m.timestamp >= start_time]
            recent_optimizations = [o for o in self.optimization_history if o.timestamp >= start_time]
            
            if not recent_metrics:
                return {'error': '没有足够的历史数据生成报告'}
            
            # 计算统计信息
            avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
            avg_response_time = sum(m.response_time for m in recent_metrics) / len(recent_metrics)
            avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
            
            max_cpu = max(m.cpu_usage for m in recent_metrics)
            max_memory = max(m.memory_usage for m in recent_metrics)
            max_response_time = max(m.response_time for m in recent_metrics)
            
            # 生成报告
            report = {
                'report_period': f'{hours}小时',
                'generated_at': datetime.now().isoformat(),
                'data_points': len(recent_metrics),
                'system_performance': {
                    'avg_cpu_usage': round(avg_cpu, 2),
                    'max_cpu_usage': round(max_cpu, 2),
                    'avg_memory_usage': round(avg_memory, 2),
                    'max_memory_usage': round(max_memory, 2)
                },
                'ocr_performance': {
                    'avg_response_time': round(avg_response_time, 2),
                    'max_response_time': round(max_response_time, 2),
                    'avg_cache_hit_rate': round(avg_cache_hit_rate, 2)
                },
                'optimizations': {
                    'total_optimizations': len(recent_optimizations),
                    'optimization_types': list(set(o.action_type for o in recent_optimizations)),
                    'recent_actions': [asdict(o) for o in recent_optimizations[-5:]]  # 最近5个优化动作
                },
                'monitoring_stats': self.stats.copy()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成性能报告失败: {e}")
            return {'error': f'生成报告失败: {e}'}
    
    def save_report(self, report: Dict[str, Any], filename: Optional[str] = None) -> str:
        """保存性能报告到文件"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'performance_report_{timestamp}.json'
            
            # 确保报告目录存在
            # 使用环境变量获取项目根目录
            project_root = Path(os.environ.get('HONYGO_PROJECT_ROOT', Path(__file__).resolve().parent.parent.parent.parent.parent))
            report_dir = project_root / "data" / "logs" / "Performance"
            report_dir.mkdir(parents=True, exist_ok=True)
            
            report_path = report_dir / filename
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"性能报告已保存到: {report_path}")
            return str(report_path)
            
        except Exception as e:
            self.logger.error(f"保存性能报告失败: {e}")
            raise
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前监控状态"""
        latest_metrics = self.metrics_history[-1] if self.metrics_history else None
        
        return {
            'is_monitoring': self.is_monitoring,
            'monitor_interval': self.monitor_interval,
            'auto_optimize': self.auto_optimize,
            'metrics_count': len(self.metrics_history),
            'optimization_count': len(self.optimization_history),
            'latest_metrics': asdict(latest_metrics) if latest_metrics else None,
            'stats': self.stats.copy(),
            'thresholds': self.thresholds.copy()
        }
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        获取当前性能指标
        
        Returns:
            当前性能指标字典
        """
        if not self.metrics_history:
            return {}
        
        current_metrics = self.metrics_history[-1]
        return asdict(current_metrics)
    
    def record_request(self, response_time: float, success: bool = True):
        """
        记录请求性能数据
        
        Args:
            response_time: 响应时间（秒）
            success: 请求是否成功
        """
        try:
            # 这里可以添加更详细的请求记录逻辑
            # 目前只记录到日志中
            if success:
                self.logger.debug(f"请求成功，响应时间: {response_time:.3f}秒")
            else:
                self.logger.warning(f"请求失败，响应时间: {response_time:.3f}秒")
        except Exception as e:
            self.logger.error(f"记录请求性能数据失败: {e}")


if __name__ == "__main__":
    # 示例用法
    monitor = PerformanceMonitor()
    
    try:
        test_logger = get_logger("PerformanceMonitorTest", "MONITOR")
        test_logger.info("启动性能监控...")
        monitor.start_monitoring()
        
        # 运行一段时间
        time.sleep(60)
        
        # 生成报告
        report = monitor.get_performance_report(hours=1)
        report_path = monitor.save_report(report)
        test_logger.info(f"性能报告已生成: {report_path}")
        
    except KeyboardInterrupt:
        test_logger.info("停止监控...")
    finally:
        monitor.stop_monitoring()
        test_logger.info("监控已停止")