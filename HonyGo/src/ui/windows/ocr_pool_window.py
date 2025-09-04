#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR实例池管理器窗口
按照UI2.txt设计实现的PySide6二级界面

@author: Mr.Rey Copyright © 2025
"""

import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QTextEdit, QComboBox,
    QFrame, QSizePolicy, QApplication, QMessageBox, QTabWidget,
    QProgressBar, QSplitter, QHeaderView, QAbstractItemView, QStatusBar
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QPixmap, QFont, QIcon, QColor

# 导入requests用于HTTP请求
try:
    import requests
except ImportError:
    requests = None

# 导入统一日志服务
from src.ui.services.logging_service import get_logger


class OCRPoolStatusThread(QThread):
    """
    OCR实例池状态监控线程（已移除自动定时刷新）
    @author: Mr.Rey Copyright © 2025
    """
    status_updated = Signal(dict)  # 状态更新信号
    
    def __init__(self, ocr_pool_api_base="http://127.0.0.1:8900"):
        super().__init__()
        self.running = False  # 默认不运行
        self.ocr_pool_api_base = ocr_pool_api_base
        self.logger = get_logger("OCRPoolStatusThread", "Application")
    
    def run(self):
        # 移除定时刷新逻辑，改为手动触发模式
        self.logger.info("OCR实例池状态监控线程已启动（手动刷新模式）")
        # 不再进行循环刷新，等待手动触发
        pass
    
    def refresh_status(self):
        """
        手动刷新状态数据
        @author: Mr.Rey Copyright © 2025
        """
        try:
            status_data = self._get_pool_status()
            self.status_updated.emit(status_data)
            self.logger.debug("手动刷新OCR实例池状态完成")
        except Exception as e:
            self.logger.error(f"获取OCR实例池状态失败: {e}")
            # 发送错误状态，不再使用模拟数据
            error_data = {
                'status': 'error',
                'message': f'OCR池连接失败: {str(e)}',
                'data': None
            }
            self.status_updated.emit(error_data)
    
    def _get_pool_status(self):
        """
        从OCR池服务获取实际状态数据
        @author: Mr.Rey Copyright © 2025
        """
        if not requests:
            raise ImportError("requests模块不可用，无法连接OCR池服务")
        
        try:
            # 获取池状态
            status_response = requests.get(f'{self.ocr_pool_api_base}/status', timeout=5)
            # 获取实例列表
            instances_response = requests.get(f'{self.ocr_pool_api_base}/instances', timeout=5)
            
            if status_response.status_code == 200 and instances_response.status_code == 200:
                status_data = status_response.json()
                instances_data = instances_response.json()
                
                if status_data.get('status') == 'success' and instances_data.get('status') == 'success':
                    # 合并状态和实例数据
                    combined_data = {
                        'status': 'success',
                        'data': {
                            'pool_status': status_data['data'],
                            'instances': instances_data['data']
                        }
                    }
                    return combined_data
            
            raise Exception(f"OCR池服务API返回错误状态码: {status_response.status_code}")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"无法连接到OCR池服务(127.0.0.1:8900)，服务可能未启动: {e}")
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"连接OCR池服务超时: {e}")
        except Exception as e:
            raise Exception(f"调用OCR池服务API失败: {e}")
    

    
    def stop(self):
        self.running = False
        self.quit()
        self.wait()


class OCRPoolWindow(QMainWindow):
    """
    OCR实例池管理器窗口
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化日志记录器
        self.logger = get_logger("OCRPoolWindow", "Application")
        self.logger.info("开始初始化OCR实例池管理器窗口")
        
        # 界面组件
        self.central_widget = None
        self.instance_table = None
        self.detail_tabs = None
        self.instance_log_display = None
        self.selected_instance_id = None
        
        # OCR池服务配置
        self.ocr_pool_api_base = "http://127.0.0.1:8900"
        
        # 状态监控线程（手动刷新模式）
        self.status_thread = OCRPoolStatusThread(ocr_pool_api_base=self.ocr_pool_api_base)
        self.status_thread.status_updated.connect(self._on_status_updated)
        
        # 初始化界面
        self._init_ui()
        self._connect_signals()
        
        self.logger.info("OCR实例池管理器已切换为手动刷新模式，避免无连接时卡死")
        
        # 执行一次初始状态刷新
        self.status_thread.refresh_status()
        
        self.logger.info("OCR实例池管理器窗口初始化完成")
    
    def _init_ui(self):
        """
        初始化用户界面 - 重新设计合理的布局结构
        页面尺寸固定为1000px×800px，采用垂直布局：顶部工具栏->中间主内容区->底部状态栏
        """
        self.logger.info("开始初始化OCR实例池管理器界面组件")
        
        # 设置窗口属性 - 按照文档要求固定尺寸
        self.setWindowTitle("OCR实例池管理器")
        self.setFixedSize(1000, 800)  # 固定尺寸1000px×800px
        
        # 设置主窗口背景色 #f0f0f0（浅灰色）
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(240, 240, 240))  # #f0f0f0
        self.setPalette(palette)
        
        # 设置窗口图标
        icon_path = Path(__file__).parent.parent / "resources" / "icons" / "HonyGo.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局 - 使用QVBoxLayout实现垂直布局
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建顶部工具栏
        self._create_top_toolbar(main_layout)
        
        # 创建中间主内容区域（左右分布）
        self._create_main_content_area(main_layout)
        
        # 创建底部状态栏
        self._create_bottom_status_bar(main_layout)
        
        self.logger.info("OCR实例池管理器界面组件初始化完成")
    
    def _create_top_toolbar(self, parent_layout):
        """
        创建顶部工具栏
        高度：50px，背景色：#e0e0e0，包含标题和操作按钮
        """
        self.logger.debug("创建顶部工具栏")
        
        # 顶部工具栏容器
        toolbar_widget = QWidget()
        toolbar_widget.setFixedHeight(50)
        toolbar_widget.setAutoFillBackground(True)
        toolbar_palette = toolbar_widget.palette()
        toolbar_palette.setColor(toolbar_widget.backgroundRole(), QColor(224, 224, 224))  # #e0e0e0
        toolbar_widget.setPalette(toolbar_palette)
        toolbar_widget.setStyleSheet("border-bottom: 1px solid #cccccc;")
        
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(15, 10, 15, 10)
        toolbar_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("OCR实例池管理器")
        title_label.setFont(QFont("微软雅黑", 18, QFont.Bold))
        title_label.setStyleSheet("color: #333333;")
        toolbar_layout.addWidget(title_label)
        
        # 弹性空间
        toolbar_layout.addStretch()
        
        # 刷新按钮
        self.refresh_button = self._create_operation_button("刷新", "#28a745", self._on_refresh_clicked)
        toolbar_layout.addWidget(self.refresh_button)
        
        # 设置按钮
        self.settings_button = self._create_operation_button("设置", "#ffc107", self._on_settings_clicked)
        toolbar_layout.addWidget(self.settings_button)
        
        parent_layout.addWidget(toolbar_widget)
    
    def _create_main_content_area(self, parent_layout):
        """
        创建中间主内容区域（左右分布）
        左侧：实例池概览 + 实例操作，右侧：实例列表 + 实例详情
        """
        self.logger.debug("创建主内容区域")
        
        # 主内容区域容器
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(5)
        content_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建左侧区域（实例池概览 + 实例操作）
        self._create_left_panel(content_layout)
        
        # 创建右侧区域（实例列表 + 实例详情）
        self._create_right_panel(content_layout)
        
        parent_layout.addWidget(content_widget)
    
    def _create_left_panel(self, parent_layout):
        """
        创建左侧区域（实例池概览 + 实例操作）
        背景色：#ffffff，边框：1px solid #cccccc
        """
        self.logger.debug("创建左侧面板")
        
        # 左侧容器
        left_widget = QWidget()
        left_widget.setFixedWidth(300)  # 左侧固定宽度
        left_widget.setAutoFillBackground(True)
        left_palette = left_widget.palette()
        left_palette.setColor(left_widget.backgroundRole(), QColor(255, 255, 255))  # #ffffff
        left_widget.setPalette(left_palette)
        left_widget.setStyleSheet("border: 1px solid #cccccc;")
        
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)
        
        # 实例池概览部分（自适应高度）
        overview_widget = self._create_pool_overview()
        left_layout.addWidget(overview_widget)
        
        # 实例操作部分（固定高度400px）
        operation_widget = self._create_instance_operations()
        operation_widget.setFixedHeight(400)
        left_layout.addWidget(operation_widget)
        
        # 添加弹性空间
        left_layout.addStretch()
        
        parent_layout.addWidget(left_widget)
    
    def _create_pool_overview(self):
        """
        创建实例池概览部分
        字体：微软雅黑，大小12px，颜色#333333
        """
        overview_widget = QWidget()
        overview_layout = QVBoxLayout(overview_widget)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        overview_layout.setSpacing(8)
        
        # 标题
        title_label = QLabel("实例池概览")
        title_label.setFont(QFont("微软雅黑", 14, QFont.Bold))  # 标题字体14px
        title_label.setStyleSheet("color: #333333; background-color: #e0e0e0; padding: 5px;")
        overview_layout.addWidget(title_label)
        
        # 统计信息标签
        self.total_instances_label = QLabel("总实例数: 0")
        self.running_instances_label = QLabel("运行实例: 0")
        self.idle_instances_label = QLabel("空闲实例: 0")
        self.cpu_usage_label = QLabel("CPU使用率: 0%")
        self.memory_usage_label = QLabel("内存使用: 0MB")
        
        # 设置标签样式
        for label in [self.total_instances_label, self.running_instances_label, 
                     self.idle_instances_label, self.cpu_usage_label, self.memory_usage_label]:
            label.setFont(QFont("微软雅黑", 12))  # 其他字体12px
            label.setStyleSheet("color: #333333; padding: 2px;")
            overview_layout.addWidget(label)
        
        return overview_widget
    
    def _create_instance_operations(self):
        """
        创建实例操作部分
        按钮大小：宽100px，高30px，间距10px
        """
        operation_widget = QWidget()
        operation_layout = QVBoxLayout(operation_widget)
        operation_layout.setContentsMargins(0, 0, 0, 0)
        operation_layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("实例操作")
        title_label.setFont(QFont("微软雅黑", 14, QFont.Bold))  # 标题字体14px
        title_label.setStyleSheet("color: #333333; background-color: #e0e0e0; padding: 5px;")
        operation_layout.addWidget(title_label)
        
        # 按钮网格布局
        button_grid = QGridLayout()
        button_grid.setSpacing(10)
        
        # 创建操作按钮
        self.start_button = self._create_operation_button("启动实例", "#28a745", self._on_start_instance_clicked)
        self.stop_button = self._create_operation_button("停止实例", "#dc3545", self._on_stop_instance_clicked)
        self.restart_button = self._create_operation_button("重启实例", "#007bff", self._on_restart_instance_clicked)
        self.add_button = self._create_operation_button("添加实例", "#ffc107", self._on_add_instance_clicked)
        self.remove_button = self._create_operation_button("移除实例", "#6f42c1", self._on_remove_instance_clicked)
        
        # 按钮布局（2列）
        button_grid.addWidget(self.start_button, 0, 0)
        button_grid.addWidget(self.stop_button, 0, 1)
        button_grid.addWidget(self.restart_button, 1, 0)
        button_grid.addWidget(self.add_button, 1, 1)
        button_grid.addWidget(self.remove_button, 2, 0, 1, 2)  # 跨两列
        
        operation_layout.addLayout(button_grid)
        operation_layout.addStretch()  # 底部弹性空间
        
        return operation_widget
    
    def _create_operation_button(self, text, color, callback):
        """
        创建操作按钮
        字体：微软雅黑，大小12px，颜色#ffffff
        """
        button = QPushButton(text)
        button.setFixedSize(100, 30)  # 固定大小100px×30px
        button.setFont(QFont("微软雅黑", 12))  # 其他字体12px
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: #ffffff;
                border: none;
                border-radius: 0px;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(color)};
            }}
        """)
        button.clicked.connect(callback)
        return button
    
    def _darken_color(self, hex_color):
        """
        将颜色亮度降低10%
        """
        # 移除#号
        hex_color = hex_color.lstrip('#')
        # 转换为RGB
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        # 降低亮度10%
        r = max(0, int(r * 0.9))
        g = max(0, int(g * 0.9))
        b = max(0, int(b * 0.9))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _create_right_panel(self, parent_layout):
        """
        创建右侧区域（实例列表 + 实例详情）
        背景色：#ffffff，边框：1px solid #cccccc
        """
        self.logger.debug("创建右侧面板")
        
        # 右侧容器
        right_widget = QWidget()
        right_widget.setAutoFillBackground(True)
        right_palette = right_widget.palette()
        right_palette.setColor(right_widget.backgroundRole(), QColor(255, 255, 255))  # #ffffff
        right_widget.setPalette(right_palette)
        right_widget.setStyleSheet("border: 1px solid #cccccc;")
        
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)
        
        # 实例列表部分（固定高度280px）
        list_widget = self._create_instance_list()
        list_widget.setFixedHeight(280)
        right_layout.addWidget(list_widget)
        
        # 实例详情部分（固定高度390px）
        detail_widget = self._create_instance_detail()
        detail_widget.setFixedHeight(390)
        right_layout.addWidget(detail_widget)
        
        # 添加弹性空间
        right_layout.addStretch()
        
        parent_layout.addWidget(right_widget)
    
    def _create_instance_list(self):
        """
        创建实例列表部分
        表格样式：边框1px solid #cccccc，表头背景#f0f0f0
        """
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(8)
        
        # 标题
        title_label = QLabel("实例列表")
        title_label.setFont(QFont("微软雅黑", 14, QFont.Bold))  # 标题字体14px
        title_label.setStyleSheet("color: #333333; background-color: #e0e0e0; padding: 5px;")
        list_layout.addWidget(title_label)
        
        # 实例表格
        self.instance_table = QTableWidget()
        self.instance_table.setColumnCount(7)
        self.instance_table.setHorizontalHeaderLabels(["实例ID", "状态", "CPU%", "内存MB", "处理数", "错误数", "最后活动"])
        
        # 设置表格样式
        self.instance_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #cccccc;
                gridline-color: #cccccc;
                background-color: #000000;
                color: #8B4513;
                font-family: 微软雅黑;
                font-size: 12px;  /* 其他字体12px */
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #cccccc;
                padding: 5px;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eeeeee;
            }
            QTableWidget::item:selected {
                background-color: rgba(227, 242, 253, 0.3);
            }
            QTableWidget::item:selected:hover {
                background-color: rgba(227, 242, 253, 0.1);
                color: #000000;
            }
        """)
        
        # 设置表格属性
        self.instance_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.instance_table.setAlternatingRowColors(True)
        self.instance_table.horizontalHeader().setStretchLastSection(True)
        
        list_layout.addWidget(self.instance_table)
        
        return list_widget
    
    def _create_instance_detail(self):
        """
        创建实例详情部分
        标签页样式：边框1px solid #cccccc，标签背景#f0f0f0
        """
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(8)
        
        # 标题
        title_label = QLabel("实例详情")
        title_label.setFont(QFont("微软雅黑", 18, QFont.Bold))  # 标题18px
        title_label.setStyleSheet("color: #333333; background-color: #e0e0e0; padding: 5px;")
        detail_layout.addWidget(title_label)
        
        # 详情标签页
        self.detail_tabs = QTabWidget()
        self.detail_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #cccccc;
                padding: 5px 10px;
                margin-right: 2px;
                font-family: 微软雅黑;
                font-size: 14px;  /* 普通字体14px */
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom: 1px solid #ffffff;
            }
        """)
        
        # 基本信息标签页
        info_tab = QWidget()
        info_tab.setStyleSheet("background-color: #000000;")
        info_layout = QVBoxLayout(info_tab)
        self.instance_info_display = QTextEdit()
        self.instance_info_display.setReadOnly(True)
        self.instance_info_display.setStyleSheet("""
            QTextEdit {
                border: none;
                background-color: #000000;
                font-family: 微软雅黑;
                font-size: 12px;  /* 其他字体12px */
                color: #ffffff;
            }
        """)
        info_layout.addWidget(self.instance_info_display)
        self.detail_tabs.addTab(info_tab, "基本信息")
        
        # 日志标签页
        log_tab = QWidget()
        log_tab.setStyleSheet("background-color: #000000;")
        log_layout = QVBoxLayout(log_tab)
        self.instance_log_display = QTextEdit()
        self.instance_log_display.setReadOnly(True)
        self.instance_log_display.setStyleSheet("""
            QTextEdit {
                border: none;
                background-color: #000000;
                font-family: 微软雅黑;
                font-size: 12px;
                color: #ffffff;
            }
        """)
        log_layout.addWidget(self.instance_log_display)
        self.detail_tabs.addTab(log_tab, "运行日志")
        
        detail_layout.addWidget(self.detail_tabs)
        
        return detail_widget
    

    
    def _create_bottom_status_bar(self, parent_layout):
        """
        创建底部状态栏
        高度：30px，背景色：#f0f0f0，字体：微软雅黑12px
        """
        self.logger.debug("创建底部状态栏")
        
        # 状态栏容器
        status_widget = QWidget()
        status_widget.setFixedHeight(30)
        status_widget.setAutoFillBackground(True)
        status_palette = status_widget.palette()
        status_palette.setColor(status_widget.backgroundRole(), QColor(240, 240, 240))  # #f0f0f0
        status_widget.setPalette(status_palette)
        status_widget.setStyleSheet("border-top: 1px solid #cccccc;")
        
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(15, 5, 15, 5)
        status_layout.setSpacing(10)
        
        # 状态信息标签
        self.status_label = QLabel("就绪 - OCR实例池管理器已启动")
        self.status_label.setFont(QFont("微软雅黑", 12))  # 其他字体12px
        self.status_label.setStyleSheet("color: #333333;")
        status_layout.addWidget(self.status_label)
        
        # 弹性空间
        status_layout.addStretch()
        
        # 连接状态指示器
        self.connection_status_label = QLabel("连接状态: 检查中...")
        self.connection_status_label.setFont(QFont("微软雅黑", 12))  # 其他字体12px
        self.connection_status_label.setStyleSheet("color: #666666;")
        status_layout.addWidget(self.connection_status_label)
        
        # 分隔符
        separator = QLabel("|")
        separator.setFont(QFont("微软雅黑", 12))  # 其他字体12px
        separator.setStyleSheet("color: #cccccc;")
        status_layout.addWidget(separator)
        
        # 最后更新时间标签
        self.last_update_label = QLabel("最后更新：未更新")
        self.last_update_label.setFont(QFont("微软雅黑", 12))  # 其他字体12px
        self.last_update_label.setStyleSheet("color: #757575;")
        status_layout.addWidget(self.last_update_label)
        
        parent_layout.addWidget(status_widget)
    
    # 按钮事件处理方法
    def _on_start_instance_clicked(self):
        """
        启动实例按钮点击事件
        """
        self.logger.info("用户点击启动实例按钮")
        selected_rows = self.instance_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_bar.showMessage("请先选择要启动的实例")
            return
        
        for index in selected_rows:
            instance_id = self.instance_table.item(index.row(), 0).text()
            self.logger.info(f"启动实例: {instance_id}")
            # TODO: 实现启动实例逻辑
        
        self.status_bar.showMessage("实例启动命令已发送")
    
    def _on_stop_instance_clicked(self):
        """
        停止实例按钮点击事件
        """
        self.logger.info("用户点击停止实例按钮")
        selected_rows = self.instance_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_bar.showMessage("请先选择要停止的实例")
            return
        
        for index in selected_rows:
            instance_id = self.instance_table.item(index.row(), 0).text()
            self.logger.info(f"停止实例: {instance_id}")
            # TODO: 实现停止实例逻辑
        
        self.status_bar.showMessage("实例停止命令已发送")
    
    def _on_restart_instance_clicked(self):
        """
        重启实例按钮点击事件
        """
        self.logger.info("用户点击重启实例按钮")
        selected_rows = self.instance_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_bar.showMessage("请先选择要重启的实例")
            return
        
        for index in selected_rows:
            instance_id = self.instance_table.item(index.row(), 0).text()
            self.logger.info(f"重启实例: {instance_id}")
            # TODO: 实现重启实例逻辑
        
        self.status_bar.showMessage("实例重启命令已发送")
    
    def _on_add_instance_clicked(self):
        """
        添加实例按钮点击事件
        """
        self.logger.info("用户点击添加实例按钮")
        # TODO: 实现添加实例逻辑
        self.status_bar.showMessage("添加实例功能开发中")
    
    def _on_remove_instance_clicked(self):
        """
        移除实例按钮点击事件
        """
        self.logger.info("用户点击移除实例按钮")
        selected_rows = self.instance_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_bar.showMessage("请先选择要移除的实例")
            return
        
        for index in selected_rows:
            instance_id = self.instance_table.item(index.row(), 0).text()
            self.logger.info(f"移除实例: {instance_id}")
            # TODO: 实现移除实例逻辑
        
        self.status_bar.showMessage("实例移除命令已发送")
        
        # 设置按钮
        self.settings_button = self._create_operation_button("设置", "#ff9800", self._on_settings_clicked)
        top_layout.addWidget(self.settings_button)
    
    # 旧方法已删除，使用新的布局方法
    
    # 旧的_create_control_panel方法已删除，使用新的布局方法


    
    # 旧的_create_main_panel方法已删除，使用新的布局方法
    
    def _create_status_section(self, parent_layout):
        """
        创建底部状态栏
        """
        self.logger.debug("创建底部状态栏")
        
        status_frame = QFrame()
        status_frame.setFixedHeight(32)
        status_frame.setFrameStyle(QFrame.Box)
        status_frame.setLineWidth(1)
        status_frame.setAutoFillBackground(True)
        status_palette = status_frame.palette()
        status_palette.setColor(status_frame.backgroundRole(), QColor(255, 255, 255))
        status_frame.setPalette(status_palette)
        
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(12, 6, 12, 6)
        status_layout.setSpacing(16)
        
        # 连接状态
        self.connection_status_label = QLabel("连接状态: 未连接")
        self.connection_status_label.setFont(QFont("Microsoft YaHei UI", 14))  # 普通字体14px
        connection_palette = self.connection_status_label.palette()
        connection_palette.setColor(self.connection_status_label.foregroundRole(), QColor(211, 47, 47))
        self.connection_status_label.setPalette(connection_palette)
        status_layout.addWidget(self.connection_status_label)
        
        # 分隔符
        separator1 = QLabel("|")
        separator1.setFont(QFont("Microsoft YaHei UI", 14))  # 普通字体14px
        separator1_palette = separator1.palette()
        separator1_palette.setColor(separator1.foregroundRole(), QColor(189, 189, 189))
        separator1.setPalette(separator1_palette)
        status_layout.addWidget(separator1)
        
        # 最后更新时间
        self.last_update_label = QLabel("最后更新: --")
        self.last_update_label.setFont(QFont("Microsoft YaHei UI", 12))  # 其他字体12px
        update_palette = self.last_update_label.palette()
        update_palette.setColor(self.last_update_label.foregroundRole(), QColor(117, 117, 117))
        self.last_update_label.setPalette(update_palette)
        status_layout.addWidget(self.last_update_label)
        
        # 弹性空间
        status_layout.addStretch()
        
        # 分隔符
        separator2 = QLabel("|")
        separator2.setFont(QFont("Microsoft YaHei UI", 14))  # 普通字体14px
        separator2_palette = separator2.palette()
        separator2_palette.setColor(separator2.foregroundRole(), QColor(189, 189, 189))
        separator2.setPalette(separator2_palette)
        status_layout.addWidget(separator2)
        
        # 版本信息
        version_label = QLabel("版本: v1.0.0")
        version_label.setFont(QFont("Microsoft YaHei UI", 14))  # 普通字体14px
        version_palette = version_label.palette()
        version_palette.setColor(version_label.foregroundRole(), QColor(117, 117, 117))
        version_label.setPalette(version_palette)
        status_layout.addWidget(version_label)
        
        parent_layout.addWidget(status_frame)
        self.logger.debug("底部状态栏创建完成")
    
    def _connect_signals(self):
        """
        连接信号和槽
        """
        self.logger.debug("连接信号和槽")
        # 连接实例表格选择事件
        self.instance_table.itemSelectionChanged.connect(self._on_instance_selected)
        # 信号连接已在组件创建时完成
    
    def _on_status_updated(self, status_data):
        """
        处理状态更新
        @author: Mr.Rey Copyright © 2025
        """
        try:
            self.logger.debug("开始更新OCR实例池状态显示")
            
            # 检查数据格式，兼容新的API响应格式
            if status_data and status_data.get('status') == 'success':
                data = status_data.get('data', {})
                pool_status = data.get('pool_status', {})
                instances = data.get('instances', [])
            else:
                # 兼容旧格式或直接数据格式
                pool_status = status_data.get('pool_status', {})
                instances = status_data.get('instances', [])
            
            # 更新概览信息
            self.total_instances_label.setText(f"总实例数: {pool_status.get('total_instances', len(instances))}")
            self.running_instances_label.setText(f"运行实例: {pool_status.get('active_instances', 0)}")
            self.idle_instances_label.setText(f"空闲实例: {pool_status.get('total_instances', len(instances)) - pool_status.get('active_instances', 0)}")
            self.cpu_usage_label.setText(f"CPU使用率: {pool_status.get('avg_cpu_usage', 0)}%")
            self.memory_usage_label.setText(f"内存使用: {pool_status.get('avg_memory_usage', 0)}MB")
            
            # 更新实例列表 - 优化UI更新逻辑
            # 暂时禁用表格更新信号，避免频繁刷新
            self.instance_table.blockSignals(True)
            self.instance_table.setRowCount(len(instances))
            
            for row, instance in enumerate(instances):
                # 批量创建表格项，减少单独设置的开销
                items = [
                    QTableWidgetItem(instance.get('id', instance.get('instance_id', ''))),
                    QTableWidgetItem(instance.get('status', '')),
                    QTableWidgetItem(f"{instance.get('cpu_usage', 0)}%"),
                    QTableWidgetItem(f"{instance.get('memory_usage', 0)}MB"),
                    QTableWidgetItem(str(instance.get('processed_count', instance.get('processed_requests', 0)))),
                    QTableWidgetItem(str(instance.get('error_count', 0))),
                    QTableWidgetItem(instance.get('last_activity', ''))
                ]
                
                # 设置状态列颜色
                status = instance.get('status', '').lower()
                if status in ['运行中', 'running', 'ready']:
                    items[1].setBackground(QColor(144, 238, 144))  # 浅绿色
                elif status in ['忙碌', 'busy']:
                    items[1].setBackground(QColor(255, 255, 0))   # 黄色
                elif status in ['空闲', 'idle']:
                    items[1].setBackground(QColor(173, 216, 230)) # 浅蓝色
                elif status == 'error':
                    items[1].setBackground(QColor(255, 182, 193)) # 浅红色
                
                # 批量设置表格项
                for col, item in enumerate(items):
                    self.instance_table.setItem(row, col, item)
            
            # 重新启用表格更新信号
            self.instance_table.blockSignals(False)
            
            # 更新最后更新时间
            current_time = datetime.now().strftime('%H:%M:%S')
            self.last_update_label.setText(f"最后更新：{current_time}")
            
            # 更新连接状态
            active_instances = pool_status.get('active_instances', 0)
            if active_instances > 0:
                self.connection_status_label.setText(f"连接状态: 已连接 ({active_instances}个实例)")
                self.connection_status_label.setStyleSheet("color: #00aa00;")  # 绿色
            else:
                self.connection_status_label.setText("连接状态: 无活跃实例")
                self.connection_status_label.setStyleSheet("color: #cc0000;")  # 红色
            
            self.logger.debug("OCR实例池状态显示更新完成")
            
        except Exception as e:
            self.logger.error(f"更新状态显示失败: {e}")
            # 记录详细错误信息到统一日志
            import traceback
            self.logger.error(f"状态更新异常详情: {traceback.format_exc()}")
    
    def _on_instance_selected(self):
        """
        实例选择事件
        """
        selected_items = self.instance_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            instance_id = self.instance_table.item(row, 0).text()
            self.selected_instance_id = instance_id
            
            self.logger.info(f"用户选择实例: {instance_id}")
            
            # 更新详情显示
            self._update_instance_detail(instance_id)
    
    def _update_instance_detail(self, instance_id):
        """
        更新实例详情显示
        """
        try:
            # 获取实例详细信息
            detail_info = self._get_instance_detail(instance_id)
            self.instance_info_display.setPlainText(detail_info)
            
        except Exception as e:
            self.logger.error(f"获取实例详情失败: {e}")
            self.instance_info_display.setPlainText(f"获取实例详情失败: {e}")
        
        try:
            # 获取实例日志
            log_content = self._get_instance_logs(instance_id)
            self.instance_log_display.setPlainText(log_content)
            
        except Exception as e:
            self.logger.error(f"获取实例日志失败: {e}")
            self.instance_log_display.setPlainText(f"获取实例日志失败: {e}")
    
    def _get_instance_detail(self, instance_id):
        """
        获取实例详细信息
        """
        if not requests:
            raise ImportError("requests库未安装，无法调用API")
        
        try:
            response = requests.get(f'{self.ocr_pool_api_base}/instances/{instance_id}', timeout=5)
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    data = result.get('data', {})
                    
                    # 计算运行时长
                    created_at = data.get('created_at', '')
                    uptime = '--'
                    if created_at:
                        try:
                            from datetime import datetime
                            start_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            now = datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.now()
                            uptime_seconds = (now - start_time).total_seconds()
                            hours = int(uptime_seconds // 3600)
                            minutes = int((uptime_seconds % 3600) // 60)
                            uptime = f"{hours}小时{minutes}分钟"
                        except:
                            uptime = '--'
                    
                    # 计算平均处理时间
                    response_times = data.get('response_times', [])
                    avg_time = '--'
                    if response_times:
                        avg_time = f"{sum(response_times) / len(response_times):.2f}"
                    
                    # 计算成功率
                    processed_requests = data.get('processed_requests', 0)
                    error_count = data.get('error_count', 0)
                    success_rate = '--'
                    if processed_requests > 0:
                        success_rate = f"{((processed_requests - error_count) / processed_requests * 100):.1f}"
                    
                    # 获取配置信息
                    config = data.get('config', {})
                    languages = config.get('languages', ['ch_sim', 'en'])
                    language_display = '中文+英文' if 'ch_sim' in languages and 'en' in languages else '+'.join(languages)
                    
                    return f"""
实例ID: {data.get('instance_id', instance_id)}
启动时间: {created_at.split('T')[0] + ' ' + created_at.split('T')[1][:8] if created_at else '--'}
运行时长: {uptime}
配置信息:
  - 模型: {config.get('model', 'EasyOCR')}
  - 语言: {language_display}
  - GPU: {'启用' if config.get('gpu_enabled', False) else '禁用'}
  - 最大并发: {config.get('max_concurrent', 1)}

性能统计:
  - 平均处理时间: {avg_time}ms
  - 成功率: {success_rate}%
  - 内存使用: {data.get('memory_usage', 0):.1f}MB
                    """
            else:
                raise Exception(f"API返回错误状态码: {response.status_code}")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"无法连接到OCR池服务: {e}")
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"连接OCR池服务超时: {e}")
        except Exception as e:
            raise Exception(f"获取实例详情失败: {e}")
    
    def _get_instance_logs(self, instance_id):
        """
        获取实例日志
        """
        if not requests:
            raise ImportError("requests库未安装，无法调用API")
        
        try:
            response = requests.get(f'{self.ocr_pool_api_base}/instances/{instance_id}/logs', timeout=5)
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    # API返回的data直接是日志列表，需要转换为字符串
                    logs_data = result.get('data', [])
                    if isinstance(logs_data, list):
                        return '\n'.join(logs_data)
                    else:
                        return str(logs_data)
            else:
                raise Exception(f"API返回错误状态码: {response.status_code}")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"无法连接到OCR池服务: {e}")
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"连接OCR池服务超时: {e}")
        except Exception as e:
            raise Exception(f"获取实例日志失败: {e}")
    
    # 事件处理方法
    def _on_refresh_clicked(self):
        """
        刷新按钮点击事件
        """
        self.logger.info("用户点击刷新按钮")
        # 手动触发状态刷新
        try:
            self.status_thread.refresh_status()
            # 更新状态栏信息
            self.status_label.setText("刷新完成 - 数据已更新")
            QMessageBox.information(self, "刷新", "数据刷新完成")
        except Exception as e:
            self.logger.error(f"手动刷新失败: {e}")
            self.status_label.setText(f"刷新失败 - {str(e)}")
            QMessageBox.warning(self, "刷新失败", f"数据刷新失败: {str(e)}")
    
    def _on_settings_clicked(self):
        """
        设置按钮点击事件
        """
        self.logger.info("用户点击设置按钮")
        # 显示设置对话框或菜单
        QMessageBox.information(self, "设置", "设置功能正在开发中...")
        self.status_label.setText("设置 - 功能开发中")
    
    def _on_start_instance_clicked(self):
        """
        启动实例按钮点击事件
        """
        self.logger.info("用户点击启动实例按钮")
        if self.selected_instance_id:
            success = self._call_instance_action('start', self.selected_instance_id)
            if success:
                self.logger.info(f"启动实例: {self.selected_instance_id}")
                QMessageBox.information(self, "启动实例", f"实例 {self.selected_instance_id} 启动成功")
            else:
                QMessageBox.warning(self, "错误", f"启动实例 {self.selected_instance_id} 失败")
        else:
            QMessageBox.warning(self, "警告", "请先选择一个实例")
    
    def _on_stop_instance_clicked(self):
        """
        停止实例按钮点击事件
        """
        self.logger.info("用户点击停止实例按钮")
        if self.selected_instance_id:
            success = self._call_instance_action('stop', self.selected_instance_id)
            if success:
                self.logger.info(f"停止实例: {self.selected_instance_id}")
                QMessageBox.information(self, "停止实例", f"实例 {self.selected_instance_id} 停止成功")
            else:
                QMessageBox.warning(self, "错误", f"停止实例 {self.selected_instance_id} 失败")
        else:
            QMessageBox.warning(self, "警告", "请先选择一个实例")
    
    def _on_restart_instance_clicked(self):
        """
        重启实例按钮点击事件
        """
        self.logger.info("用户点击重启实例按钮")
        if self.selected_instance_id:
            success = self._call_instance_action('restart', self.selected_instance_id)
            if success:
                self.logger.info(f"重启实例: {self.selected_instance_id}")
                QMessageBox.information(self, "重启实例", f"实例 {self.selected_instance_id} 重启成功")
            else:
                QMessageBox.warning(self, "错误", f"重启实例 {self.selected_instance_id} 失败")
        else:
            QMessageBox.warning(self, "警告", "请先选择一个实例")
    
    def _on_add_instance_clicked(self):
        """
        添加实例按钮点击事件
        """
        self.logger.info("用户点击添加实例按钮")
        success = self._call_instance_action('add')
        if success:
            QMessageBox.information(self, "添加实例", "新实例添加成功")
        else:
            QMessageBox.warning(self, "错误", "添加实例失败")
    
    def _on_remove_instance_clicked(self):
        """
        移除实例按钮点击事件
        """
        self.logger.info("用户点击移除实例按钮")
        if self.selected_instance_id:
            reply = QMessageBox.question(self, "确认移除", 
                                       f"确定要移除实例 {self.selected_instance_id} 吗？",
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)
            if reply == QMessageBox.Yes:
                success = self._call_instance_action('remove', self.selected_instance_id)
                if success:
                    self.logger.info(f"移除实例: {self.selected_instance_id}")
                    QMessageBox.information(self, "移除实例", f"实例 {self.selected_instance_id} 移除成功")
                else:
                    QMessageBox.warning(self, "错误", f"移除实例 {self.selected_instance_id} 失败")
        else:
            QMessageBox.warning(self, "警告", "请先选择一个实例")
    
    def _call_instance_action(self, action, instance_id=None):
        """
        调用实例操作API
        """
        if not requests:
            self.logger.warning("requests库未安装，无法调用API")
            return False
        
        try:
            if action == 'start' and instance_id:
                url = f'{self.ocr_pool_api_base}/instances/{instance_id}/start'
                response = requests.post(url, timeout=10)
            elif action == 'stop' and instance_id:
                url = f'{self.ocr_pool_api_base}/instances/{instance_id}/stop'
                response = requests.post(url, timeout=10)
            elif action == 'restart' and instance_id:
                url = f'{self.ocr_pool_api_base}/instances/{instance_id}/restart'
                response = requests.post(url, timeout=10)
            elif action == 'remove' and instance_id:
                url = f'{self.ocr_pool_api_base}/instances/{instance_id}'
                response = requests.delete(url, timeout=10)
            elif action == 'add':
                url = f'{self.ocr_pool_api_base}/instances'
                response = requests.post(url, timeout=10)
            else:
                return False
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    self.logger.info(f"实例操作成功: {action}, 实例ID: {instance_id}")
                    return True
                else:
                    self.logger.error(f"实例操作失败: {result.get('error', '未知错误')}")
                    return False
            else:
                self.logger.error(f"API调用失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"调用实例操作API失败: {e}")
            return False
    
    def closeEvent(self, event):
        """
        窗口关闭事件
        """
        self.logger.info("OCR实例池管理器窗口正在关闭")
        
        # 由于已改为手动刷新模式，状态监控线程不再持续运行
        # 无需停止线程
        if self.status_thread:
            self.status_thread.running = False
        
        self.logger.info("OCR实例池管理器窗口已关闭")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 创建并显示OCR实例池窗口
    window = OCRPoolWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec())