#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一进程监控服务
使用psutil监控进程资源，包括CPU、内存、线程数、文件句柄数等关键指标

@author: Mr.Rey Copyright © 2025
"""

import json
import os
import os
import socket
import subprocess
import threading
import time
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from datetime import datetime
from datetime import timedelta
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
import psutil
from src.core.services.system_manager_service import get_system_manager_service
from src.ui.services.logging_service import get_logger


@dataclass
class ProcessInfo:
    """进程信息数据类"""
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    threads_count: int
    file_handles: int
    status: str
    create_time: datetime
    runtime_seconds: float
    cmdline: List[str]
    # 扩展监控指标
    network_connections: int = 0
    disk_read_bytes: int = 0
    disk_write_bytes: int = 0
    disk_read_count: int = 0
    disk_write_count: int = 0
    gpu_usage_percent: float = 0.0
    gpu_memory_mb: float = 0.0
    response_time_ms: float = 0.0
    tcp_connections: int = 0
    udp_connections: int = 0
    listening_ports: List[int] = None
    
    def __post_init__(self):
        if self.listening_ports is None:
            self.listening_ports = []


@dataclass
class ProcessAlert:
    """进程告警信息"""
    pid: int
    alert_type: str
    current_value: float
    threshold: float
    message: str
    timestamp: datetime


class ProcessMonitorService:
    """统一进程监控服务"""
    
    def __init__(self):
        """初始化进程监控服务"""
        self.logger = get_logger("ProcessMonitorService", "System")
        self.monitoring_logger = get_logger("ProcessMonitoringData", "Performance")
        
        # 监控配置
        self._monitoring_enabled = False
        self._monitoring_interval = 30  # 30秒监控间隔
        self._lock = threading.RLock()
        
        # 监控的进程
        self._monitored_processes: Dict[int, psutil.Process] = {}
        self._process_history: Dict[int, List[ProcessInfo]] = {}
        
        # 告警配置
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 80.0,
            'threads_count': 100,
            'file_handles': 1000,
            'network_connections': 100,
            'gpu_usage_percent': 90.0,
            'response_time_ms': 5000.0
        }
        
        # 告警回调
        self._alert_callbacks: List[Callable[[ProcessAlert], None]] = []
        
        # 定时器服务和智能告警服务
        self._timer_service = None
        self._intelligent_alert_service = None
        
        self.logger.info("进程监控服务初始化完成")
    
    def initialize(self, timer_service, intelligent_alert_service=None):
        """初始化服务依赖"""
        self._timer_service = timer_service
        self._intelligent_alert_service = intelligent_alert_service
        self.logger.info("进程监控服务依赖初始化完成")
    
    def get_process_history_from_logs(self, pid: int, hours: int = 24) -> List[dict]:
        """从日志文件获取进程历史数据"""
        try:
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # 获取日志文件路径
            # 优先使用环境变量中的项目根目录路径
            project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
            if project_root_env:
                log_dir = os.path.join(project_root_env, 'data', 'logs', 'Performance')
            else:
                # 备用方案：从当前文件路径计算
                log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'logs', 'Performance')
            
            history_data = []
            
            # 遍历可能的日志文件（当天和前一天）
            for days_back in range(2):
                check_date = end_time - timedelta(days=days_back)
                log_file = os.path.join(log_dir, f'ProcessMonitoringData_{check_date.strftime("%Y%m%d")}.log')
                
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                # 解析日志行
                                if 'ProcessMonitoringData' in line and '{' in line:
                                    json_start = line.find('{')
                                    json_data = line[json_start:].strip()
                                    data = json.loads(json_data)
                                    
                                    # 检查PID和时间范围
                                    if data.get('pid') == pid:
                                        timestamp = datetime.fromisoformat(data.get('timestamp', ''))
                                        if start_time <= timestamp <= end_time:
                                            history_data.append(data)
                                            
                            except (json.JSONDecodeError, ValueError, KeyError):
                                continue
            
            # 按时间排序
            history_data.sort(key=lambda x: x.get('timestamp', ''))
            return history_data
             
        except Exception as e:
            self.logger.error(f"从日志文件获取历史数据失败: {e}")
            return []
    
    def get_monitoring_statistics(self, pid: int = None, hours: int = 24) -> dict:
        """获取监控统计信息"""
        try:
            # 获取历史数据
            if pid:
                history_data = self.get_process_history_from_logs(pid, hours)
            else:
                # 获取所有进程的数据
                history_data = []
                for process_pid in self.monitored_processes.keys():
                    history_data.extend(self.get_process_history_from_logs(process_pid, hours))
            
            if not history_data:
                return {}
            
            # 计算统计信息
            stats = {
                'total_records': len(history_data),
                'time_range': {
                    'start': min(data.get('timestamp', '') for data in history_data),
                    'end': max(data.get('timestamp', '') for data in history_data)
                },
                'cpu_usage': {
                    'avg': sum(data.get('cpu_percent', 0) for data in history_data) / len(history_data),
                    'max': max(data.get('cpu_percent', 0) for data in history_data),
                    'min': min(data.get('cpu_percent', 0) for data in history_data)
                },
                'memory_usage': {
                    'avg_mb': sum(data.get('memory_mb', 0) for data in history_data) / len(history_data),
                    'max_mb': max(data.get('memory_mb', 0) for data in history_data),
                    'avg_percent': sum(data.get('memory_percent', 0) for data in history_data) / len(history_data),
                    'max_percent': max(data.get('memory_percent', 0) for data in history_data)
                },
                'network_connections': {
                    'avg': sum(data.get('network_connections', 0) for data in history_data) / len(history_data),
                    'max': max(data.get('network_connections', 0) for data in history_data)
                },
                'threads_count': {
                    'avg': sum(data.get('threads_count', 0) for data in history_data) / len(history_data),
                    'max': max(data.get('threads_count', 0) for data in history_data)
                }
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取监控统计信息失败: {e}")
            return {}
    
    def find_processes_by_name(self, name: str) -> List[int]:
        """根据进程名查找进程PID"""
        pids = []
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and name.lower() in proc.info['name'].lower():
                    pids.append(proc.info['pid'])
        except Exception as e:
            self.logger.error(f"查找进程失败: 名称={name}, 错误={e}")
        return pids
    
    def find_processes_by_cmdline(self, cmdline_pattern: str) -> List[int]:
        """根据命令行参数查找进程PID"""
        pids = []
        try:
            for proc in psutil.process_iter(['pid', 'cmdline']):
                if proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if cmdline_pattern.lower() in cmdline.lower():
                        pids.append(proc.info['pid'])
        except Exception as e:
            self.logger.error(f"查找进程失败: 命令行={cmdline_pattern}, 错误={e}")
        return pids

    def _get_network_info(self, process: psutil.Process) -> Tuple[int, int, int, List[int]]:
        """获取网络连接信息"""
        try:
            connections = process.connections()
            total_connections = len(connections)
            tcp_connections = 0
            udp_connections = 0
            listening_ports = []
            
            for conn in connections:
                if conn.type == socket.SOCK_STREAM:
                    tcp_connections += 1
                elif conn.type == socket.SOCK_DGRAM:
                    udp_connections += 1
                
                # 收集监听端口
                if conn.status == psutil.CONN_LISTEN and conn.laddr:
                    listening_ports.append(conn.laddr.port)
            
            return total_connections, tcp_connections, udp_connections, listening_ports
        except Exception as e:
            self.logger.debug(f"获取网络信息失败: {e}")
            return 0, 0, 0, []
    
    def _get_disk_io_info(self, process: psutil.Process) -> Tuple[int, int, int, int]:
        """获取磁盘IO信息"""
        try:
            io_counters = process.io_counters()
            return (
                io_counters.read_bytes,
                io_counters.write_bytes,
                io_counters.read_count,
                io_counters.write_count
            )
        except Exception as e:
            self.logger.debug(f"获取磁盘IO信息失败: {e}")
            return 0, 0, 0, 0
    
    def _get_gpu_info(self, process: psutil.Process) -> Tuple[float, float]:
        """获取GPU使用信息"""
        try:
            # 尝试使用nvidia-smi获取GPU信息
            result = subprocess.run(
                ['nvidia-smi', '--query-compute-apps=pid,used_memory', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split(', ')
                        if len(parts) >= 2:
                            gpu_pid = int(parts[0])
                            if gpu_pid == process.pid:
                                gpu_memory_mb = float(parts[1])
                                # 简化的GPU使用率计算（基于内存使用）
                                gpu_usage = min(gpu_memory_mb / 1024, 100.0)  # 假设1GB为100%
                                return gpu_usage, gpu_memory_mb
            
            return 0.0, 0.0
        except Exception as e:
            self.logger.debug(f"获取GPU信息失败: {e}")
            return 0.0, 0.0
    
    def _measure_response_time(self, process: psutil.Process) -> float:
        """测量进程响应时间"""
        try:
            start_time = time.time()
            # 简单的响应时间测试：检查进程状态
            _ = process.status()
            _ = process.cpu_percent()
            end_time = time.time()
            return (end_time - start_time) * 1000  # 转换为毫秒
        except Exception as e:
            self.logger.debug(f"测量响应时间失败: {e}")
            return 0.0

    def _collect_process_info(self, process: psutil.Process) -> ProcessInfo:
        """收集进程信息"""
        try:
            # 获取基本信息
            pid = process.pid
            name = process.name()
            status = process.status()
            create_time = datetime.fromtimestamp(process.create_time())
            runtime_seconds = time.time() - process.create_time()
            
            # 获取资源使用情况
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = process.memory_percent()
            
            # 获取线程数
            try:
                threads_count = process.num_threads()
            except:
                threads_count = 0
            
            # 获取文件句柄数
            try:
                if hasattr(process, 'num_fds'):
                    file_handles = process.num_fds()
                else:
                    file_handles = len(process.open_files())
            except:
                file_handles = 0
            
            # 获取命令行参数
            try:
                cmdline = process.cmdline()
            except:
                cmdline = []
            
            # 获取扩展监控指标
            network_connections, tcp_connections, udp_connections, listening_ports = self._get_network_info(process)
            disk_read_bytes, disk_write_bytes, disk_read_count, disk_write_count = self._get_disk_io_info(process)
            gpu_usage_percent, gpu_memory_mb = self._get_gpu_info(process)
            response_time_ms = self._measure_response_time(process)
            
            return ProcessInfo(
                pid=pid,
                name=name,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                threads_count=threads_count,
                file_handles=file_handles,
                status=status,
                create_time=create_time,
                runtime_seconds=runtime_seconds,
                cmdline=cmdline,
                # 扩展监控指标
                network_connections=network_connections,
                disk_read_bytes=disk_read_bytes,
                disk_write_bytes=disk_write_bytes,
                disk_read_count=disk_read_count,
                disk_write_count=disk_write_count,
                gpu_usage_percent=gpu_usage_percent,
                gpu_memory_mb=gpu_memory_mb,
                response_time_ms=response_time_ms,
                tcp_connections=tcp_connections,
                udp_connections=udp_connections,
                listening_ports=listening_ports
            )
        except psutil.NoSuchProcess:
            raise
        except Exception as e:
            self.logger.error(f"收集进程信息失败: PID={process.pid}, 错误={e}")
            raise
    
    def _monitor_processes(self):
        """监控进程（定时任务）"""
        if not self._monitoring_enabled:
            return
        
        try:
            with self._lock:
                # 检查已停止的进程
                stopped_pids = []
                for pid, process in self._monitored_processes.items():
                    try:
                        if not process.is_running():
                            stopped_pids.append(pid)
                            self.logger.warning(f"检测到进程已停止: PID={pid}")
                            # 发送告警
                            alert = ProcessAlert(
                                pid=pid,
                                alert_type='process_stopped',
                                current_value=0,
                                threshold=1,
                                message=f"进程 {pid} 已停止运行",
                                timestamp=datetime.now()
                            )
                            self._send_alert(alert)
                    except psutil.NoSuchProcess:
                        stopped_pids.append(pid)
                        self.logger.warning(f"进程不存在: PID={pid}")
                
                # 移除已停止的进程
                for pid in stopped_pids:
                    del self._monitored_processes[pid]
                
                # 监控运行中的进程
                for pid, process in self._monitored_processes.items():
                    try:
                        info = self._collect_process_info(process)
                        
                        # 保存监控数据到日志文件
                        self._save_monitoring_data(info)
                        
                        # 保存历史记录（仅保留最近100条用于实时查询）
                        if pid not in self._process_history:
                            self._process_history[pid] = []
                        self._process_history[pid].append(info)
                        
                        # 限制内存中历史记录数量
                        if len(self._process_history[pid]) > 100:
                            self._process_history[pid] = self._process_history[pid][-50:]
                        
                        # 检查告警条件
                        self._check_alerts(info)
                        
                        # 记录监控日志
                        self.logger.debug(
                            f"进程监控 PID={pid} 名称={info.name} "
                            f"CPU={info.cpu_percent:.1f}% 内存={info.memory_mb:.1f}MB "
                            f"线程={info.threads_count} 句柄={info.file_handles} "
                            f"网络连接={info.network_connections} TCP={info.tcp_connections} "
                            f"磁盘读={info.disk_read_bytes//1024//1024}MB 磁盘写={info.disk_write_bytes//1024//1024}MB "
                            f"GPU={info.gpu_usage_percent:.1f}% GPU内存={info.gpu_memory_mb:.1f}MB "
                            f"响应时间={info.response_time_ms:.1f}ms"
                        )
                        
                    except psutil.NoSuchProcess:
                        self.logger.warning(f"进程已不存在: PID={pid}")
                    except Exception as e:
                        self.logger.error(f"监控进程失败: PID={pid}, 错误={e}")
        
        except Exception as e:
            self.logger.error(f"进程监控任务执行失败: {e}")
    
    def _check_alerts(self, info: ProcessInfo):
        """检查告警条件（使用智能告警服务）"""
        if not self._intelligent_alert_service:
            return
        
        try:
            # 定义告警检查项
            alert_checks = [
                ('high_cpu', info.cpu_percent, self.thresholds['cpu_percent'], 
                 f"进程 {info.pid}({info.name}) CPU使用率过高: {info.cpu_percent:.1f}%"),
                
                ('high_memory', info.memory_percent, self.thresholds['memory_percent'],
                 f"进程 {info.pid}({info.name}) 内存使用率过高: {info.memory_percent:.1f}%"),
                
                ('too_many_threads', info.threads_count, self.thresholds['threads_count'],
                 f"进程 {info.pid}({info.name}) 线程数过多: {info.threads_count}"),
                
                ('too_many_handles', info.file_handles, self.thresholds['file_handles'],
                 f"进程 {info.pid}({info.name}) 文件句柄数过多: {info.file_handles}"),
                
                ('too_many_connections', info.network_connections, self.thresholds['network_connections'],
                 f"进程 {info.pid}({info.name}) 网络连接数过多: {info.network_connections}"),
                
                ('high_gpu_usage', info.gpu_usage_percent, self.thresholds['gpu_usage_percent'],
                 f"进程 {info.pid}({info.name}) GPU使用率过高: {info.gpu_usage_percent:.1f}%"),
                
                ('high_gpu_memory', info.gpu_memory_mb, self.thresholds['gpu_memory_mb'],
                 f"进程 {info.pid}({info.name}) GPU内存使用过高: {info.gpu_memory_mb:.1f}MB"),
                
                ('slow_response', info.response_time_ms, self.thresholds['response_time_ms'],
                 f"进程 {info.pid}({info.name}) 响应时间过长: {info.response_time_ms:.1f}ms"),
                
                ('too_many_tcp_connections', info.tcp_connections, self.thresholds['tcp_connections'],
                 f"进程 {info.pid}({info.name}) TCP连接数过多: {info.tcp_connections}")
            ]
            
            # 使用智能告警服务处理每个检查项
            for alert_type, current_value, threshold, message in alert_checks:
                smart_alert = self._intelligent_alert_service.process_alert(
                    pid=info.pid,
                    alert_type=alert_type,
                    current_value=current_value,
                    base_threshold=threshold,
                    message=message
                )
                
                # 如果智能告警服务生成了告警，转换为ProcessAlert格式并发送
                if smart_alert:
                    process_alert = ProcessAlert(
                        pid=smart_alert.pid,
                        alert_type=smart_alert.alert_type,
                        current_value=smart_alert.current_value,
                        threshold=smart_alert.dynamic_threshold,  # 使用动态阈值
                        message=smart_alert.message,
                        timestamp=smart_alert.timestamp
                    )
                    self._send_alert(process_alert)
            
        except Exception as e:
            self.logger.error(f"检查告警失败: {e}")
    
    def _save_monitoring_data(self, info: ProcessInfo):
        """保存监控数据到日志文件"""
        try:
            # 将ProcessInfo转换为字典
            data = asdict(info)
            # 转换datetime对象为字符串
            data['create_time'] = info.create_time.isoformat()
            data['timestamp'] = datetime.now().isoformat()
            
            # 记录监控数据到专用日志
            self.monitoring_logger.info(json.dumps(data, ensure_ascii=False))
            
        except Exception as e:
            self.logger.error(f"保存监控数据失败: {e}")
    
    def _send_alert(self, alert: ProcessAlert):
        """发送告警"""
        try:
            # 记录告警日志
            self.logger.warning(alert.message)
            
            # 调用告警回调函数
            for callback in self._alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"告警回调函数执行失败: {e}")
        except Exception as e:
            self.logger.error(f"发送告警失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        try:
            self.stop_monitoring()
            with self._lock:
                self._monitored_processes.clear()
                self._process_history.clear()
                self._alert_callbacks.clear()
            self.logger.info("进程监控服务清理完成")
        except Exception as e:
            self.logger.error(f"进程监控服务清理失败: {e}")


# 全局实例
_process_monitor_service = None


def get_process_monitor_service() -> ProcessMonitorService:
    """获取进程监控服务实例"""
    global _process_monitor_service
    if _process_monitor_service is None:
        _process_monitor_service = ProcessMonitorService()
    return _process_monitor_service


def initialize_process_monitor_service(timer_service):
    """初始化进程监控服务"""
    service = get_process_monitor_service()
    service.initialize(timer_service)
    return service