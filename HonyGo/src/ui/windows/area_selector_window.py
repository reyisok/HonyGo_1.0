#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
区域选择窗口模块

@author: Mr.Rey Copyright © 2025
@description: 提供可视化区域选择功能，允许用户在屏幕上框选监控区域
@version: 1.0.0
@created: 2025-09-01
"""

import logging
import sys
from PySide6.QtCore import QPoint
from PySide6.QtCore import QRect
from PySide6.QtCore import Qt
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtGui import QFont
from PySide6.QtGui import QIcon
from PySide6.QtGui import QPainter
from PySide6.QtGui import QPen
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QFrame
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget
from src.ui.services.coordinate_service import get_coordinate_service
from src.ui.services.logging_service import get_logger


class AreaSelectorWindow(QWidget):
    """
    区域选择窗口类
    提供全屏遮罩和区域选择功能
    """
    
    # 信号定义
    area_selected = Signal(dict)  # 区域选择完成信号
    selection_cancelled = Signal()  # 选择取消信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('AreaSelectorWindow')
        self._coordinate_service = None  # 延迟初始化
        
        # 选择状态
        self.selecting = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.selection_rect = QRect()
        
        # 屏幕信息
        self.screen = QApplication.primaryScreen()
        self.screen_geometry = self.screen.geometry()
        
        self.logger.info("开始初始化区域选择窗口，使用统一坐标转换服务")
        self._init_ui()
        self.logger.info("区域选择窗口初始化完成")
    
    @property
    def coordinate_service(self):
        """延迟获取坐标服务"""
        if self._coordinate_service is None:
            self._coordinate_service = get_coordinate_service()
        return self._coordinate_service
    
    def _init_ui(self):
        """
        初始化用户界面
        """
        try:
            # 设置窗口属性
            self.setWindowTitle("选择监控区域")
            self.setWindowFlags(
                Qt.WindowStaysOnTopHint | 
                Qt.FramelessWindowHint |
                Qt.Tool
            )
            
            # 设置窗口图标
            from pathlib import Path
            icon_path = Path(__file__).parent.parent / "resources" / "icons" / "HonyGo.ico"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                self.logger.info(f"设置窗口图标: {icon_path}")
            else:
                self.logger.warning(f"窗口图标文件不存在: {icon_path}")
            
            # 设置全屏显示
            self.setGeometry(self.screen_geometry)
            
            # 设置半透明背景
            self.setAttribute(Qt.WA_TranslucentBackground)
            # 使用PySide6原生样式设置半透明背景
            self.setAutoFillBackground(True)
            bg_palette = self.palette()
            bg_palette.setColor(bg_palette.ColorRole.Window, QColor(0, 0, 0, 100))
            self.setPalette(bg_palette)
            
            # 创建布局
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # 创建提示标签
            self._create_instruction_label(layout)
            
            # 创建控制按钮
            self._create_control_buttons(layout)
            
            # 设置鼠标跟踪
            self.setMouseTracking(True)
            
            self.logger.debug("区域选择窗口UI初始化完成")
            
        except Exception as e:
            self.logger.error(f"初始化区域选择窗口UI失败: {e}")
            raise
    
    def _create_instruction_label(self, layout):
        """
        创建操作说明标签
        """
        instruction_frame = QFrame()
        instruction_frame.setFixedHeight(80)
        
        # 使用原生样式设置边框
        instruction_frame.setFrameStyle(QFrame.Box)
        instruction_frame.setLineWidth(2)
        
        # 使用QPalette设置背景色和边框色
        palette = instruction_frame.palette()
        palette.setColor(instruction_frame.backgroundRole(), QColor(0, 0, 0, 180))
        palette.setColor(instruction_frame.foregroundRole(), QColor(76, 175, 80))  # #4CAF50
        instruction_frame.setPalette(palette)
        instruction_frame.setAutoFillBackground(True)
        
        # 设置内边距
        instruction_frame.setContentsMargins(20, 20, 20, 20)
        
        instruction_layout = QVBoxLayout(instruction_frame)
        
        # 主要说明
        main_label = QLabel("请拖拽鼠标选择监控区域")
        main_label.setAlignment(Qt.AlignCenter)
        
        # 使用原生方式设置字体和颜色
        font = QFont("Microsoft YaHei", 13)
        font.setBold(True)
        main_label.setFont(font)
        
        palette = main_label.palette()
        palette.setColor(main_label.foregroundRole(), QColor(255, 255, 255))  # #FFFFFF
        main_label.setPalette(palette)
        instruction_layout.addWidget(main_label)
        
        # 详细说明
        detail_label = QLabel("按住左键拖拽选择区域，右键取消选择，ESC键退出")
        detail_label.setAlignment(Qt.AlignCenter)
        
        # 使用原生方式设置字体和颜色
        font = QFont("Microsoft YaHei", 13)
        detail_label.setFont(font)
        
        palette = detail_label.palette()
        palette.setColor(detail_label.foregroundRole(), QColor(0, 0, 0))  # 黑色
        detail_label.setPalette(palette)
        instruction_layout.addWidget(detail_label)
        
        layout.addWidget(instruction_frame)
        layout.addStretch()
    
    def _create_control_buttons(self, layout):
        """
        创建控制按钮
        """
        button_frame = QFrame()
        button_frame.setFixedHeight(80)
        
        # 使用原生样式设置边框
        button_frame.setFrameStyle(QFrame.Box)
        button_frame.setLineWidth(2)
        
        # 使用QPalette设置背景色和边框色
        palette = button_frame.palette()
        palette.setColor(button_frame.backgroundRole(), QColor(0, 0, 0, 180))
        palette.setColor(button_frame.foregroundRole(), QColor(33, 150, 243))  # #2196F3
        button_frame.setPalette(palette)
        button_frame.setAutoFillBackground(True)
        
        # 设置内边距
        button_frame.setContentsMargins(20, 20, 20, 20)
        
        button_layout = QHBoxLayout(button_frame)
        button_layout.addStretch()
        
        # 确认按钮
        self.confirm_button = QPushButton("确认选择")
        self.confirm_button.setMaximumSize(150, 30)
        self.confirm_button.setFixedHeight(30)
        
        # 使用原生方式设置字体
        font = QFont("Microsoft YaHei", 13)
        font.setBold(True)
        self.confirm_button.setFont(font)
        
        # 使用QPalette设置颜色
        palette = self.confirm_button.palette()
        palette.setColor(self.confirm_button.backgroundRole(), QColor(76, 175, 80))  # #4CAF50
        palette.setColor(self.confirm_button.foregroundRole(), QColor(255, 255, 255))  # #FFFFFF
        self.confirm_button.setPalette(palette)
        self.confirm_button.setAutoFillBackground(True)
        self.confirm_button.clicked.connect(self._confirm_selection)
        self.confirm_button.setEnabled(False)
        button_layout.addWidget(self.confirm_button)
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.setMaximumSize(150, 30)
        cancel_button.setFixedHeight(30)
        
        # 使用原生方式设置字体
        font = QFont("Microsoft YaHei", 13)
        font.setBold(True)
        cancel_button.setFont(font)
        
        # 使用QPalette设置颜色
        palette = cancel_button.palette()
        palette.setColor(cancel_button.backgroundRole(), QColor(244, 67, 54))  # #f44336
        palette.setColor(cancel_button.foregroundRole(), QColor(255, 255, 255))  # #FFFFFF
        cancel_button.setPalette(palette)
        cancel_button.setAutoFillBackground(True)
        cancel_button.clicked.connect(self._cancel_selection)
        button_layout.addWidget(cancel_button)
        
        button_layout.addStretch()
        layout.addWidget(button_frame)
    
    def mousePressEvent(self, event):
        """
        鼠标按下事件
        """
        if event.button() == Qt.LeftButton:
            self.selecting = True
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.selection_rect = QRect()
            self.logger.debug(f"开始选择区域，起始点: ({self.start_point.x()}, {self.start_point.y()})")
        elif event.button() == Qt.RightButton:
            self._cancel_selection()
    
    def mouseMoveEvent(self, event):
        """
        鼠标移动事件
        """
        if self.selecting:
            self.end_point = event.pos()
            self.selection_rect = QRect(self.start_point, self.end_point).normalized()
            self.update()  # 触发重绘
    
    def mouseReleaseEvent(self, event):
        """
        鼠标释放事件
        """
        if event.button() == Qt.LeftButton and self.selecting:
            self.selecting = False
            self.end_point = event.pos()
            self.selection_rect = QRect(self.start_point, self.end_point).normalized()
            
            # 检查选择区域是否有效
            if self.selection_rect.width() > 10 and self.selection_rect.height() > 10:
                self.confirm_button.setEnabled(True)
                self.logger.debug(f"选择区域完成: {self.selection_rect}")
            else:
                self.confirm_button.setEnabled(False)
                self.logger.debug("选择区域太小，无效")
            
            self.update()
    
    def keyPressEvent(self, event):
        """
        键盘按下事件
        """
        if event.key() == Qt.Key_Escape:
            self._cancel_selection()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.confirm_button.isEnabled():
                self._confirm_selection()
    
    def paintEvent(self, event):
        """
        绘制事件
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制半透明背景
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        # 绘制选择区域
        if not self.selection_rect.isEmpty():
            # 绘制选择框
            pen = QPen(QColor(0, 255, 0), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(self.selection_rect)
            
            # 绘制选择区域信息
            self._draw_selection_info(painter)
            
            # 高亮选择区域（降低透明度）
            painter.fillRect(self.selection_rect, QColor(255, 255, 255, 30))
    
    def _draw_selection_info(self, painter):
        """
        绘制选择区域信息
        """
        if self.selection_rect.isEmpty():
            return
        
        # 设置字体
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        painter.setFont(font)
        
        # 准备信息文本
        info_text = (
            f"区域: {self.selection_rect.x()}, {self.selection_rect.y()}\n"
            f"尺寸: {self.selection_rect.width()} x {self.selection_rect.height()}"
        )
        
        # 计算文本位置
        text_rect = painter.fontMetrics().boundingRect(info_text)
        text_x = self.selection_rect.x() + 5
        text_y = self.selection_rect.y() - text_rect.height() - 5
        
        # 确保文本在屏幕内
        if text_y < 0:
            text_y = self.selection_rect.y() + self.selection_rect.height() + 20
        if text_x + text_rect.width() > self.width():
            text_x = self.width() - text_rect.width() - 5
        
        # 绘制背景
        bg_rect = QRect(text_x - 5, text_y - text_rect.height() - 5, 
                       text_rect.width() + 10, text_rect.height() + 10)
        painter.fillRect(bg_rect, QColor(0, 0, 0, 180))
        
        # 绘制文本
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(text_x, text_y, info_text)
    
    def _confirm_selection(self):
        """
        确认选择
        """
        if self.selection_rect.isEmpty():
            QMessageBox.warning(self, "选择错误", "请先选择一个有效的区域")
            return
        
        # 使用统一坐标转换服务规范化坐标
        raw_x = self.selection_rect.x()
        raw_y = self.selection_rect.y()
        raw_width = self.selection_rect.width()
        raw_height = self.selection_rect.height()
        
        # 规范化坐标，确保在有效范围内
        normalized_x, normalized_y, normalized_width, normalized_height = \
            self.coordinate_service.normalize_coordinates(raw_x, raw_y, raw_width, raw_height)
        
        # 获取坐标详细信息
        coord_info = self.coordinate_service.get_coordinate_info(normalized_x, normalized_y)
        
        # 构建区域信息
        area_info = {
            'x': normalized_x,
            'y': normalized_y,
            'width': normalized_width,
            'height': normalized_height,
            'screen_index': coord_info.screen_index if coord_info else 0,
            'dpi_scale': coord_info.dpi_scale if coord_info else 1.0,
            'raw_coordinates': {
                'x': raw_x,
                'y': raw_y,
                'width': raw_width,
                'height': raw_height
            }
        }
        
        self.logger.info(
            f"用户确认选择区域: 原始({raw_x}, {raw_y}, {raw_width}, {raw_height}) -> "
            f"规范化({normalized_x}, {normalized_y}, {normalized_width}, {normalized_height}), "
            f"屏幕={area_info['screen_index']}, DPI缩放={area_info['dpi_scale']}"
        )
        
        # 发送信号
        self.area_selected.emit(area_info)
        
        # 关闭窗口
        self.close()
    
    def _cancel_selection(self):
        """
        取消选择
        """
        self.logger.info("用户取消区域选择")
        
        # 发送信号
        self.selection_cancelled.emit()
        
        # 关闭窗口
        self.close()
    
    def showEvent(self, event):
        """
        窗口显示事件
        """
        super().showEvent(event)
        self.logger.debug("区域选择窗口已显示")
        
        # 获取焦点
        self.setFocus()
        self.activateWindow()
        self.raise_()
    
    def closeEvent(self, event):
        """
        窗口关闭事件
        """
        self.logger.debug("区域选择窗口正在关闭")
        super().closeEvent(event)


if __name__ == "__main__":
    # 测试代码
    app = QApplication(sys.argv)
    
    def on_area_selected(area_info):
        self.logger.info(f"选择的区域: {area_info}")
        app.quit()
    
    def on_selection_cancelled():
        self.logger.info("取消选择")
        app.quit()
    
    window = AreaSelectorWindow()
    window.area_selected.connect(on_area_selected)
    window.selection_cancelled.connect(on_selection_cancelled)
    window.show()
    
    sys.exit(app.exec())