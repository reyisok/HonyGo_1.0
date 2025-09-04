#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一坐标转换服务

提供项目中所有坐标处理的统一接口，包括：
- DPI感知的坐标转换
- 多显示器支持
- 逻辑坐标与物理坐标映射
- 屏幕坐标、窗口坐标、全局坐标转换

@author: Mr.Rey Copyright © 2025
@created: 2025-01-23 10:15:00
@modified: 2025-01-23 10:15:00
"""

import os
import sys
from typing import Dict, Optional, Tuple
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QApplication
from dataclasses import dataclass
import pyautogui
import numpy as np
from PIL import Image
import time

# 设置pyautogui的安全设置
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1

# Windows DPI API常量
SHCORE_DLL = ctypes.windll.shcore
USER32_DLL = ctypes.windll.user32
GDI32_DLL = ctypes.windll.gdi32

# DPI感知级别
PROCESS_DPI_UNAWARE = 0
PROCESS_SYSTEM_DPI_AWARE = 1
PROCESS_PER_MONITOR_DPI_AWARE = 2

# 监视器DPI类型
MDT_EFFECTIVE_DPI = 0
MDT_ANGULAR_DPI = 1
MDT_RAW_DPI = 2
















@dataclass
class CoordinateInfo:
    """坐标信息数据类"""
    x: int
    y: int
    screen_index: int = 0
    dpi_scale: float = 1.0
    is_logical: bool = True  # True表示逻辑坐标，False表示物理坐标


@dataclass
class ScreenInfo:
    """屏幕信息数据类"""
    index: int
    geometry: QRect
    available_geometry: QRect
    dpi_scale: float
    logical_dpi: float
    physical_dpi: float
    is_primary: bool


class CoordinateService:
    """统一坐标转换服务"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化坐标转换服务"""
        if self._initialized:
            return
            
        from src.ui.services.logging_service import get_logger
        self.logger = get_logger("CoordinateService", "System")
        self._screens_info: Dict[int, ScreenInfo] = {}
        self._primary_screen_index = 0
        self._global_dpi_scale = 1.0
        self._screen_initialized = False
        
        # 延迟初始化屏幕信息，避免过早调用QApplication
        self._initialized = True
        
        self.logger.info("坐标转换服务初始化完成，屏幕信息将延迟初始化")
    
    def _initialize_screens(self) -> None:
        """初始化屏幕信息"""
        if self._screen_initialized:
            return
            
        try:
            app = QApplication.instance()
            if not app:
                self.logger.warning("QApplication实例不存在，使用默认屏幕信息")
                self._use_default_screen_info()
                return
            
            screens = app.screens()
            primary_screen = app.primaryScreen()
            
            if not screens:
                self.logger.warning("未检测到任何屏幕，使用默认屏幕信息")
                self._use_default_screen_info()
                return
            
            # 获取Windows API的准确DPI缩放
            windows_dpi_scale = self._get_windows_dpi_scale()
            
            for i, screen in enumerate(screens):
                # 使用Windows API获取的DPI缩放，而不是Qt的devicePixelRatio
                screen_info = ScreenInfo(
                    index=i,
                    geometry=screen.geometry(),
                    available_geometry=screen.availableGeometry(),
                    dpi_scale=windows_dpi_scale,  # 使用Windows API的DPI缩放
                    logical_dpi=screen.logicalDotsPerInch(),
                    physical_dpi=screen.physicalDotsPerInch(),
                    is_primary=(screen == primary_screen)
                )
                
                self._screens_info[i] = screen_info
                
                if screen_info.is_primary:
                    self._primary_screen_index = i
                    self._global_dpi_scale = screen_info.dpi_scale
                
                self.logger.debug(
                    f"屏幕 {i}: 几何={screen_info.geometry}, "
                    f"DPI缩放={screen_info.dpi_scale}, "
                    f"逻辑DPI={screen_info.logical_dpi}, "
                    f"物理DPI={screen_info.physical_dpi}, "
                    f"主屏幕={screen_info.is_primary}"
                )
                
            self._screen_initialized = True
            self.logger.info(f"屏幕信息初始化完成，检测到 {len(self._screens_info)} 个显示器")
                
        except Exception as e:
            self.logger.error(f"初始化屏幕信息失败: {e}")
            self._use_default_screen_info()
    
    def _get_windows_dpi_scale(self) -> float:
        """使用Windows API获取准确的DPI缩放比例"""
        try:
            # 方法1: 使用GetDpiForSystem (Windows 10 1607+)
            try:
                system_dpi = USER32_DLL.GetDpiForSystem()
                return system_dpi / 96.0
            except:
                pass
            
            # 方法2: 使用GetDeviceCaps
            try:
                hdc = USER32_DLL.GetDC(0)
                if hdc:
                    dpi_x = GDI32_DLL.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
                    USER32_DLL.ReleaseDC(0, hdc)
                    return dpi_x / 96.0
            except:
                pass
            
            # 方法3: 使用GetDpiForMonitor
            try:
                monitor = USER32_DLL.MonitorFromPoint(wintypes.POINT(0, 0), 1)  # MONITOR_DEFAULTTOPRIMARY
                if monitor:
                    dpi_x = wintypes.UINT()
                    dpi_y = wintypes.UINT()
                    result = SHCORE_DLL.GetDpiForMonitor(monitor, MDT_EFFECTIVE_DPI, 
                                                       ctypes.byref(dpi_x), ctypes.byref(dpi_y))
                    if result == 0:  # S_OK
                        return dpi_x.value / 96.0
            except:
                pass
                
        except Exception as e:
            self.logger.warning(f"获取Windows DPI失败: {e}")
        
        return 1.0  # 默认值
    
    def _use_default_screen_info(self) -> None:
        """使用默认屏幕信息"""
        default_info = self._get_default_screen_info()
        self._screens_info[0] = default_info
        self._primary_screen_index = 0
        self._global_dpi_scale = default_info.dpi_scale
        self._screen_initialized = True
        self.logger.warning("使用默认屏幕信息")
    
    def get_screen_info(self, screen_index: Optional[int] = None) -> ScreenInfo:
        """获取屏幕信息"""
        self._initialize_screens()  # 确保屏幕信息已初始化
        
        if screen_index is None:
            screen_index = self._primary_screen_index
        
        if screen_index not in self._screens_info:
            self.logger.warning(f"屏幕索引 {screen_index} 不存在，使用主屏幕")
            screen_index = self._primary_screen_index
        
        return self._screens_info.get(screen_index, self._get_default_screen_info())
    
    def _get_default_screen_info(self) -> ScreenInfo:
        """获取默认屏幕信息"""
        # 即使在默认情况下，也尝试获取准确的DPI缩放
        windows_dpi_scale = self._get_windows_dpi_scale()
        
        return ScreenInfo(
            index=0,
            geometry=QRect(0, 0, 1920, 1080),
            available_geometry=QRect(0, 0, 1920, 1040),
            dpi_scale=windows_dpi_scale,  # 使用Windows API的DPI缩放
            logical_dpi=96.0,
            physical_dpi=96.0,
            is_primary=True
        )
    
    def get_primary_screen_dpi_scale(self) -> float:
        """获取主屏幕DPI缩放比例"""
        self._initialize_screens()  # 确保屏幕信息已初始化
        return self._global_dpi_scale
    
    def get_screen_dpi_scale(self, screen_index: Optional[int] = None) -> float:
        """获取指定屏幕的DPI缩放比例"""
        self._initialize_screens()  # 确保屏幕信息已初始化
        screen_info = self.get_screen_info(screen_index)
        return screen_info.dpi_scale
    
    def get_dpi_scale(self, screen_index: Optional[int] = None) -> float:
        """获取DPI缩放比例（兼容性方法）"""
        return self.get_screen_dpi_scale(screen_index)
    
    def logical_to_physical(self, x: int, y: int, screen_index: Optional[int] = None) -> Tuple[int, int]:
        """逻辑坐标转物理坐标"""
        dpi_scale = self.get_screen_dpi_scale(screen_index)
        physical_x = int(x * dpi_scale)
        physical_y = int(y * dpi_scale)
        
        self.logger.debug(
            f"逻辑坐标转物理坐标: ({x}, {y}) -> ({physical_x}, {physical_y}), "
            f"DPI缩放={dpi_scale}, 屏幕={screen_index or self._primary_screen_index}"
        )
        
        return physical_x, physical_y
    
    def physical_to_logical(self, x: int, y: int, screen_index: Optional[int] = None) -> Tuple[int, int]:
        """物理坐标转逻辑坐标"""
        dpi_scale = self.get_screen_dpi_scale(screen_index)
        if dpi_scale == 0:
            dpi_scale = 1.0
        
        logical_x = int(x / dpi_scale)
        logical_y = int(y / dpi_scale)
        
        self.logger.debug(
            f"物理坐标转逻辑坐标: ({x}, {y}) -> ({logical_x}, {logical_y}), "
            f"DPI缩放={dpi_scale}, 屏幕={screen_index or self._primary_screen_index}"
        )
        
        return logical_x, logical_y
    
    def get_screen_from_point(self, x: int, y: int) -> int:
        """根据坐标点确定所在屏幕"""
        self._initialize_screens()  # 确保屏幕信息已初始化
        
        point = QPoint(x, y)
        
        for screen_index, screen_info in self._screens_info.items():
            if screen_info.geometry.contains(point):
                return screen_index
        
        # 如果没有找到，返回主屏幕
        self.logger.debug(f"坐标点 ({x}, {y}) 不在任何屏幕范围内，返回主屏幕")
        return self._primary_screen_index
    
    def normalize_coordinates(self, x: int, y: int, width: int = 0, height: int = 0) -> Tuple[int, int, int, int]:
        """规范化坐标，确保坐标在有效范围内"""
        screen_index = self.get_screen_from_point(x, y)
        screen_info = self.get_screen_info(screen_index)
        
        # 确保坐标在屏幕范围内
        geometry = screen_info.geometry
        
        normalized_x = max(geometry.left(), min(x, geometry.right()))
        normalized_y = max(geometry.top(), min(y, geometry.bottom()))
        
        # 如果提供了宽高，确保区域不超出屏幕
        if width > 0 and height > 0:
            max_width = geometry.right() - normalized_x + 1
            max_height = geometry.bottom() - normalized_y + 1
            
            normalized_width = min(width, max_width)
            normalized_height = min(height, max_height)
        else:
            normalized_width = width
            normalized_height = height
        
        self.logger.debug(
            f"坐标规范化: ({x}, {y}, {width}, {height}) -> "
            f"({normalized_x}, {normalized_y}, {normalized_width}, {normalized_height}), "
            f"屏幕={screen_index}"
        )
        
        return normalized_x, normalized_y, normalized_width, normalized_height
    
    def convert_for_click(self, x: int, y: int, source_screen: Optional[int] = None) -> Tuple[int, int]:
        """为点击操作转换坐标（适用于pyautogui等库）"""
        # 大多数自动化库需要物理坐标
        return self.logical_to_physical(x, y, source_screen)
    
    def convert_for_animation(self, x: int, y: int, source_screen: Optional[int] = None) -> Tuple[int, int]:
        """为动画显示转换坐标（适用于Qt窗口定位）"""
        # Qt窗口定位通常使用逻辑坐标
        return x, y
    
    def convert_to_click_coordinates(self, x: int, y: int, source_screen: Optional[int] = None) -> Tuple[int, int]:
        """转换为点击坐标（别名方法，兼容旧代码）"""
        return self.convert_for_click(x, y, source_screen)
    
    def convert_to_animation_coordinates(self, x: int, y: int, source_screen: Optional[int] = None) -> Tuple[int, int]:
        """转换为动画坐标（别名方法，兼容旧代码）"""
        return self.convert_for_animation(x, y, source_screen)
    
    def convert_rect_logical_to_physical(self, rect: QRect, screen_index: Optional[int] = None) -> QRect:
        """矩形区域逻辑坐标转物理坐标"""
        dpi_scale = self.get_screen_dpi_scale(screen_index)
        
        physical_rect = QRect(
            int(rect.x() * dpi_scale),
            int(rect.y() * dpi_scale),
            int(rect.width() * dpi_scale),
            int(rect.height() * dpi_scale)
        )
        
        self.logger.debug(
            f"矩形逻辑坐标转物理坐标: {rect} -> {physical_rect}, "
            f"DPI缩放={dpi_scale}, 屏幕={screen_index or self._primary_screen_index}"
        )
        
        return physical_rect
    
    def convert_rect_physical_to_logical(self, rect: QRect, screen_index: Optional[int] = None) -> QRect:
        """矩形区域物理坐标转逻辑坐标"""
        dpi_scale = self.get_screen_dpi_scale(screen_index)
        if dpi_scale == 0:
            dpi_scale = 1.0
        
        logical_rect = QRect(
            int(rect.x() / dpi_scale),
            int(rect.y() / dpi_scale),
            int(rect.width() / dpi_scale),
            int(rect.height() / dpi_scale)
        )
        
        self.logger.debug(
            f"矩形物理坐标转逻辑坐标: {rect} -> {logical_rect}, "
            f"DPI缩放={dpi_scale}, 屏幕={screen_index or self._primary_screen_index}"
        )
        
        return logical_rect
    
    def refresh_screen_info(self) -> None:
        """刷新屏幕信息（当显示器配置改变时调用）"""
        self.logger.info("刷新屏幕信息")
        self._screens_info.clear()
        self._initialize_screens()
    
    def get_all_screens_info(self) -> Dict[int, ScreenInfo]:
        """获取所有屏幕信息"""
        self._initialize_screens()  # 确保屏幕信息已初始化
        return self._screens_info.copy()
    
    def is_point_in_screen(self, x: int, y: int, screen_index: Optional[int] = None) -> bool:
        """检查点是否在指定屏幕范围内"""
        self._initialize_screens()  # 确保屏幕信息已初始化
        
        if screen_index is None:
            # 检查是否在任何屏幕范围内
            for screen_info in self._screens_info.values():
                if screen_info.geometry.contains(QPoint(x, y)):
                    return True
            return False
        else:
            screen_info = self.get_screen_info(screen_index)
            return screen_info.geometry.contains(QPoint(x, y))
    
    def get_coordinate_info(self, x: int, y: int) -> CoordinateInfo:
        """获取坐标的详细信息"""
        screen_index = self.get_screen_from_point(x, y)
        screen_info = self.get_screen_info(screen_index)
        
        return CoordinateInfo(
            x=x,
            y=y,
            screen_index=screen_index,
            dpi_scale=screen_info.dpi_scale,
            is_logical=True  # 默认假设输入的是逻辑坐标
        )
    
    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[Image.Image]:
        """DPI感知屏幕截图
        
        Args:
            region: 截图区域 (x, y, width, height)，None表示全屏
            
        Returns:
            PIL Image对象，失败返回None
        """
        try:
            self.logger.debug(f"开始DPI感知屏幕截图 - 区域: {region}")
            
            if region:
                # 指定区域截图，需要转换为物理坐标
                x, y, width, height = region
                
                # 获取DPI缩放比例
                screen_index = self.get_screen_from_point(x, y)
                dpi_scale = self.get_screen_dpi_scale(screen_index)
                
                # 转换为物理坐标
                physical_x = int(x * dpi_scale)
                physical_y = int(y * dpi_scale)
                physical_width = int(width * dpi_scale)
                physical_height = int(height * dpi_scale)
                
                self.logger.debug(
                    f"DPI坐标转换: 逻辑({x}, {y}, {width}, {height}) -> "
                    f"物理({physical_x}, {physical_y}, {physical_width}, {physical_height}), "
                    f"DPI缩放={dpi_scale}"
                )
                
                # 规范化物理坐标
                norm_x, norm_y, norm_width, norm_height = self.normalize_coordinates(
                    physical_x, physical_y, physical_width, physical_height
                )
                
                screenshot = pyautogui.screenshot(region=(norm_x, norm_y, norm_width, norm_height))
            else:
                # 全屏截图
                screenshot = pyautogui.screenshot()
            
            self.logger.debug(f"DPI感知屏幕截图完成 - 尺寸: {screenshot.size}, 区域: {region}")
            return screenshot
            
        except Exception as e:
            self.logger.error(f"DPI感知屏幕截图失败，尝试标准截图: {e}")
            # 回退到标准截图
            try:
                if region:
                    x, y, width, height = region
                    screenshot = pyautogui.screenshot(region=(x, y, width, height))
                else:
                    screenshot = pyautogui.screenshot()
                self.logger.info("标准截图成功")
                return screenshot
            except Exception as fallback_e:
                self.logger.error(f"标准截图也失败: {fallback_e}")
                return None
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """获取当前鼠标位置（逻辑坐标）
        
        Returns:
            鼠标位置的逻辑坐标 (x, y)
        """
        try:
            # 获取物理坐标
            physical_x, physical_y = pyautogui.position()
            
            # 转换为逻辑坐标
            screen_index = self.get_screen_from_point(physical_x, physical_y)
            logical_x, logical_y = self.physical_to_logical(physical_x, physical_y, screen_index)
            
            self.logger.debug(f"获取鼠标位置: 物理({physical_x}, {physical_y}) -> 逻辑({logical_x}, {logical_y})")
            return logical_x, logical_y
            
        except Exception as e:
            self.logger.error(f"获取鼠标位置失败: {e}")
            return 0, 0
    
    def move_mouse_to(self, x: int, y: int, duration: float = 0.0) -> bool:
        """移动鼠标到指定位置（逻辑坐标）
        
        Args:
            x: 目标X坐标（逻辑坐标）
            y: 目标Y坐标（逻辑坐标）
            duration: 移动持续时间（秒），0表示瞬间移动
            
        Returns:
            移动是否成功
        """
        try:
            # 转换为物理坐标
            screen_index = self.get_screen_from_point(x, y)
            physical_x, physical_y = self.logical_to_physical(x, y, screen_index)
            
            # 规范化坐标
            norm_x, norm_y, _, _ = self.normalize_coordinates(physical_x, physical_y)
            
            self.logger.debug(
                f"移动鼠标: 逻辑({x}, {y}) -> 物理({physical_x}, {physical_y}) -> 规范化({norm_x}, {norm_y}), "
                f"持续时间={duration}s"
            )
            
            # 执行移动
            pyautogui.moveTo(norm_x, norm_y, duration=duration)
            return True
            
        except Exception as e:
            self.logger.error(f"移动鼠标失败: {e}")
            return False
    
    def click_at(self, x: int, y: int, button: str = 'left', clicks: int = 1, interval: float = 0.0) -> bool:
        """在指定位置点击鼠标（逻辑坐标）
        
        Args:
            x: 点击X坐标（逻辑坐标）
            y: 点击Y坐标（逻辑坐标）
            button: 鼠标按钮 ('left', 'right', 'middle')
            clicks: 点击次数
            interval: 多次点击间隔（秒）
            
        Returns:
            点击是否成功
        """
        try:
            # 转换为物理坐标
            screen_index = self.get_screen_from_point(x, y)
            physical_x, physical_y = self.logical_to_physical(x, y, screen_index)
            
            # 规范化坐标
            norm_x, norm_y, _, _ = self.normalize_coordinates(physical_x, physical_y)
            
            self.logger.debug(
                f"点击鼠标: 逻辑({x}, {y}) -> 物理({physical_x}, {physical_y}) -> 规范化({norm_x}, {norm_y}), "
                f"按钮={button}, 次数={clicks}, 间隔={interval}s"
            )
            
            # 执行点击
            pyautogui.click(norm_x, norm_y, button=button, clicks=clicks, interval=interval)
            return True
            
        except Exception as e:
            self.logger.error(f"点击鼠标失败: {e}")
            return False
    
    def left_click(self, x: int, y: int, clicks: int = 1, interval: float = 0.0) -> bool:
        """左键点击（逻辑坐标）"""
        return self.click_at(x, y, button='left', clicks=clicks, interval=interval)
    
    def right_click(self, x: int, y: int, clicks: int = 1, interval: float = 0.0) -> bool:
        """右键点击（逻辑坐标）"""
        return self.click_at(x, y, button='right', clicks=clicks, interval=interval)
    
    def middle_click(self, x: int, y: int, clicks: int = 1, interval: float = 0.0) -> bool:
        """中键点击（逻辑坐标）"""
        return self.click_at(x, y, button='middle', clicks=clicks, interval=interval)
    
    def click(self, x: int, y: int, button: str = 'left', clicks: int = 1, interval: float = 0.0) -> bool:
        """通用点击方法（逻辑坐标）- 兼容性接口"""
        return self.click_at(x, y, button=button, clicks=clicks, interval=interval)
    
    def get_screen_size(self, screen_index: Optional[int] = None) -> Tuple[int, int]:
        """获取屏幕尺寸（逻辑坐标）
        
        Args:
            screen_index: 屏幕索引，None表示主屏幕
            
        Returns:
            屏幕尺寸 (width, height)
        """
        try:
            screen_info = self.get_screen_info(screen_index)
            geometry = screen_info.geometry
            
            # 转换为逻辑坐标
            logical_width = int(geometry.width() / screen_info.dpi_scale)
            logical_height = int(geometry.height() / screen_info.dpi_scale)
            
            self.logger.debug(
                f"获取屏幕尺寸: 物理({geometry.width()}, {geometry.height()}) -> "
                f"逻辑({logical_width}, {logical_height}), DPI缩放={screen_info.dpi_scale}"
            )
            
            return logical_width, logical_height
            
        except Exception as e:
            self.logger.error(f"获取屏幕尺寸失败: {e}")
            # 返回默认尺寸
            return 1920, 1080


# 全局坐标服务实例（延迟初始化）
_coordinate_service: Optional[CoordinateService] = None


def get_coordinate_service() -> CoordinateService:
    """获取坐标转换服务实例（延迟初始化）"""
    global _coordinate_service
    if _coordinate_service is None:
        _coordinate_service = CoordinateService()
    return _coordinate_service