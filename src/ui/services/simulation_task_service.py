#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟任务服务

@author: Mr.Rey Copyright © 2025
@created: 2025-01-25 15:45:00
@modified: 2025-01-25 15:45:00
@version: 1.0.0

负责管理自动化模拟任务的生命周期，包括任务启动、停止、状态管理等功能
"""

import os
import sys
import threading
import time
import keyboard
import pyautogui
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path

# 设置项目根路径
project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
if project_root_env:
    project_root = Path(project_root_env)
else:
    project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.services.logging_service import get_logger
from src.ui.services.smart_click_service import SmartClickService
from src.ui.services.coordinate_service import get_coordinate_service

class SimulationTaskService:
    """
    模拟任务服务
    
    负责管理自动化模拟任务的生命周期，包括：
    - 任务启动、停止、状态管理
    - 监控频率控制
    - 用户输入检测（鼠标移动、ESC/空格键）
    - 图片参照和OCR池算法的统一调度
    - 多目标点击的间隔控制
    """
    
    def __init__(self):
        self.logger = get_logger("SimulationTaskService", "Simulation")
        self.logger.info("初始化模拟任务服务")
        
        # 任务状态
        self._is_running = False
        self._task_config = None
        self._monitoring_thread = None
        self._stop_event = threading.Event()
        self._start_time = None
        self._end_time = None
        
        # 用户输入检测（仅支持ESC和空格键）
        self._input_detection_active = False
        
        # 服务实例
        self._smart_click_service = None
        self._coordinate_service = None
        
        # 统计信息
        self._statistics = {
            'total_matches': 0,
            'total_clicks': 0,
            'detection_cycles': 0,
            'errors': 0,
            'last_match_time': None,
            'last_click_time': None,
            'ocr_detections': 0,
            'image_detections': 0,
            'user_interruptions': 0
        }
        
        # 点击状态管理（用于优化鼠标移动检测）
        self._click_in_progress = False
        
        # 初始化服务
        self._initialize_services()
        
        # 设置智能点击服务的引用
        if self._smart_click_service:
            self._smart_click_service.set_simulation_task_service(self)
        
        self.logger.debug("模拟任务服务初始化完成")
    
    def _set_click_in_progress(self, in_progress: bool):
        """
        设置点击操作进行状态（供智能点击服务调用）
        
        Args:
            in_progress: 是否正在进行点击操作
        """
        self._click_in_progress = in_progress
        self.logger.debug(f"点击操作状态更新: {in_progress}")
    
    def _initialize_services(self):
        """初始化依赖服务"""
        try:
            self.logger.debug("开始初始化依赖服务")
            
            # 初始化坐标服务
            self._coordinate_service = get_coordinate_service()
            self.logger.debug("坐标服务初始化完成")
            
            # 初始化智能点击服务
            self._smart_click_service = SmartClickService()
            self.logger.debug("智能点击服务初始化完成")
            
            self.logger.info("所有依赖服务初始化完成")
            
        except Exception as e:
            self.logger.error(f"初始化依赖服务失败: {e}")
            raise
    
    def start_task(self, config: Dict[str, Any]) -> bool:
        """
        启动模拟任务
        
        Args:
            config: 任务配置字典，包含算法类型、参数等
            
        Returns:
            bool: 启动是否成功
        """
        try:
            if self._is_running:
                self.logger.warning("任务已在运行中，无法重复启动")
                return False
            
            self.logger.info(f"开始启动模拟任务，配置: {config}")
            
            # 严格验证配置
            if not self._validate_config(config):
                self.logger.error("配置验证失败，无法启动任务")
                return False
            
            # 验证智能点击服务可用性
            if not self._smart_click_service:
                self.logger.error("智能点击服务未初始化，无法启动任务")
                return False
            
            # 保存配置
            self._task_config = config.copy()
            self._stop_event.clear()
            self._start_time = datetime.now()
            
            # 重置统计信息
            self.reset_statistics()
            
            # 移除初始鼠标位置记录 - 不再需要鼠标移动检测
            
            # 启动监控线程
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            
            self._is_running = True
            self._monitoring_thread.start()
            
            # 等待监控线程启动完成
            time.sleep(0.1)
            
            if not self._monitoring_thread.is_alive():
                self.logger.error("监控线程启动失败")
                self._is_running = False
                return False
            
            # 启用用户输入检测
            self._enable_input_detection()
            
            self.logger.info(f"模拟任务已启动 - 算法类型: {config.get('algorithm_type')}, 监控频率: {config.get('monitor_frequency')}s")
            self.logger.info("提示：任务运行期间，请使用ESC键或空格键停止任务，鼠标移动不会停止任务")
            return True
            
        except Exception as e:
            self.logger.error(f"启动模拟任务失败: {e}")
            self._is_running = False
            return False
    
    def stop_task(self) -> bool:
        """
        停止模拟任务
        
        Returns:
            bool: 停止是否成功
        """
        try:
            if not self._is_running:
                self.logger.info("任务未在运行，无需停止")
                return True
            
            self.logger.info("正在停止模拟任务...")
            
            # 设置停止事件
            self._stop_event.set()
            self._is_running = False
            self._end_time = datetime.now()
            
            # 禁用用户输入检测
            self._disable_input_detection()
            
            # 等待监控线程结束
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=5.0)
            
            # 生成任务报告
            self._generate_task_report()
            
            if self._monitoring_thread.is_alive():
                self.logger.warning("监控线程未能在超时时间内结束")
            
            self._task_config = None
            self.logger.info("模拟任务已成功停止")
            return True
            
        except Exception as e:
            self.logger.error(f"停止模拟任务失败: {e}")
            return False
    
    def is_running(self) -> bool:
        """
        检查任务是否正在运行
        
        Returns:
            bool: 任务运行状态
        """
        return self._is_running
    
    def get_task_status(self) -> Dict[str, Any]:
        """
        获取任务状态信息
        
        Returns:
            Dict[str, Any]: 任务状态信息
        """
        return {
            'is_running': self._is_running,
            'config': self._task_config,
            'input_detection_active': self._input_detection_active,
            'start_time': self._start_time.isoformat() if self._start_time else None,
            'end_time': self._end_time.isoformat() if self._end_time else None,
            'statistics': self._statistics.copy()
        }
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """
        验证任务配置
        
        Args:
            config: 任务配置字典
            
        Returns:
            bool: 配置是否有效
        """
        try:
            self.logger.debug(f"开始验证配置: {config}")
            
            # 检查必要字段
            required_fields = [
                'algorithm_type', 'click_interval', 'mouse_button',
                'monitor_frequency', 'monitor_area'
            ]
            
            for field in required_fields:
                if field not in config:
                    self.logger.error(f"配置缺少必要字段: {field}, 当前配置: {config}")
                    return False
                else:
                    self.logger.debug(f"字段 {field} 验证通过: {config[field]}")
            
            # 验证算法类型特定配置
            algorithm_type = config.get('algorithm_type')
            
            if algorithm_type == 'ocr_pool':
                keyword = config.get('keyword', '').strip()
                if not keyword:
                    self.logger.error("OCR池算法需要设置关键字")
                    return False
                if len(keyword) > 100:  # 关键字长度限制
                    self.logger.error(f"关键字过长: {len(keyword)} 字符，最大允许100字符")
                    return False
            elif algorithm_type == 'image_reference':
                image_path = config.get('image_path', '')
                if not image_path:
                    self.logger.error("图片参照算法需要设置图片路径")
                    return False
                if not os.path.exists(image_path):
                    self.logger.error(f"图片文件不存在: {image_path}")
                    return False
                # 检查图片文件格式
                valid_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
                if not any(image_path.lower().endswith(ext) for ext in valid_extensions):
                    self.logger.error(f"不支持的图片格式: {image_path}，支持格式: {valid_extensions}")
                    return False
            else:
                self.logger.error(f"不支持的算法类型: {algorithm_type}")
                return False
            
            # 验证数值参数
            monitor_frequency = config.get('monitor_frequency', 0)
            if monitor_frequency <= 0:
                self.logger.error(f"监控频率必须大于0: {monitor_frequency}")
                return False
            if monitor_frequency < 0.1:  # 最小监控频率0.1秒
                self.logger.error(f"监控频率过高: {monitor_frequency}s，最小允许0.1s")
                return False
            if monitor_frequency > 60:  # 防止过高频率
                self.logger.error(f"监控频率过低: {monitor_frequency}s，最大允许60s")
                return False
            
            click_interval = config.get('click_interval', 0)
            if click_interval < 0:
                self.logger.error(f"点击间隔不能为负数: {click_interval}")
                return False
            if click_interval > 10000:  # 防止过长间隔
                self.logger.error(f"点击间隔过长: {click_interval}ms，最大允许10000ms")
                return False
            
            # 验证监控区域
            monitor_area = config.get('monitor_area')
            if monitor_area:
                required_area_fields = ['x', 'y', 'width', 'height']
                for field in required_area_fields:
                    if field not in monitor_area:
                        self.logger.error(f"监控区域缺少字段: {field}")
                        return False
                    if not isinstance(monitor_area[field], (int, float)) or monitor_area[field] < 0:
                        self.logger.error(f"监控区域字段值无效: {field}={monitor_area[field]}")
                        return False
                
                # 检查区域大小合理性
                if monitor_area['width'] <= 0 or monitor_area['height'] <= 0:
                    self.logger.error(f"监控区域大小无效: {monitor_area['width']}x{monitor_area['height']}")
                    return False
            
            # 验证鼠标按键
            mouse_button = config.get('mouse_button', 'left')
            if mouse_button not in ['left', 'right', 'middle']:
                self.logger.error(f"不支持的鼠标按键: {mouse_button}")
                return False
            
            self.logger.debug("配置验证完成，所有检查通过")
            return True
            
        except Exception as e:
            self.logger.error(f"验证配置时发生异常: {e}, 配置: {config}")
            import traceback
            self.logger.error(f"异常堆栈: {traceback.format_exc()}")
            return False
    
    def _enable_input_detection(self):
        """
        启用用户输入检测
        """
        try:
            # 记录初始鼠标位置
            coordinate_service = get_coordinate_service()
            self._initial_mouse_pos = coordinate_service.get_mouse_position()
            self._input_detection_active = True
            
            # 注册键盘事件监听
            keyboard.on_press_key('esc', self._on_esc_pressed)
            keyboard.on_press_key('space', self._on_space_pressed)
            
            self.logger.debug(f"用户输入检测已启用 - 初始鼠标位置: {self._initial_mouse_pos}")
            
        except Exception as e:
            self.logger.error(f"启用用户输入检测失败: {e}")
    
    def _disable_input_detection(self):
        """
        禁用用户输入检测
        """
        try:
            self._input_detection_active = False
            
            # 取消键盘事件监听
            keyboard.unhook_all()
            
            self.logger.debug("用户输入检测已禁用")
            
        except Exception as e:
            self.logger.error(f"禁用用户输入检测失败: {e}")
    
    def _on_esc_pressed(self, event):
        """
        ESC键按下事件处理
        """
        if self._input_detection_active and self._is_running:
            self._statistics['user_interruptions'] += 1
            self.logger.info("检测到ESC键按下，停止模拟任务")
            self.stop_task()
    
    def _on_space_pressed(self, event):
        """
        空格键按下事件处理
        """
        if self._input_detection_active and self._is_running:
            self._statistics['user_interruptions'] += 1
            self.logger.info("检测到空格键按下，停止模拟任务")
            self.stop_task()
    
    # 已移除_check_mouse_movement方法 - 不再支持鼠标移动退出
    
    def _check_timeout(self) -> bool:
        """
        检查任务是否超时
        
        Returns:
            bool: 任务是否超时
        """
        try:
            if not self._task_config or not self._start_time:
                return False
            
            timeout = self._task_config.get('timeout', 0)
            if timeout <= 0:
                return False  # 未设置超时或超时值无效
            
            elapsed_time = (datetime.now() - self._start_time).total_seconds()
            is_timeout = elapsed_time >= timeout
            
            if is_timeout:
                self.logger.debug(f"任务超时: 已运行 {elapsed_time:.1f}s, 超时设置 {timeout}s")
            
            return is_timeout
            
        except Exception as e:
            self.logger.error(f"检查任务超时失败: {e}")
            return False
    
    def _check_max_clicks(self) -> bool:
        """
        检查是否达到最大点击次数
        
        Returns:
            bool: 是否达到最大点击次数
        """
        try:
            if not self._task_config:
                return False
            
            max_clicks = self._task_config.get('max_clicks', 0)
            if max_clicks <= 0:
                return False  # 未设置最大点击次数或值无效
            
            current_clicks = self._statistics.get('total_clicks', 0)
            is_max_reached = current_clicks >= max_clicks
            
            if is_max_reached:
                self.logger.debug(f"达到最大点击次数: {current_clicks}/{max_clicks}")
            
            return is_max_reached
            
        except Exception as e:
            self.logger.error(f"检查最大点击次数失败: {e}")
            return False
    
    def _monitoring_loop(self):
        """
        监控循环主逻辑
        """
        self.logger.info("开始监控循环")
        
        try:
            # 启动后短暂等待，确保界面稳定
            initial_wait = 0.5
            self.logger.debug(f"启动后等待 {initial_wait}s 确保界面稳定")
            time.sleep(initial_wait)
            
            # 移除鼠标位置更新逻辑 - 不再需要鼠标移动检测
            
            while not self._stop_event.is_set() and self._is_running:
                # 更新检测周期计数
                self._statistics['detection_cycles'] += 1
                cycle_start_time = time.time()
                
                # 移除鼠标移动检测逻辑 - 只允许ESC或空格键退出
                
                # 检查超时条件
                if self._check_timeout():
                    self.logger.info("任务超时，停止模拟任务")
                    break
                
                # 检查最大点击次数
                if self._check_max_clicks():
                    self.logger.info("达到最大点击次数，停止模拟任务")
                    break
                
                # 执行算法检测和点击
                click_occurred = self._execute_algorithm_detection()
                
                # 关键修复：在点击发生后立即处理鼠标位置
                # 避免在等待期间检测到鼠标移动而停止任务
                if click_occurred:
                    self._handle_post_click_mouse_position()
                
                # 计算已用时间，调整等待时间
                cycle_elapsed = time.time() - cycle_start_time
                monitor_frequency = self._task_config.get('monitor_frequency', 1.0)
                remaining_wait = max(0, monitor_frequency - cycle_elapsed)
                
                if remaining_wait > 0:
                    # 智能分段等待，根据等待时间动态调整检查频率
                    if remaining_wait <= 0.5:
                        # 短等待时间：每50ms检查一次，提升响应速度
                        check_interval = 0.05
                    elif remaining_wait <= 2.0:
                        # 中等等待时间：每100ms检查一次，平衡响应和性能
                        check_interval = 0.1
                    else:
                        # 长等待时间：每200ms检查一次，减少资源消耗
                        check_interval = 0.2
                    
                    wait_segments = max(1, int(remaining_wait / check_interval))
                    actual_segment_time = remaining_wait / wait_segments
                    
                    self.logger.debug(f"分段等待: 总时长{remaining_wait:.3f}s, 分{wait_segments}段, 每段{actual_segment_time:.3f}s")
                    
                    for segment in range(wait_segments):
                        if self._stop_event.is_set():
                            self.logger.debug(f"等待第{segment+1}/{wait_segments}段时收到停止信号")
                            break
                        
                        # 移除等待期间的鼠标移动检测 - 只允许ESC或空格键退出
                        pass
                        
                        time.sleep(actual_segment_time)
                else:
                    # 如果检测时间已超过监控频率，记录警告
                    self.logger.warning(f"检测周期耗时过长: {cycle_elapsed:.3f}s > {monitor_frequency}s")
                
        except Exception as e:
            self.logger.error(f"监控循环异常: {e}")
            import traceback
            self.logger.error(f"异常堆栈: {traceback.format_exc()}")
        
        finally:
            # 确保任务状态正确更新
            if self._is_running:
                self._is_running = False
                self._disable_input_detection()
                self._generate_task_report()
                self.logger.info("任务因监控循环结束而停止")
            self.logger.info("监控循环结束")
    
    def _execute_algorithm_detection(self) -> bool:
        """
        执行算法检测和点击
        
        Returns:
            bool: 是否发生了点击操作
        """
        try:
            if not self._task_config:
                return False
            
            algorithm_type = self._task_config.get('algorithm_type')
            
            if algorithm_type == 'ocr_pool':
                return self._execute_ocr_pool_detection()
            elif algorithm_type == 'image_reference':
                return self._execute_image_reference_detection()
            else:
                self.logger.warning(f"未知的算法类型: {algorithm_type}")
                return False
                
        except Exception as e:
            self._statistics['errors'] += 1
            self.logger.error(f"执行算法检测失败: {e}")
            return False
    
    def _execute_ocr_pool_detection(self) -> bool:
        """
        执行OCR池检测
        
        Returns:
            bool: 是否发生了点击操作
        """
        try:
            keyword = self._task_config.get('keyword')
            monitor_area = self._task_config.get('monitor_area')
            
            self._statistics['ocr_detections'] += 1
            self.logger.debug(f"执行OCR池检测 - 关键字: {keyword}, 区域: {monitor_area}")
            
            # 调用智能点击服务的OCR检测方法
            if self._smart_click_service:
                result = self._smart_click_service.smart_click_targets(
                    target_keyword=keyword,
                    monitor_area=monitor_area,
                    max_targets=5,
                    use_precise_positioning=True
                )
                
                success = result.get('success', False) and result.get('clicked_targets', 0) > 0
                
                if success:
                    clicked_count = result.get('clicked_targets', 0)
                    self._statistics['total_matches'] += clicked_count
                    self._statistics['total_clicks'] += clicked_count
                    self._statistics['last_match_time'] = datetime.now()
                    self._statistics['last_click_time'] = datetime.now()
                    self.logger.info(f"OCR池检测成功，找到并点击了 {clicked_count} 个关键字: {keyword}")
                    return True
                else:
                    self.logger.debug(f"OCR池检测未找到关键字: {keyword}")
                    return False
            
            return False
            
        except Exception as e:
            self._statistics['errors'] += 1
            self.logger.error(f"OCR池检测失败: {e}")
            return False
    
    def _execute_image_reference_detection(self) -> bool:
        """
        执行图片参照检测
        
        Returns:
            bool: 是否发生了点击操作
        """
        try:
            image_path = self._task_config.get('image_path')
            monitor_area = self._task_config.get('monitor_area')
            
            self._statistics['image_detections'] += 1
            self.logger.debug(f"执行图片参照检测 - 图片: {image_path}, 区域: {monitor_area}")
            
            # 调用智能点击服务的图片检测方法
            if self._smart_click_service:
                # 获取监控频率配置
                monitor_frequency = self._task_config.get('monitor_frequency', 2.0)
                
                result = self._smart_click_service.smart_click_by_image(
                    reference_image_path=image_path,
                    monitor_area=monitor_area,
                    max_targets=5,
                    similarity_threshold=0.1,  # 降低阈值以提高匹配成功率
                    use_precise_matching=True,
                    monitor_frequency=monitor_frequency  # 传递监控频率用于动画时间计算
                )
                success = result.get('success', False) and result.get('clicked_targets', 0) > 0
                
                if success:
                    self._statistics['total_matches'] += 1
                    self._statistics['total_clicks'] += 1
                    self._statistics['last_match_time'] = datetime.now()
                    self._statistics['last_click_time'] = datetime.now()
                    self.logger.info(f"图片参照检测成功，找到并点击了图片: {image_path}")
                    return True
                else:
                    self.logger.debug(f"图片参照检测未找到图片: {image_path}")
                    return False
            
            return False
            
        except Exception as e:
            self._statistics['errors'] += 1
            self.logger.error(f"图片参照检测失败: {e}")
            return False
    
    def _handle_post_click_mouse_position(self):
        """
        处理点击后的鼠标位置管理
        移除鼠标位置管理逻辑 - 不再需要鼠标移动检测
        """
        try:
            self.logger.debug("点击操作完成 - 已移除鼠标位置管理逻辑")
            # 不再需要移动鼠标或更新位置，因为已移除鼠标移动检测
            pass
                    
        except Exception as e:
            self.logger.error(f"处理点击后操作失败: {e}")
    
    def _generate_task_report(self):
        """
        生成模拟任务总结报告
        """
        try:
            if not self._start_time:
                return
            
            end_time = self._end_time or datetime.now()
            duration = end_time - self._start_time
            
            # 计算性能指标
            total_detections = self._statistics['ocr_detections'] + self._statistics['image_detections']
            match_success_rate = (self._statistics['total_matches'] / total_detections * 100) if total_detections > 0 else 0
            click_success_rate = (self._statistics['total_clicks'] / self._statistics['total_matches'] * 100) if self._statistics['total_matches'] > 0 else 0
            avg_detection_interval = (duration.total_seconds() / self._statistics['detection_cycles']) if self._statistics['detection_cycles'] > 0 else 0
            
            report = f"""
========== 模拟任务总结报告 ==========
任务持续时间: {duration}
开始时间: {self._start_time.strftime('%Y-%m-%d %H:%M:%S')}
结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}

统计信息:
- 检测周期: {self._statistics['detection_cycles']} 次
- 总匹配次数: {self._statistics['total_matches']} 次
- 总点击次数: {self._statistics['total_clicks']} 次
- OCR检测次数: {self._statistics['ocr_detections']} 次
- 图像检测次数: {self._statistics['image_detections']} 次
- 用户中断次数: {self._statistics['user_interruptions']} 次
- 错误次数: {self._statistics['errors']} 次

性能指标:
- 匹配成功率: {match_success_rate:.2f}%
- 点击成功率: {click_success_rate:.2f}%
- 平均检测间隔: {avg_detection_interval:.2f} 秒

最后匹配时间: {self._statistics['last_match_time'].strftime('%Y-%m-%d %H:%M:%S') if self._statistics['last_match_time'] else '无'}
最后点击时间: {self._statistics['last_click_time'].strftime('%Y-%m-%d %H:%M:%S') if self._statistics['last_click_time'] else '无'}
=====================================
"""
            
            self.logger.info(report)
            
        except Exception as e:
            self.logger.error(f"生成任务报告失败: {e}")
    
    def reset_statistics(self):
        """
        重置统计信息
        """
        self._statistics = {
            'detection_cycles': 0,
            'total_matches': 0,
            'total_clicks': 0,
            'errors': 0,
            'last_match_time': None,
            'last_click_time': None,
            'ocr_detections': 0,
            'image_detections': 0,
            'user_interruptions': 0
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取当前统计信息
        """
        return self._statistics.copy()
    
    def __del__(self):
        """
        析构函数，确保资源清理
        """
        try:
            if self._is_running:
                self.stop_task()
        except:
            pass