#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HonyGo 关键词匹配蓝色标记组件
提供关键词匹配区域的视觉反馈标记

@author: Mr.Rey Copyright © 2025
"""

import threading
import time
import traceback
from typing import List, Optional, Tuple
from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRect, QTimer, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget
from src.ui.services.logging_service import get_logger

# 全局变量存储活动的标记
_active_markers = []


class KeywordMarkerWidget(QWidget):
    """关键词匹配标记组件"""
    
    def __init__(self, x: int, y: int, width: int, height: int, duration: int = 3000):
        super().__init__()
        self.logger = get_logger('KeywordMarker')
        
        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        # 标记参数
        self._opacity = 1.0
        self._border_width = 3
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        
        # 设置窗口大小和位置
        margin = 10
        self.setGeometry(x - margin, y - margin, width + 2 * margin, height + 2 * margin)
        
        # 创建动画
        self._setup_animation(duration)
        
        # 显示窗口
        self.show()
        
        # 添加到活动标记列表
        _active_markers.append(self)
        
    def _setup_animation(self, duration: int):
        """设置动画"""
        try:
            # 透明度动画 - 闪烁效果
            self._opacity_animation = QPropertyAnimation(self, b"opacity")
            self._opacity_animation.setDuration(800)  # 闪烁周期
            self._opacity_animation.setStartValue(1.0)
            self._opacity_animation.setEndValue(0.3)
            self._opacity_animation.setEasingCurve(QEasingCurve.InOutQuad)
            self._opacity_animation.setLoopCount(-1)  # 无限循环
            
            # 启动闪烁动画
            self._opacity_animation.start()
            
            # 设置自动隐藏定时器
            if duration > 0:
                # 检查是否在主线程中
                app = QApplication.instance()
                if app and app.thread() == threading.current_thread():
                    self._hide_timer = QTimer()
                    self._hide_timer.setSingleShot(True)
                    self._hide_timer.timeout.connect(self._on_hide_timeout)
                    self._hide_timer.start(duration)
                else:
                    # 在非主线程中使用线程定时器
                    import threading
                    def delayed_hide():
                        time.sleep(duration / 1000.0)  # 转换为秒
                        self._on_hide_timeout()
                    timer_thread = threading.Thread(target=delayed_hide, daemon=True)
                    timer_thread.start()
            
        except Exception as e:
            self.logger.error(f"设置关键词标记动画失败: {e}")
            self._on_hide_timeout()
            
    def _on_hide_timeout(self):
        """隐藏超时处理"""
        try:
            self.stop_marker()
        except Exception as e:
            self.logger.debug(f"标记隐藏超时处理失败: {e}")
            
    def stop_marker(self):
        """停止标记动画并关闭"""
        try:
            # 停止动画
            if hasattr(self, '_opacity_animation'):
                self._opacity_animation.stop()
                
            # 停止定时器
            if hasattr(self, '_hide_timer'):
                self._hide_timer.stop()
                
            # 从活动标记列表中移除
            if self in _active_markers:
                _active_markers.remove(self)
            
            # 关闭窗口
            self.close()
            
        except Exception as e:
            self.logger.debug(f"停止关键词标记失败: {e}")
            
    @Property(float)
    def opacity(self):
        return self._opacity
        
    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        self.update()
        
    def paintEvent(self, event):
        """绘制标记"""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 设置画笔 - 蓝色边框
            color = QColor(0, 120, 215, int(255 * self._opacity))
            pen = QPen(color, self._border_width)
            pen.setStyle(Qt.SolidLine)
            
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)  # 不填充
            
            # 计算绘制区域
            margin = 10
            rect = QRect(margin, margin, self._width, self._height)
            
            # 绘制矩形边框
            painter.drawRect(rect)
            
        except Exception as e:
            self.logger.debug(f"绘制关键词标记失败: {e}")


def show_keyword_marker(x: int, y: int, width: int, height: int, duration: int = 3000) -> Optional[KeywordMarkerWidget]:
    """
    在指定位置显示关键词匹配标记
    
    Args:
        x: 标记位置X坐标
        y: 标记位置Y坐标
        width: 标记宽度
        height: 标记高度
        duration: 显示持续时间（毫秒），0表示不自动隐藏
        
    Returns:
        KeywordMarkerWidget: 标记组件，失败时返回None
    """
    logger = get_logger('KeywordMarker')
    
    try:
        # 检查是否有QApplication实例
        app = QApplication.instance()
        if app is None:
            logger.warning("没有QApplication实例，无法显示关键词标记")
            return None
            
        # 创建标记组件
        marker_widget = KeywordMarkerWidget(x, y, width, height, duration)
        
        logger.debug(f"显示关键词标记: 位置({x}, {y}), 大小({width}x{height}), 持续时间={duration}ms")
        
        return marker_widget
        
    except Exception as e:
        logger.error(f"显示关键词标记失败: {e}")
        logger.error(traceback.format_exc())
        return None


def hide_keyword_marker(marker: KeywordMarkerWidget) -> None:
    """
    隐藏指定的关键词标记
    
    Args:
        marker: 要隐藏的标记组件
    """
    logger = get_logger('KeywordMarker')
    
    try:
        if marker and marker in _active_markers:
            _active_markers.remove(marker)
            marker.stop_marker()
            marker.deleteLater()
            logger.debug("关键词标记已隐藏")
    except Exception as e:
        logger.error(f"隐藏关键词标记失败: {e}")


def hide_all_keyword_markers() -> None:
    """
    隐藏所有活动的关键词标记
    """
    logger = get_logger('KeywordMarker')
    
    try:
        markers_to_remove = _active_markers.copy()
        for marker in markers_to_remove:
            hide_keyword_marker(marker)
        
        logger.info(f"已隐藏 {len(markers_to_remove)} 个关键词标记")
    except Exception as e:
        logger.error(f"隐藏所有关键词标记失败: {e}")


def show_multiple_keyword_markers(positions: List[Tuple[int, int, int, int]]) -> List[KeywordMarkerWidget]:
    """
    在多个位置显示关键词匹配标记
    
    Args:
        positions: 标记位置列表 [(x1, y1, width1, height1), (x2, y2, width2, height2), ...]
        
    Returns:
        List[KeywordMarkerWidget]: 标记组件列表
    """
    logger = get_logger('KeywordMarker')
    
    markers = []
    try:
        for x, y, width, height in positions:
            marker = show_keyword_marker(x, y, width, height)
            if marker:
                markers.append(marker)
                
        logger.info(f"批量显示关键词标记完成，共{len(markers)}个标记")
        
    except Exception as e:
        logger.error(f"显示批量关键词标记失败: {e}")
        
    return markers


def cleanup_all_keyword_markers() -> None:
    """
    清理所有活动的关键词标记
    在程序退出时调用，防止C++对象已删除错误
    """
    logger = get_logger('KeywordMarker')
    
    try:
        markers_to_clean = _active_markers.copy()  # 创建副本避免迭代时修改
        cleaned_count = 0
        
        for marker_widget in markers_to_clean:
            try:
                if marker_widget is None:
                    continue
                    
                # 检查C++对象是否仍然有效
                try:
                    _ = marker_widget.isVisible()
                    # C++对象有效，正常关闭
                    if not marker_widget.isHidden():
                        marker_widget.close()
                    marker_widget.deleteLater()
                    cleaned_count += 1
                except RuntimeError:
                    # C++对象已删除，只需清理Python引用
                    cleaned_count += 1
                    
            except Exception as e:
                logger.debug(f"清理单个关键词标记时出错: {e}")
                cleaned_count += 1
        
        # 清空活动标记列表
        _active_markers.clear()
        
        if cleaned_count > 0:
            logger.info(f"已清理 {cleaned_count} 个关键词标记")
            
    except Exception as e:
        logger.error(f"清理所有关键词标记失败: {e}")
        # 强制清空列表
        _active_markers.clear()