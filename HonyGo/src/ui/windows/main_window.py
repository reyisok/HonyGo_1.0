#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HonyGo 主界面窗口


@author: Mr.Rey Copyright © 2025
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# 添加项目路径到sys.path
project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
if project_root_env:
    project_root = Path(project_root_env)
else:
    # 备用方案：从当前文件路径计算
    project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox,
    QRadioButton, QButtonGroup, QTextEdit, QComboBox,
    QFrame, QSizePolicy, QApplication, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QPixmap, QFont, QIcon, QColor
from PySide6.QtSvgWidgets import QSvgWidget

# 导入requests库（可选）
try:
    import requests
    import urllib3.exceptions
except ImportError:
    requests = None
    urllib3 = None

# 导入统一日志服务
from src.ui.services.logging_service import get_logger, set_ui_log_callback
from src.ui.services.cross_process_log_bridge import get_log_bridge_server
# 导入模拟任务服务
from src.ui.services.simulation_task_service import SimulationTaskService


class LogDisplayThread(QThread):
    """
    日志显示线程，用于处理日志更新
    """
    log_received = Signal(str, str)  # level, message
    
    def __init__(self):
        super().__init__()
        self.running = True
        
    def run(self):
        """
        线程运行方法
        """
        # 修复：不使用exec()避免阻塞，改为简单的事件循环
        while self.running:
            self.msleep(100)  # 100ms间隔检查
        
    def stop(self):
        """安全停止线程"""
        self.running = False
        # 等待线程自然结束，避免强制退出
        if self.isRunning():
            self.wait(3000)  # 最多等待3秒
        if self.isRunning():
            self.terminate()  # 强制终止
            self.wait(1000)   # 等待终止完成


class MainWindow(QMainWindow):
    """
    HonyGo 主界面窗口
    """
    
    def __init__(self):
        super().__init__()
        
        # 初始化日志记录器
        self.logger = get_logger("MainWindow", "Application")
        self.logger.info("=== 开始初始化主界面窗口 ===")
        
        # 记录初始化开始时间
        init_start_time = datetime.now()
        self.logger.info(f"初始化开始时间: {init_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        
        # 记录系统环境信息
        self._log_system_environment()
        
        # 界面组件初始化
        self.logger.info("开始初始化界面组件变量")
        self.central_widget = None
        self.log_display = None
        self.log_level_combo = None
        self.log_filter_input = None
        self.auto_scroll_button = None
        self.auto_scroll_enabled = True
        
        # 日志筛选相关
        self.all_log_entries = []  # 存储所有日志条目 (level, message, timestamp, formatted_message)
        self.pending_log_entries = []  # 停止滚动期间缓存的日志条目
        
        # OCR服务控制按钮
        self.start_ocr_service_button = None
        self.stop_ocr_service_button = None
        self.logger.debug("界面组件变量初始化完成")
        
        # 配置参数初始化
        self.logger.info("开始初始化配置参数")
        self.config = {
            'keyword': 'test',
            'click_interval': 1000,
            'mouse_button': 'left',
            'similarity_threshold': 0.15,  # 图片参照匹配阈值
            'monitor_frequency': 1.0,
            'monitor_area': {'x': 0, 'y': 0, 'width': 1536, 'height': 960}
        }
        self.logger.debug(f"默认配置参数: {self.config}")
        
        # 算法类型相关属性初始化
        self.algorithm_type_group = None
        self.ocr_pool_radio = None
        self.image_ref_radio = None
        self.keyword_input = None
        self.keyword_label = None
        self.image_path_input = None
        self.select_image_button = None
        self.selected_image_path = ""
        
        # 系统状态初始化
        self.logger.info("开始初始化系统状态")
        self.system_status = "就绪"
        self.running_status = "已停止"
        self.logger.debug(f"初始系统状态: {self.system_status}, 运行状态: {self.running_status}")
        
        # 日志显示线程初始化（延迟到UI初始化后）
        self.logger.info("准备初始化日志显示线程")
        self.log_thread = None
        self.logger.debug("日志显示线程变量初始化完成")
        
        # 初始化跨进程日志桥接服务
        self.logger.info("开始初始化跨进程日志桥接服务")
        self.log_bridge = None
        self.logger.debug("跨进程日志桥接服务变量初始化完成")
        
        # 初始化模拟任务服务
        self.logger.info("开始初始化模拟任务服务")
        self.simulation_task_service = SimulationTaskService()
        self.logger.debug("模拟任务服务初始化完成")
        
        # 注意：已移除OCR日志轮询定时器，改用跨线程日志传递机制
        self.logger.debug("OCR日志将通过统一日志服务直接传递到主界面")
        
        # 初始化界面
        ui_start_time = datetime.now()
        self.logger.info(f"开始初始化用户界面组件 - 开始时间: {ui_start_time.strftime('%H:%M:%S.%f')[:-3]}")
        self._init_ui()
        ui_end_time = datetime.now()
        ui_duration = (ui_end_time - ui_start_time).total_seconds() * 1000
        self.logger.info(f"用户界面组件初始化完成 - 耗时: {ui_duration:.2f}ms")
        
        # 设置日志系统
        log_start_time = datetime.now()
        self.logger.info(f"开始设置日志系统 - 开始时间: {log_start_time.strftime('%H:%M:%S.%f')[:-3]}")
        self._setup_logging()
        log_end_time = datetime.now()
        log_duration = (log_end_time - log_start_time).total_seconds() * 1000
        self.logger.info(f"日志系统设置完成 - 耗时: {log_duration:.2f}ms")
        
        # 连接信号和槽
        signal_start_time = datetime.now()
        self.logger.info(f"开始连接信号和槽 - 开始时间: {signal_start_time.strftime('%H:%M:%S.%f')[:-3]}")
        self._connect_signals()
        signal_end_time = datetime.now()
        signal_duration = (signal_end_time - signal_start_time).total_seconds() * 1000
        self.logger.info(f"信号和槽连接完成 - 耗时: {signal_duration:.2f}ms")
        
        # 记录总初始化时间
        init_end_time = datetime.now()
        total_duration = (init_end_time - init_start_time).total_seconds() * 1000
        self.logger.info(f"=== 主界面窗口初始化完成 - 总耗时: {total_duration:.2f}ms ===")
    
    def _log_system_environment(self):
        """
        记录系统环境信息
        """
        try:
            import platform
            import psutil
            
            self.logger.info("=== 系统环境信息 ===")
            self.logger.info(f"操作系统: {platform.system()} {platform.release()}")
            self.logger.info(f"Python版本: {platform.python_version()}")
            self.logger.info(f"架构: {platform.architecture()[0]}")
            self.logger.info(f"处理器: {platform.processor()}")
            self.logger.info(f"CPU核心数: {psutil.cpu_count(logical=False)} 物理核心, {psutil.cpu_count(logical=True)} 逻辑核心")
            
            # 内存信息
            memory = psutil.virtual_memory()
            self.logger.info(f"总内存: {memory.total / (1024**3):.2f}GB, 可用内存: {memory.available / (1024**3):.2f}GB")
            
            # 屏幕信息
            screen = QApplication.primaryScreen().geometry()
            self.logger.info(f"主屏幕分辨率: {screen.width()}x{screen.height()}")
            
            # 项目路径信息
            self.logger.info(f"项目根目录: {project_root}")
            self.logger.info(f"当前工作目录: {os.getcwd()}")
            
            # PySide6版本信息
            from PySide6 import __version__ as pyside_version
            self.logger.info(f"PySide6版本: {pyside_version}")
            
            self.logger.info("=== 系统环境信息记录完成 ===")
            
        except Exception as e:
            self.logger.error(f"记录系统环境信息失败: {e}")
    
    def _update_log_display(self):
        """
        线程安全的日志显示更新方法
        """
        pass  # 实际更新逻辑已在_on_log_received中处理
    
    def _init_ui(self):
        """
        初始化用户界面
        """
        self.logger.info("开始初始化用户界面组件")
        
        # 获取屏幕尺寸并设置窗口为屏幕宽度的50%
        screen = QApplication.primaryScreen().geometry()
        window_width = int(screen.width() * 0.5)
        window_height = 800
        
        # 设置窗口属性
        self.setWindowTitle("HonyGo - 自动化操作工具 实验型")
        self.setMinimumSize(800, 650)
        self.resize(window_width, window_height)
        
        # 使用PySide6原生样式，设置主窗口背景色
        palette = self.palette()
        palette.setColor(palette.ColorRole.Window, QColor(233, 233, 233))  # #e9e9e9
        self.setPalette(palette)
        
        # 设置窗口图标
        icon_path = Path(__file__).parent.parent / "resources" / "icons" / "HonyGo.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
            self.logger.info(f"设置窗口图标: {icon_path}")
        else:
            self.logger.warning(f"窗口图标文件不存在: {icon_path}")
        
        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setSpacing(2)  # 统一间隙为2px
        main_layout.setContentsMargins(2, 2, 2, 2)  # 最大间隔2px，为日志区域留出更多空间
        
        # 创建各个区域
        self._create_title_bar(main_layout)
        self._create_system_config_area(main_layout)
        self._create_monitor_area_config(main_layout)
        self._create_system_control_area(main_layout)
        
        # 创建日志区域并设置拉伸因子以最大化高度
        log_frame = self._create_log_area(main_layout)
        main_layout.setStretchFactor(log_frame, 1)  # 给日志区域最大拉伸权重
        
        self._create_status_bar(main_layout)
        
        # 触发算法类型变更处理，确保默认选择图片参照时显示正确的控件状态
        self._on_algorithm_type_changed(self.image_ref_radio)
        
        self.logger.info("用户界面组件初始化完成")
    
    def _create_title_bar(self, parent_layout):
        """
        创建标题栏区域
        """
        start_time = datetime.now()
        self.logger.info(f"开始创建标题栏区域 - 开始时间: {start_time.strftime('%H:%M:%S.%f')[:-3]}")
        
        # 创建标题栏框架
        frame_start = datetime.now()
        title_frame = QFrame()
        
        # 使用原生样式设置边框
        title_frame.setFrameStyle(QFrame.NoFrame)
        
        # 使用QPalette设置背景色
        palette = title_frame.palette()
        palette.setColor(title_frame.backgroundRole(), QColor(57, 156, 248))  # #399cf8
        title_frame.setPalette(palette)
        title_frame.setAutoFillBackground(True)
        
        # 设置内边距
        title_frame.setContentsMargins(15, 15, 15, 15)
        title_layout = QHBoxLayout(title_frame)
        frame_end = datetime.now()
        self.logger.debug(f"标题栏框架创建完成 - 耗时: {(frame_end - frame_start).total_seconds() * 1000:.2f}ms")
        
        # 程序SVG图标
        icon_start = datetime.now()
        svg_icon = QSvgWidget()
        # 使用环境变量获取项目根路径
        project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
        if project_root_env:
            project_root = Path(project_root_env)
        else:
            # 备用方案：从当前文件路径计算
            project_root = Path(__file__).parent.parent.parent.parent
        svg_path = project_root / "src" / "ui" / "resources" / "images" / "HonyGo.svg"
        if svg_path.exists():
            svg_icon.load(str(svg_path))
            # 设置图标大小为190%，基于32px计算约为61px，统一设为67px
            svg_icon.setFixedSize(67, 67)
            self.logger.debug(f"成功加载SVG图标: {svg_path}")
        else:
            # 如果SVG文件不存在，创建一个占位符
            svg_icon.setFixedSize(67, 67)  # 调整为190%大小 (35 * 1.9 = 66.5 ≈ 67)
            self.logger.warning(f"SVG图标文件不存在: {svg_path}")
        # SVG图标使用透明背景属性
        svg_icon.setAttribute(Qt.WA_TranslucentBackground)
        title_layout.addWidget(svg_icon)
        icon_end = datetime.now()
        self.logger.debug(f"SVG图标创建完成 - 耗时: {(icon_end - icon_start).total_seconds() * 1000:.2f}ms")
        
        # 工具名称
        name_start = datetime.now()
        name_label = QLabel("HonyGo")
        name_font = QFont("Segoe UI", 24, QFont.Bold)
        name_label.setFont(name_font)
        # 使用QPalette设置文字颜色
        palette = name_label.palette()
        palette.setColor(name_label.foregroundRole(), QColor(255, 255, 255))  # #ffffff
        name_label.setPalette(palette)
        title_layout.addWidget(name_label)
        name_end = datetime.now()
        self.logger.debug(f"工具名称标签创建完成 - 耗时: {(name_end - name_start).total_seconds() * 1000:.2f}ms")
        
        # 工具描述
        desc_start = datetime.now()
        desc_label = QLabel("自动化操作工具 实验型")
        desc_font = QFont("Segoe UI", 10)
        desc_label.setFont(desc_font)
        # 使用QPalette设置文字颜色
        palette = desc_label.palette()
        palette.setColor(desc_label.foregroundRole(), QColor(255, 255, 255))  # #ffffff
        desc_label.setPalette(palette)
        title_layout.addWidget(desc_label)
        desc_end = datetime.now()
        self.logger.debug(f"工具描述标签创建完成 - 耗时: {(desc_end - desc_start).total_seconds() * 1000:.2f}ms")
        
        # 版权信息
        copyright_start = datetime.now()
        copyright_label = QLabel("Copyright © 2025 Mr.Rey")
        copyright_font = QFont("Segoe UI", 8)
        copyright_label.setFont(copyright_font)
        # 使用PySide6原生样式设置版权标签颜色
        copyright_palette = copyright_label.palette()
        copyright_palette.setColor(copyright_palette.ColorRole.WindowText, QColor(255, 255, 255))
        copyright_label.setPalette(copyright_palette)
        title_layout.addWidget(copyright_label)
        copyright_end = datetime.now()
        self.logger.debug(f"版权信息标签创建完成 - 耗时: {(copyright_end - copyright_start).total_seconds() * 1000:.2f}ms")
        
        # 弹性空间
        title_layout.addStretch()
        
        # 最小化按钮
        minimize_start = datetime.now()
        minimize_button = QPushButton("最小化")
        minimize_button.setMaximumSize(150, 30)
        minimize_button.setFixedHeight(30)
        # 使用PySide6原生样式设置最小化按钮
        minimize_palette = minimize_button.palette()
        minimize_palette.setColor(minimize_palette.ColorRole.Button, QColor(255, 255, 255, 51))  # rgba(255,255,255,0.2)
        minimize_palette.setColor(minimize_palette.ColorRole.ButtonText, QColor(255, 255, 255))
        minimize_button.setPalette(minimize_palette)
        minimize_font = QFont("Microsoft YaHei", 10, QFont.Weight.Medium)
        minimize_button.setFont(minimize_font)
        minimize_button.clicked.connect(self.showMinimized)
        title_layout.addWidget(minimize_button)
        minimize_end = datetime.now()
        self.logger.debug(f"最小化按钮创建完成 - 耗时: {(minimize_end - minimize_start).total_seconds() * 1000:.2f}ms")
        
        # 退出按钮
        exit_start = datetime.now()
        exit_button = QPushButton("退出")
        exit_button.setMaximumSize(150, 30)
        exit_button.setFixedHeight(30)
        # 使用PySide6原生样式设置退出按钮
        exit_palette = exit_button.palette()
        exit_palette.setColor(exit_palette.ColorRole.Button, QColor(244, 67, 54))  # #f44336
        exit_palette.setColor(exit_palette.ColorRole.ButtonText, QColor(0, 0, 0))
        exit_button.setPalette(exit_palette)
        exit_font = QFont("Microsoft YaHei", 10, QFont.Weight.Medium)
        exit_button.setFont(exit_font)
        exit_button.clicked.connect(self._on_exit_clicked)
        title_layout.addWidget(exit_button)
        exit_end = datetime.now()
        self.logger.debug(f"退出按钮创建完成 - 耗时: {(exit_end - exit_start).total_seconds() * 1000:.2f}ms")
        
        parent_layout.addWidget(title_frame)
        
        # 记录总耗时
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds() * 1000
        self.logger.info(f"标题栏区域创建完成 - 总耗时: {total_duration:.2f}ms")
    
    def _create_system_config_area(self, parent_layout):
        """
        创建系统配置区域 - 重新设计布局：统一间距10px，每行两个控件，控件标题最大160px
        """
        start_time = datetime.now()
        self.logger.info(f"开始创建系统配置区域 - 开始时间: {start_time.strftime('%H:%M:%S.%f')[:-3]}")
        
        # 创建配置框架
        frame_start = datetime.now()
        config_frame = QFrame()
        config_frame.setFrameStyle(QFrame.Box)
        # 使用PySide6原生样式设置配置框架
        config_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        config_frame.setLineWidth(1)
        config_palette = config_frame.palette()
        config_palette.setColor(config_palette.ColorRole.WindowText, QColor(0, 0, 0))  # 黑色
        config_frame.setPalette(config_palette)
        config_layout = QGridLayout(config_frame)
        config_layout.setHorizontalSpacing(10)  # 统一左右间距10px
        config_layout.setVerticalSpacing(10)    # 统一上下间距10px
        config_layout.setContentsMargins(10, 10, 10, 10)  # 统一边距10px
        frame_end = datetime.now()
        self.logger.debug(f"配置框架创建完成 - 耗时: {(frame_end - frame_start).total_seconds() * 1000:.2f}ms")
        
        # 第一行：设定关键字 + 点击间隔
        # 设定关键字
        self.keyword_label = QLabel("设定关键字:")
        self.keyword_label.setFixedWidth(160)  # 控件标题固定160px
        self.keyword_label.setWordWrap(True)
        self.keyword_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # 左对齐
        config_layout.addWidget(self.keyword_label, 0, 0)
        
        self.keyword_input = QLineEdit(self.config['keyword'])
        self.keyword_input.textChanged.connect(self._on_keyword_changed)
        # 默认设置为只读，因为图片参照是默认选择的算法类型
        self.keyword_input.setReadOnly(True)
        # 创建左对齐布局容器
        keyword_layout = QHBoxLayout()
        keyword_layout.setContentsMargins(0, 0, 0, 0)
        keyword_layout.addWidget(self.keyword_input)
        keyword_layout.addStretch()  # 添加弹性空间使控件靠左
        keyword_widget = QWidget()
        keyword_widget.setLayout(keyword_layout)
        config_layout.addWidget(keyword_widget, 0, 1)
        
        # 点击间隔
        interval_label = QLabel("点击间隔 (毫秒):")
        interval_label.setFixedWidth(160)  # 控件标题固定160px
        interval_label.setWordWrap(True)
        interval_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)  # 右对齐
        config_layout.addWidget(interval_label, 0, 2)
        
        self.interval_input = QSpinBox()
        self.interval_input.setRange(100, 10000)
        self.interval_input.setValue(self.config['click_interval'])
        self.interval_input.valueChanged.connect(self._on_interval_changed)
        config_layout.addWidget(self.interval_input, 0, 3)
        
        # 第二行：鼠标按键 + 监控频率
        # 鼠标按键
        mouse_button_label = QLabel("鼠标按键:")
        mouse_button_label.setFixedWidth(160)  # 控件标题固定160px
        mouse_button_label.setWordWrap(True)
        mouse_button_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # 左对齐
        config_layout.addWidget(mouse_button_label, 1, 0)
        
        self.mouse_button_group = QButtonGroup()
        self.left_button = QRadioButton("左键")
        self.right_button = QRadioButton("右键")
        self.left_button.setChecked(self.config['mouse_button'] == 'left')
        self.right_button.setChecked(self.config['mouse_button'] == 'right')
        self.mouse_button_group.addButton(self.left_button, 0)
        self.mouse_button_group.addButton(self.right_button, 1)
        self.mouse_button_group.buttonClicked.connect(self._on_mouse_button_changed)
        
        mouse_layout = QHBoxLayout()
        mouse_layout.setSpacing(10)
        mouse_layout.setContentsMargins(0, 0, 0, 0)
        mouse_layout.addWidget(self.left_button)
        mouse_layout.addWidget(self.right_button)
        mouse_layout.addStretch()  # 添加弹性空间使控件靠左
        mouse_widget = QWidget()
        mouse_widget.setLayout(mouse_layout)
        config_layout.addWidget(mouse_widget, 1, 1)
        
        # 监控频率
        frequency_label = QLabel("监控频率 (秒):")
        frequency_label.setFixedWidth(160)  # 控件标题固定160px
        frequency_label.setWordWrap(True)
        frequency_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)  # 右对齐
        config_layout.addWidget(frequency_label, 1, 2)
        
        self.frequency_input = QDoubleSpinBox()
        self.frequency_input.setRange(0.1, 60.0)  # 支持0.1秒到60秒的监控频率
        self.frequency_input.setSingleStep(0.1)
        self.frequency_input.setDecimals(1)  # 显示1位小数
        self.frequency_input.setValue(self.config['monitor_frequency'])
        self.frequency_input.valueChanged.connect(self._on_frequency_changed)
        # 添加工具提示
        self.frequency_input.setToolTip("监控频率范围: 0.1-60.0秒\n较低值响应更快但消耗更多资源\n较高值响应较慢但节省资源")
        config_layout.addWidget(self.frequency_input, 1, 3)
        
        # 第三行：OCR实例池服务 + 算法类型
        # OCR服务控制按钮
        ocr_service_label = QLabel("OCR实例池服务:")
        ocr_service_label.setFixedWidth(160)  # 控件标题固定160px
        ocr_service_label.setWordWrap(True)
        ocr_service_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # 左对齐
        config_layout.addWidget(ocr_service_label, 2, 0)
        
        # 创建按钮水平布局容器，实现靠左对齐
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        # 启动OCR实例池服务按钮 - 使用PySide6原生样式
        self.start_ocr_service_button = QPushButton("运行")
        self.start_ocr_service_button.setMaximumSize(80, 30)
        self.start_ocr_service_button.setFixedHeight(30)
        self.start_ocr_service_button.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.DemiBold))
        start_ocr_palette = self.start_ocr_service_button.palette()
        start_ocr_palette.setColor(self.start_ocr_service_button.foregroundRole(), QColor(0, 0, 0))
        start_ocr_palette.setColor(self.start_ocr_service_button.backgroundRole(), QColor(76, 175, 80))  # #4CAF50
        self.start_ocr_service_button.setPalette(start_ocr_palette)
        self.start_ocr_service_button.setAutoFillBackground(True)
        self.start_ocr_service_button.clicked.connect(self._on_start_ocr_service_clicked)
        buttons_layout.addWidget(self.start_ocr_service_button)
        
        # 停止OCR实例池服务按钮 - 使用PySide6原生样式
        self.stop_ocr_service_button = QPushButton("停止")
        self.stop_ocr_service_button.setMaximumSize(80, 30)
        self.stop_ocr_service_button.setFixedHeight(30)
        self.stop_ocr_service_button.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.DemiBold))
        stop_ocr_palette = self.stop_ocr_service_button.palette()
        stop_ocr_palette.setColor(self.stop_ocr_service_button.foregroundRole(), QColor(0, 0, 0))
        stop_ocr_palette.setColor(self.stop_ocr_service_button.backgroundRole(), QColor(244, 67, 54))  # #f44336
        self.stop_ocr_service_button.setPalette(stop_ocr_palette)
        self.stop_ocr_service_button.setAutoFillBackground(True)
        self.stop_ocr_service_button.clicked.connect(self._on_stop_ocr_service_clicked)
        buttons_layout.addWidget(self.stop_ocr_service_button)
        
        # 实例池管理按钮 - 使用PySide6原生样式
        self.ocr_pool_button = QPushButton("实例池管理")
        self.ocr_pool_button.setMaximumSize(120, 30)
        self.ocr_pool_button.setFixedHeight(30)
        self.ocr_pool_button.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.DemiBold))
        pool_palette = self.ocr_pool_button.palette()
        pool_palette.setColor(self.ocr_pool_button.foregroundRole(), QColor(0, 0, 0))
        pool_palette.setColor(self.ocr_pool_button.backgroundRole(), QColor(255, 182, 193))  # #ffb6c1
        self.ocr_pool_button.setPalette(pool_palette)
        self.ocr_pool_button.setAutoFillBackground(True)
        self.ocr_pool_button.clicked.connect(self._on_ocr_pool_clicked)
        buttons_layout.addWidget(self.ocr_pool_button)
        
        # 添加弹性空间，使按钮靠左对齐
        buttons_layout.addStretch()
        
        # 将按钮布局添加到网格布局中
        buttons_widget = QWidget()
        buttons_widget.setLayout(buttons_layout)
        config_layout.addWidget(buttons_widget, 2, 1)
        
        # 算法类型选择
        algorithm_type_label = QLabel("算法类型:")
        algorithm_type_label.setFixedWidth(160)  # 控件标题固定160px
        algorithm_type_label.setWordWrap(True)
        algorithm_type_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)  # 右对齐
        config_layout.addWidget(algorithm_type_label, 2, 2)
        
        # 算法类型单选按钮组
        self.algorithm_type_group = QButtonGroup()
        self.ocr_pool_radio = QRadioButton("OCR池")
        self.image_ref_radio = QRadioButton("图片参照")
        self.image_ref_radio.setChecked(True)  # 默认选择图片参照
        self.algorithm_type_group.addButton(self.ocr_pool_radio, 0)
        self.algorithm_type_group.addButton(self.image_ref_radio, 1)
        self.algorithm_type_group.buttonClicked.connect(self._on_algorithm_type_changed)
        
        algorithm_layout = QHBoxLayout()
        algorithm_layout.setSpacing(10)
        algorithm_layout.addWidget(self.ocr_pool_radio)
        algorithm_layout.addWidget(self.image_ref_radio)
        algorithm_widget = QWidget()
        algorithm_widget.setLayout(algorithm_layout)
        config_layout.addWidget(algorithm_widget, 2, 3)
        
        # 第四行：图片参照上传（默认显示，因为图片参照是默认选择）
        # 图片参照上传标题
        self.image_ref_label = QLabel("图片参照上传:")
        self.image_ref_label.setFixedWidth(160)  # 控件标题固定160px
        self.image_ref_label.setWordWrap(True)
        self.image_ref_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # 左对齐
        self.image_ref_label.setVisible(True)  # 默认显示，因为图片参照是默认选择
        config_layout.addWidget(self.image_ref_label, 3, 0)
        
        # 图片路径输入和选择按钮布局（默认显示）
        image_layout = QHBoxLayout()
        image_layout.setSpacing(10)
        image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_path_input = QLineEdit()
        self.image_path_input.setReadOnly(True)
        self.image_path_input.setPlaceholderText("请选择图片文件...")
        self.select_image_button = QPushButton("选择图片")
        self.select_image_button.setMaximumSize(100, 30)
        self.select_image_button.setFont(QFont("Microsoft YaHei UI", 10))
        self.select_image_button.clicked.connect(self._on_select_image_clicked)
        
        image_layout.addWidget(self.image_path_input)
        image_layout.addWidget(self.select_image_button)
        image_layout.addStretch()  # 添加弹性空间使控件靠左
        self.image_widget = QWidget()
        self.image_widget.setLayout(image_layout)
        self.image_widget.setVisible(True)  # 默认显示，因为图片参照是默认选择
        config_layout.addWidget(self.image_widget, 3, 1, 1, 2)  # 跨越2列
        
        # 匹配阈值配置（图片参照模式专用）
        self.threshold_label = QLabel("匹配阈值:")
        self.threshold_label.setFixedWidth(80)  # 控件标题固定80px
        self.threshold_label.setWordWrap(True)
        self.threshold_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)  # 右对齐
        self.threshold_label.setVisible(True)  # 默认显示，因为图片参照是默认选择
        config_layout.addWidget(self.threshold_label, 3, 2)
        
        # 阈值输入控件
        self.threshold_input = QDoubleSpinBox()
        self.threshold_input.setRange(0.01, 1.0)  # 阈值范围0.01-1.0
        self.threshold_input.setSingleStep(0.01)  # 步长0.01
        self.threshold_input.setDecimals(2)  # 保留2位小数
        self.threshold_input.setValue(0.15)  # 默认阈值0.15
        self.threshold_input.setMaximumWidth(80)  # 控件宽度80px
        self.threshold_input.valueChanged.connect(self._on_threshold_changed)
        self.threshold_input.setVisible(True)  # 默认显示，因为图片参照是默认选择
        config_layout.addWidget(self.threshold_input, 3, 3)
        
        parent_layout.addWidget(config_frame)
        
        # 记录总耗时
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds() * 1000
        self.logger.info(f"系统配置区域创建完成 - 总耗时: {total_duration:.2f}ms")
    
    def _create_monitor_area_config(self, parent_layout):
        """
        创建监控区域配置区域
        """
        start_time = datetime.now()
        self.logger.info(f"开始创建监控区域配置 - 开始时间: {start_time.strftime('%H:%M:%S.%f')[:-3]}")
        
        # 创建监控框架
        frame_start = datetime.now()
        monitor_frame = QFrame()
        monitor_frame.setFixedHeight(40)  # 设置监控区域配置高度为40px
        monitor_frame.setFrameStyle(QFrame.Box)
        # 使用PySide6原生样式设置监控框架
        monitor_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        monitor_frame.setLineWidth(1)
        monitor_palette = monitor_frame.palette()
        monitor_palette.setColor(monitor_palette.ColorRole.WindowText, QColor(0, 0, 0))  # 黑色
        monitor_frame.setPalette(monitor_palette)
        monitor_layout = QHBoxLayout(monitor_frame)
        monitor_layout.setSpacing(5)
        monitor_layout.setContentsMargins(10, 5, 10, 5)
        frame_end = datetime.now()
        self.logger.debug(f"监控框架创建完成 - 耗时: {(frame_end - frame_start).total_seconds() * 1000:.2f}ms")
        
        # 监控区域标签
        monitor_area_label = QLabel("监控区域:")
        monitor_area_label.setMaximumWidth(140)
        monitor_area_label.setWordWrap(True)
        monitor_area_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # 左对齐
        monitor_layout.addWidget(monitor_area_label)
        
        # 监控区域显示框 - 使用PySide6原生样式
        area = self.config['monitor_area']
        area_text = f"X: {area['x']}, Y: {area['y']}, 宽度: {area['width']}, 高度: {area['height']} (全屏)"
        self.area_display = QLabel(area_text)
        self.area_display.setFrameStyle(QFrame.Box)
        self.area_display.setLineWidth(1)
        self.area_display.setAutoFillBackground(True)
        area_palette = self.area_display.palette()
        area_palette.setColor(self.area_display.backgroundRole(), QColor(249, 249, 249))  # #f9f9f9
        area_palette.setColor(self.area_display.foregroundRole(), QColor(0, 0, 0))
        self.area_display.setPalette(area_palette)
        self.area_display.setContentsMargins(5, 5, 5, 5)
        monitor_layout.addWidget(self.area_display)
        
        # 选择监控区域按钮 - 使用PySide6原生样式
        select_area_button = QPushButton("选择监控区域")
        select_area_button.setMaximumSize(150, 30)
        select_area_button.setFixedHeight(30)
        select_area_button.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.DemiBold))
        select_palette = select_area_button.palette()
        select_palette.setColor(select_area_button.foregroundRole(), QColor(0, 0, 0))
        select_palette.setColor(select_area_button.backgroundRole(), QColor(33, 150, 243))  # #2196F3
        select_area_button.setPalette(select_palette)
        select_area_button.setAutoFillBackground(True)
        select_area_button.clicked.connect(self._on_select_area_clicked)
        monitor_layout.addWidget(select_area_button)
        
        parent_layout.addWidget(monitor_frame)
        
        # 记录总耗时
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds() * 1000
        self.logger.info(f"监控区域配置创建完成 - 总耗时: {total_duration:.2f}ms")
    
    def _create_system_control_area(self, parent_layout):
        """
        创建系统控制区域
        """
        start_time = datetime.now()
        self.logger.info(f"开始创建系统控制区域 - 开始时间: {start_time.strftime('%H:%M:%S.%f')[:-3]}")
        
        # 创建控制框架 - 使用PySide6原生样式
        frame_start = datetime.now()
        control_frame = QFrame()
        control_frame.setFixedHeight(65)  # 设置系统控制区域高度为65px
        control_frame.setFrameStyle(QFrame.Box)
        control_frame.setLineWidth(1)
        control_frame.setAutoFillBackground(True)
        control_palette = control_frame.palette()
        control_palette.setColor(control_frame.backgroundRole(), QColor(255, 255, 255))  # #ffffff
        control_frame.setPalette(control_palette)
        frame_end = datetime.now()
        self.logger.debug(f"控制框架创建完成 - 耗时: {(frame_end - frame_start).total_seconds() * 1000:.2f}ms")
        
        control_layout = QHBoxLayout(control_frame)
        control_layout.setSpacing(5)
        control_layout.setContentsMargins(10, 5, 10, 5)
        
        # 模拟任务标题 - 样式参照"鼠标按键"标题
        simulation_task_label = QLabel("模拟任务：")
        simulation_task_label.setFixedWidth(160)  # 控件标题固定160px
        simulation_task_label.setWordWrap(True)
        simulation_task_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # 左对齐
        # 设置字体颜色为黑色
        simulation_palette = simulation_task_label.palette()
        simulation_palette.setColor(simulation_task_label.foregroundRole(), QColor(0, 0, 0))  # 黑色
        simulation_task_label.setPalette(simulation_palette)
        control_layout.addWidget(simulation_task_label)
        
        # 启动按钮 - 使用PySide6原生样式
        self.start_button = QPushButton("启动")
        self.start_button.setMaximumSize(150, 30)
        self.start_button.setFixedHeight(30)
        self.start_button.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.DemiBold))
        start_palette = self.start_button.palette()
        start_palette.setColor(self.start_button.foregroundRole(), QColor(0, 0, 0))
        start_palette.setColor(self.start_button.backgroundRole(), QColor(76, 175, 80))  # #4CAF50
        self.start_button.setPalette(start_palette)
        self.start_button.setAutoFillBackground(True)
        self.start_button.clicked.connect(self._on_start_clicked)
        control_layout.addWidget(self.start_button)
        
        # 停止按钮 - 使用PySide6原生样式
        self.stop_button = QPushButton("停止")
        self.stop_button.setMaximumSize(150, 30)
        self.stop_button.setFixedHeight(30)
        self.stop_button.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.DemiBold))
        stop_palette = self.stop_button.palette()
        stop_palette.setColor(self.stop_button.foregroundRole(), QColor(0, 0, 0))
        stop_palette.setColor(self.stop_button.backgroundRole(), QColor(244, 67, 54))  # #f44336
        self.stop_button.setPalette(stop_palette)
        self.stop_button.setAutoFillBackground(True)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        control_layout.addWidget(self.stop_button)
        
        # 测试按钮 - 使用PySide6原生样式
        self.test_button = QPushButton("测试")
        self.test_button.setMaximumSize(150, 30)
        self.test_button.setFixedHeight(30)
        self.test_button.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.DemiBold))
        test_palette = self.test_button.palette()
        test_palette.setColor(self.test_button.foregroundRole(), QColor(0, 0, 0))
        test_palette.setColor(self.test_button.backgroundRole(), QColor(33, 150, 243))  # #2196F3
        self.test_button.setPalette(test_palette)
        self.test_button.setAutoFillBackground(True)
        self.test_button.clicked.connect(self._on_test_clicked)
        control_layout.addWidget(self.test_button)
        
        # 保存日志按钮 - 使用PySide6原生样式
        self.save_log_button = QPushButton("保存日志")
        self.save_log_button.setMaximumSize(150, 30)
        self.save_log_button.setFixedHeight(30)
        self.save_log_button.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.DemiBold))
        save_log_palette = self.save_log_button.palette()
        save_log_palette.setColor(self.save_log_button.foregroundRole(), QColor(0, 0, 0))
        save_log_palette.setColor(self.save_log_button.backgroundRole(), QColor(255, 152, 0))  # #FF9800
        self.save_log_button.setPalette(save_log_palette)
        self.save_log_button.setAutoFillBackground(True)
        self.save_log_button.clicked.connect(self._on_save_log_clicked)
        control_layout.addWidget(self.save_log_button)
        
        # 弹性空间
        control_layout.addStretch()
        
        parent_layout.addWidget(control_frame)
        
        # 记录总耗时
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds() * 1000
        self.logger.info(f"系统控制区域创建完成 - 总耗时: {total_duration:.2f}ms")
    
    def _create_log_area(self, parent_layout):
        """
        创建运行日志区域
        """
        start_time = datetime.now()
        self.logger.info(f"开始创建运行日志区域 - 开始时间: {start_time.strftime('%H:%M:%S.%f')[:-3]}")
        
        # 创建日志框架 - 使用PySide6原生样式
        frame_start = datetime.now()
        log_frame = QFrame()
        log_frame.setFrameStyle(QFrame.Box)
        log_frame.setLineWidth(1)
        log_frame.setAutoFillBackground(True)
        log_palette = log_frame.palette()
        log_palette.setColor(log_frame.backgroundRole(), QColor(255, 255, 255))  # #ffffff
        log_frame.setPalette(log_palette)
        frame_end = datetime.now()
        self.logger.debug(f"日志框架创建完成 - 耗时: {(frame_end - frame_start).total_seconds() * 1000:.2f}ms")
        
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(15, 5, 15, 5)  # 调整级别上方间距为5
        log_layout.setSpacing(5)  # 设置控件间距为5
        
        # 日志控制区域
        log_control_layout = QHBoxLayout()
        
        # 级别筛选 - 使用PySide6原生样式
        level_label = QLabel("级别:")
        level_label.setMaximumWidth(140)
        level_label.setWordWrap(True)
        level_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)  # 右对齐
        level_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Medium))
        level_label.setContentsMargins(5, 5, 5, 5)
        level_palette = level_label.palette()
        level_palette.setColor(level_label.foregroundRole(), QColor(0, 0, 0))
        level_label.setPalette(level_palette)
        log_control_layout.addWidget(level_label)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentText("INFO")
        self.log_level_combo.setMinimumWidth(80)
        self.log_level_combo.setFont(QFont("Microsoft YaHei UI", 9))
        combo_palette = self.log_level_combo.palette()
        combo_palette.setColor(self.log_level_combo.foregroundRole(), QColor(0, 0, 0))
        combo_palette.setColor(self.log_level_combo.backgroundRole(), QColor(255, 255, 255))
        self.log_level_combo.setPalette(combo_palette)
        self.log_level_combo.setAutoFillBackground(True)
        self.log_level_combo.currentTextChanged.connect(self._on_log_level_changed)
        log_control_layout.addWidget(self.log_level_combo)
        
        # 筛选输入框 - 使用PySide6原生样式
        filter_label = QLabel("筛选:")
        filter_label.setMaximumWidth(140)
        filter_label.setWordWrap(True)
        filter_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)  # 右对齐
        filter_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Medium))
        filter_label.setContentsMargins(5, 5, 5, 5)
        filter_palette = filter_label.palette()
        filter_palette.setColor(filter_label.foregroundRole(), QColor(0, 0, 0))
        filter_label.setPalette(filter_palette)
        log_control_layout.addWidget(filter_label)
        
        self.log_filter_input = QLineEdit()
        self.log_filter_input.setMaximumWidth(200)
        self.log_filter_input.setPlaceholderText("输入关键字筛选日志，按回车确认...")
        self.log_filter_input.setMinimumWidth(200)
        self.log_filter_input.setFont(QFont("Microsoft YaHei UI", 9))
        input_palette = self.log_filter_input.palette()
        input_palette.setColor(self.log_filter_input.foregroundRole(), QColor(0, 0, 0))
        input_palette.setColor(self.log_filter_input.backgroundRole(), QColor(255, 255, 255))
        self.log_filter_input.setPalette(input_palette)
        self.log_filter_input.setAutoFillBackground(True)
        # 连接回车键事件和文本变化事件
        self.log_filter_input.returnPressed.connect(self._on_log_filter_enter_pressed)
        self.log_filter_input.textChanged.connect(self._on_log_filter_changed)
        log_control_layout.addWidget(self.log_filter_input)
        
        # 停止滚动按钮 - 使用PySide6原生样式
        self.auto_scroll_button = QPushButton("停止滚动")
        self.auto_scroll_button.setMaximumSize(150, 30)
        self.auto_scroll_button.setFixedHeight(30)
        self.auto_scroll_button.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Medium))
        scroll_palette = self.auto_scroll_button.palette()
        scroll_palette.setColor(self.auto_scroll_button.foregroundRole(), QColor(0, 0, 0))
        scroll_palette.setColor(self.auto_scroll_button.backgroundRole(), QColor(96, 125, 139))  # #607D8B
        self.auto_scroll_button.setPalette(scroll_palette)
        self.auto_scroll_button.setAutoFillBackground(True)
        self.auto_scroll_button.clicked.connect(self._on_auto_scroll_clicked)
        log_control_layout.addWidget(self.auto_scroll_button)
        
        # 清空日志按钮已删除
        
        log_layout.addLayout(log_control_layout)
        
        # 日志显示区域
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 9))
        # 使用PySide6原生样式设置日志显示区域
        self.log_display.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.log_display.setLineWidth(2)
        self.log_display.setAutoFillBackground(True)
        # 修复：使用正确的颜色角色设置黑色背景
        log_palette = self.log_display.palette()
        log_palette.setColor(log_palette.ColorRole.Base, QColor(0, 0, 0))  # #000000 黑色背景
        log_palette.setColor(log_palette.ColorRole.Window, QColor(0, 0, 0))  # #000000 黑色背景
        log_palette.setColor(log_palette.ColorRole.Text, QColor(255, 255, 255))  # #ffffff 白色文字
        log_palette.setColor(log_palette.ColorRole.WindowText, QColor(255, 255, 255))  # #ffffff 白色文字
        log_palette.setColor(log_palette.ColorRole.Highlight, QColor(76, 175, 80))  # #4CAF50 选中背景
        log_palette.setColor(log_palette.ColorRole.HighlightedText, QColor(255, 255, 255))  # 选中文字
        self.log_display.setPalette(log_palette)
        # 强制设置样式表确保黑色背景生效
        self.log_display.setStyleSheet("QTextEdit { background-color: #000000; color: #ffffff; }")
        self.log_display.setContentsMargins(10, 10, 10, 10)
        log_layout.addWidget(self.log_display)
        
        parent_layout.addWidget(log_frame)
        
        # 记录总耗时
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds() * 1000
        self.logger.info(f"运行日志区域创建完成 - 总耗时: {total_duration:.2f}ms")
        
        return log_frame
    
    def _create_status_bar(self, parent_layout):
        """
        创建状态栏区域
        """
        start_time = datetime.now()
        self.logger.info(f"开始创建状态栏区域 - 开始时间: {start_time.strftime('%H:%M:%S.%f')[:-3]}")
        
        # 创建状态栏框架
        frame_start = datetime.now()
        status_frame = QFrame()
        status_frame.setFixedHeight(45)  # 设置状态栏高度为45px，确保内容完全显示
        # 使用PySide6原生样式设置状态栏框架
        status_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        status_frame.setLineWidth(1)
        status_frame.setAutoFillBackground(True)
        status_palette = status_frame.palette()
        status_palette.setColor(status_palette.ColorRole.Window, QColor(248, 249, 250))  # #f8f9fa
        status_palette.setColor(status_palette.ColorRole.WindowText, QColor(222, 226, 230))  # #dee2e6
        status_frame.setPalette(status_palette)
        frame_end = datetime.now()
        self.logger.debug(f"状态栏框架创建完成 - 耗时: {(frame_end - frame_start).total_seconds() * 1000:.2f}ms")
        
        status_layout = QHBoxLayout(status_frame)
        status_layout.setSpacing(5)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        # 系统状态
        self.system_status_label = QLabel(f"系统状态：{self.system_status}")
        # 使用PySide6原生样式设置系统状态标签
        system_palette = self.system_status_label.palette()
        system_palette.setColor(system_palette.ColorRole.WindowText, QColor(0, 0, 0))  # 黑色
        self.system_status_label.setPalette(system_palette)
        system_font = QFont("Microsoft YaHei", 9, QFont.Weight.Medium)
        self.system_status_label.setFont(system_font)
        self.system_status_label.setContentsMargins(8, 2, 8, 2)
        status_layout.addWidget(self.system_status_label)
        
        # 分隔符
        separator1 = QLabel("|")
        # 使用PySide6原生样式设置分隔符1
        sep1_palette = separator1.palette()
        sep1_palette.setColor(sep1_palette.ColorRole.WindowText, QColor(173, 181, 189))  # #adb5bd
        separator1.setPalette(sep1_palette)
        separator1.setContentsMargins(5, 0, 5, 0)
        status_layout.addWidget(separator1)
        
        # 运行状态
        self.running_status_label = QLabel(f"运行状态：{self.running_status}")
        # 使用PySide6原生样式设置运行状态标签
        running_palette = self.running_status_label.palette()
        running_palette.setColor(running_palette.ColorRole.WindowText, QColor(0, 0, 0))  # 黑色
        self.running_status_label.setPalette(running_palette)
        running_font = QFont("Microsoft YaHei", 9, QFont.Weight.Medium)
        self.running_status_label.setFont(running_font)
        self.running_status_label.setContentsMargins(8, 2, 8, 2)
        status_layout.addWidget(self.running_status_label)
        
        # 弹性空间
        status_layout.addStretch()
        
        # 分隔符
        separator2 = QLabel("|")
        # 使用PySide6原生样式设置分隔符2
        sep2_palette = separator2.palette()
        sep2_palette.setColor(sep2_palette.ColorRole.WindowText, QColor(173, 181, 189))  # #adb5bd
        separator2.setPalette(sep2_palette)
        separator2.setContentsMargins(5, 0, 5, 0)
        status_layout.addWidget(separator2)
        
        # 版本信息
        version_label = QLabel("HonyGo v1.0.0")
        # 使用PySide6原生样式设置版本标签
        version_palette = version_label.palette()
        version_palette.setColor(version_palette.ColorRole.WindowText, QColor(108, 117, 125))  # #6c757d
        version_label.setPalette(version_palette)
        version_font = QFont("Microsoft YaHei", 9, QFont.Weight.Medium)
        version_label.setFont(version_font)
        version_label.setContentsMargins(8, 2, 8, 2)
        status_layout.addWidget(version_label)
        
        parent_layout.addWidget(status_frame)
        
        # 记录总耗时
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds() * 1000
        self.logger.info(f"状态栏区域创建完成 - 总耗时: {total_duration:.2f}ms")
    
    def _setup_logging(self):
        """
        设置日志系统
        """
        start_time = datetime.now()
        self.logger.info(f"开始设置日志系统 - 开始时间: {start_time.strftime('%H:%M:%S.%f')[:-3]}")
        
        # 初始化日志显示线程（在QApplication创建后）
        if self.log_thread is None:
            thread_init_start = datetime.now()
            self.log_thread = LogDisplayThread()
            self.log_thread.log_received.connect(self._on_log_received)
            thread_init_end = datetime.now()
            self.logger.debug(f"日志显示线程初始化完成 - 耗时: {(thread_init_end - thread_init_start).total_seconds() * 1000:.2f}ms")
        
        # 设置UI日志回调
        callback_start = datetime.now()
        set_ui_log_callback(self._log_callback)
        callback_end = datetime.now()
        self.logger.debug(f"UI日志回调设置完成 - 耗时: {(callback_end - callback_start).total_seconds() * 1000:.2f}ms")
        
        # 启动日志显示线程
        thread_start = datetime.now()
        if self.log_thread and not self.log_thread.isRunning():
            self.log_thread.start()
        thread_end = datetime.now()
        self.logger.debug(f"日志显示线程启动完成 - 耗时: {(thread_end - thread_start).total_seconds() * 1000:.2f}ms")
        
        # 记录总耗时
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds() * 1000
        self.logger.info(f"日志系统设置完成 - 总耗时: {total_duration:.2f}ms")
    
    def _log_callback(self, level: str, message: str):
        """
        日志回调函数
        """
        try:
            # 修复：使用Qt的线程安全信号机制，避免直接操作UI
            if self.log_thread and self.log_thread.isRunning():
                self.log_thread.log_received.emit(level, message)
        except Exception as e:
            # 避免日志回调异常导致程序崩溃
            self.logger.error(f"日志回调异常: {e}")
    
    def _on_log_received(self, level: str, message: str):
        """
        处理接收到的日志消息
        """
        try:
            if not self.log_display:
                return
            
            # 添加时间戳
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] [{level}] {message}"
            
            # 存储到所有日志条目列表中
            log_entry = {
                'level': level,
                'message': message,
                'timestamp': timestamp,
                'formatted_message': formatted_message
            }
            self.all_log_entries.append(log_entry)
            
            # 如果停止滚动，将日志缓存到pending列表中
            if not self.auto_scroll_enabled:
                self.pending_log_entries.append(log_entry)
                return
            
            # 检查是否通过筛选
            if self._should_show_log_entry(log_entry):
                # 根据级别设置颜色
                color_map = {
                    "DEBUG": "#888888",
                    "INFO": "#ffffff",  # 修复：INFO级别使用白色文字，确保在黑色背景上可见
                    "WARNING": "#ff8800",
                    "ERROR": "#ff4444",
                    "CRITICAL": "#ff0000"
                }
                color = color_map.get(level, "#ffffff")  # 默认使用白色文字
                
                # 修复：直接更新UI，因为信号槽机制已经保证了线程安全
                self.log_display.setTextColor(color)
                self.log_display.append(formatted_message)
                
                # 自动滚动到底部
                scrollbar = self.log_display.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            self.logger.error(f"日志处理异常: {e}")
    
    def _should_show_log_entry(self, log_entry):
        """
        检查日志条目是否应该显示（通过筛选条件）
        """
        try:
            # 检查级别筛选
            if self.log_level_combo:
                current_level = self.log_level_combo.currentText()
                if current_level != "ALL":
                    level_priority = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
                    if level_priority.get(log_entry['level'], 0) < level_priority.get(current_level, 0):
                        return False
            
            # 检查关键字筛选
            if self.log_filter_input:
                filter_text = self.log_filter_input.text().strip()
                if filter_text and filter_text.lower() not in log_entry['message'].lower():
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"筛选检查异常: {e}")
            return True
    
    def _apply_log_filters(self):
        """
        重新应用日志筛选条件，刷新显示的日志
        """
        try:
            if not self.log_display:
                return
            
            # 清空当前显示
            self.log_display.clear()
            
            # 根据级别设置颜色映射
            color_map = {
                "DEBUG": "#888888",
                "INFO": "#ffffff",
                "WARNING": "#ff8800",
                "ERROR": "#ff4444",
                "CRITICAL": "#ff0000"
            }
            
            # 重新显示符合条件的日志
            for log_entry in self.all_log_entries:
                if self._should_show_log_entry(log_entry):
                    color = color_map.get(log_entry['level'], "#ffffff")
                    self.log_display.setTextColor(color)
                    self.log_display.append(log_entry['formatted_message'])
            
            # 自动滚动到底部
            if self.auto_scroll_enabled:
                scrollbar = self.log_display.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
        except Exception as e:
            self.logger.error(f"应用日志筛选异常: {e}")
    
    def _connect_signals(self):
        """
        连接信号和槽
        """
        start_time = datetime.now()
        self.logger.info(f"开始连接信号和槽 - 开始时间: {start_time.strftime('%H:%M:%S.%f')[:-3]}")
        
        # 信号连接已在组件创建时完成
        self.logger.debug("所有信号和槽连接已在组件创建时完成")
        
        # 记录总耗时
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds() * 1000
        self.logger.info(f"信号和槽连接完成 - 总耗时: {total_duration:.2f}ms")
    
    # 事件处理方法
    def _on_exit_clicked(self):
        """
        退出按钮点击事件
        """
        self.logger.info("用户点击退出按钮")
        self.logger.debug("显示退出确认对话框")
        
        try:
            reply = QMessageBox.question(self, "确认退出", "确定要退出HonyGo吗？",
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.logger.info("用户确认退出应用程序")
                self.logger.debug("开始执行应用程序退出流程")
                self.close()
            else:
                self.logger.info("用户取消退出操作")
                
        except Exception as e:
            self.logger.error(f"处理退出操作失败: {e}")
            # 即使出错也要尝试关闭
            self.close()
    
    def _on_keyword_changed(self, text):
        """
        关键字输入框变更事件
        """
        old_keyword = self.config.get('keyword', '')
        self.config['keyword'] = text
        
        if text.strip():
            self.logger.info(f"用户修改关键字: '{text}'")
            self.logger.debug(f"关键字长度: {len(text)} 字符")
        else:
            self.logger.warning("用户清空了关键字配置")
        
        if old_keyword != text:
            self.logger.debug(f"关键字配置变更: '{old_keyword}' -> '{text}'")
        else:
            self.logger.debug("关键字配置未发生变化")
    
    def _on_interval_changed(self, value):
        """
        点击间隔变更事件
        """
        old_interval = self.config.get('click_interval', 0)
        self.config['click_interval'] = value
        
        self.logger.info(f"用户修改点击间隔: {value}毫秒")
        
        if value < 100:
            self.logger.warning(f"点击间隔设置过短: {value}毫秒，可能影响系统稳定性")
        elif value > 5000:
            self.logger.info(f"点击间隔设置较长: {value}毫秒，操作频率较低")
        
        if old_interval != value:
            self.logger.debug(f"点击间隔配置变更: {old_interval}毫秒 -> {value}毫秒")
        else:
            self.logger.debug("点击间隔配置未发生变化")
    
    def _on_mouse_button_changed(self, button):
        """
        鼠标按键变更事件
        """
        old_button = self.config.get('mouse_button', 'left')
        button_text = "左键" if button.text() == "左键" else "右键"
        new_button = "left" if button_text == "左键" else "right"
        
        self.config['mouse_button'] = new_button
        self.logger.info(f"用户修改鼠标按键: {button_text}")
        
        if old_button != new_button:
            old_text = "左键" if old_button == "left" else "右键"
            self.logger.debug(f"鼠标按键配置变更: {old_text} -> {button_text}")
        else:
            self.logger.debug("鼠标按键配置未发生变化")
    
    def _on_frequency_changed(self, value):
        """
        监控频率变更事件
        """
        old_frequency = self.config.get('monitor_frequency', 0)
        self.config['monitor_frequency'] = value
        
        self.logger.info(f"用户修改监控频率: {value}秒")
        
        if value < 0.1:
            self.logger.warning(f"监控频率设置过高: {value}秒，最小允许0.1秒，可能消耗大量系统资源")
        elif value < 0.5:
            self.logger.info(f"监控频率设置较高: {value}秒，将消耗较多系统资源但响应更快")
        elif value > 10:
            self.logger.info(f"监控频率设置较低: {value}秒，响应速度较慢但资源消耗少")
        
        if old_frequency != value:
            self.logger.debug(f"监控频率配置变更: {old_frequency}秒 -> {value}秒")
        else:
            self.logger.debug("监控频率配置未发生变化")
    
    def _on_algorithm_type_changed(self, button):
        """
        算法类型改变事件处理
        """
        try:
            if button == self.ocr_pool_radio:
                # 选择OCR池，显示关键字输入控件，隐藏图片选择控件和阈值控件
                self.keyword_label.setVisible(True)
                self.keyword_input.setVisible(True)
                self.keyword_input.setReadOnly(False)  # 设置为可编辑
                self.image_ref_label.setVisible(False)
                self.image_widget.setVisible(False)
                self.threshold_label.setVisible(False)
                self.threshold_input.setVisible(False)
                self.logger.info("算法类型切换为: OCR池")
            elif button == self.image_ref_radio:
                # 选择图片参照，关键字控件改为只读状态而不是隐藏，显示图片选择控件、标题和阈值控件
                self.keyword_label.setVisible(True)
                self.keyword_input.setVisible(True)
                self.keyword_input.setReadOnly(True)  # 设置为只读
                self.image_ref_label.setVisible(True)
                self.image_widget.setVisible(True)
                self.threshold_label.setVisible(True)
                self.threshold_input.setVisible(True)
                self.logger.info("算法类型切换为: 图片参照")
        except Exception as e:
            self.logger.error(f"切换算法类型时发生错误: {str(e)}")
    
    def _on_select_image_clicked(self):
        """
        选择图片按钮点击事件处理
        """
        try:
            file_dialog = QFileDialog()
            file_dialog.setFileMode(QFileDialog.ExistingFile)
            file_dialog.setNameFilter("图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)")
            file_dialog.setViewMode(QFileDialog.Detail)
            
            if file_dialog.exec():
                selected_files = file_dialog.selectedFiles()
                if selected_files:
                    self.selected_image_path = selected_files[0]
                    # 显示文件名和路径
                    file_name = os.path.basename(self.selected_image_path)
                    self.image_path_input.setText(f"{file_name} ({self.selected_image_path})")
                    self.logger.info(f"已选择图片文件: {self.selected_image_path}")
        except Exception as e:
            self.logger.error(f"选择图片文件时发生错误: {str(e)}")
            QMessageBox.warning(self, "错误", f"选择图片文件时发生错误: {str(e)}")
    
    def _on_threshold_changed(self, value):
        """
        匹配阈值变更事件处理
        """
        try:
            self.config['similarity_threshold'] = value
            self.logger.info(f"图片参照匹配阈值已更新为: {value:.2f}")
        except Exception as e:
            self.logger.error(f"更新匹配阈值时发生错误: {str(e)}")
    
    def _start_ocr_service_connection(self):
        """
        启动OCR实例池服务连接（内部方法）
        """
        self.logger.info("检测到OCR实例池服务未连接，正在尝试启动连接")
        self._start_ocr_service_internal()
    
    def _start_ocr_service_internal(self):
        """
        启动OCR实例池服务（内部方法，不显示弹出框）
        """
        self.logger.info("内部启动OCR实例池服务")
        self.logger.debug("开始启动OCR实例池服务进程")
        
        try:
            # 启动跨进程日志桥接服务
            self._start_log_bridge_service()
            
            # 检查服务是否已经运行
            if requests:
                try:
                    response = requests.get('http://127.0.0.1:8900/health', timeout=2)
                    if response.status_code == 200:
                        self.logger.info("OCR实例池服务已在运行中，连接状态正常")
                        self.logger.info("OCR实例池服务地址: http://127.0.0.1:8900")
                        self.logger.info("OCR实例池服务健康检查: 通过")
                        return
                except:
                    pass  # 服务未运行，继续启动
            
            # 启动OCR实例池服务
            import subprocess
            import sys
            from pathlib import Path
            import os
            
            # 获取OCR服务脚本路径
            project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
            if project_root_env:
                project_root = Path(project_root_env)
            else:
                # 备用方案：从当前文件路径计算
                project_root = Path(__file__).parent.parent.parent.parent
            
            ocr_service_script = project_root / "src" / "core" / "ocr" / "services" / "ocr_pool_service.py"
            
            if not ocr_service_script.exists():
                self.logger.error(f"OCR实例池服务脚本不存在: {ocr_service_script}")
                return
            
            # 启动服务进程（不显示控制台窗口）
            self.logger.debug(f"正在启动OCR实例池服务: {ocr_service_script}")
            process = subprocess.Popen(
                [sys.executable, str(ocr_service_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            self.logger.info(f"OCR实例池服务进程已启动，PID: {process.pid}")
            self.logger.info("OCR实例池服务启动成功，服务已在后台运行")
            
        except ImportError as e:
            self.logger.error(f"导入模块失败: {e}")
        except Exception as e:
            self.logger.error(f"启动OCR实例池服务失败: {e}")
    
    def _on_start_ocr_service_clicked(self):
        """
        启动OCR实例池服务按钮点击事件
        """
        self.logger.info("用户点击启动OCR实例池服务按钮")
        self.logger.debug("开始启动OCR实例池服务进程")
        
        try:
            # 启动跨进程日志桥接服务
            self._start_log_bridge_service()
            
            # 检查服务是否已经运行
            if requests:
                try:
                    response = requests.get('http://127.0.0.1:8900/health', timeout=2)
                    if response.status_code == 200:
                        self.logger.info("OCR实例池服务已在运行中，连接状态正常")
                        self.logger.info("OCR实例池服务地址: http://127.0.0.1:8900")
                        self.logger.info("OCR实例池服务健康检查: 通过")
                        
                        # 注意：已移除OCR日志轮询定时器，日志通过统一日志服务传递
                        self.logger.info("OCR日志将通过统一日志服务自动显示在主界面")
                        
                        QMessageBox.information(self, "服务状态", "OCR实例池服务已在运行中")
                        return
                except:
                    pass  # 服务未运行，继续启动
            
            # 启动OCR实例池服务
            import subprocess
            import sys
            from pathlib import Path
            
            # 获取OCR服务脚本路径
            project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
            if project_root_env:
                project_root = Path(project_root_env)
            else:
                # 备用方案：从当前文件路径计算
                project_root = Path(__file__).parent.parent.parent.parent
            
            ocr_service_script = project_root / "src" / "core" / "ocr" / "services" / "ocr_pool_service.py"
            
            if not ocr_service_script.exists():
                self.logger.error(f"OCR实例池服务脚本不存在: {ocr_service_script}")
                QMessageBox.critical(self, "启动失败", "OCR实例池服务脚本文件不存在")
                return
            
            # 启动服务进程（不显示控制台窗口）
            self.logger.debug(f"正在启动OCR实例池服务: {ocr_service_script}")
            process = subprocess.Popen(
                [sys.executable, str(ocr_service_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            self.logger.info(f"OCR实例池服务进程已启动，PID: {process.pid}")
            self.logger.info("OCR实例池服务启动成功，服务已在后台运行")
            self.logger.info("OCR日志将通过统一日志服务自动显示在主界面")
            
        except ImportError as e:
            self.logger.error(f"导入模块失败: {e}")
            QMessageBox.critical(self, "启动失败", f"导入必要模块失败: {e}")
        except Exception as e:
            self.logger.error(f"启动OCR实例池服务失败: {e}")
            QMessageBox.critical(self, "启动失败", f"启动OCR实例池服务失败\n\n错误详情: {str(e)}")
    
    def _start_log_bridge_service(self):
        """
        启动跨进程日志桥接服务
        """
        try:
            if self.log_bridge is None:
                self.logger.info("启动跨进程日志桥接服务")
                self.log_bridge = get_log_bridge_server()
                
                # 设置UI回调函数，将OCR池日志转发到主界面
                self.log_bridge.set_ui_callback(self._on_ocr_log_received)
                
                # 启动日志桥接服务器
                if self.log_bridge.start_server():
                    self.logger.info("跨进程日志桥接服务启动成功，端口: 8902")
                else:
                    self.logger.error("跨进程日志桥接服务启动失败")
                    self.log_bridge = None
            else:
                self.logger.debug("跨进程日志桥接服务已在运行中")
        except Exception as e:
            self.logger.error(f"启动跨进程日志桥接服务失败: {e}")
            self.log_bridge = None
    
    def _stop_log_bridge_service(self):
        """
        停止跨进程日志桥接服务
        """
        try:
            if self.log_bridge is not None:
                self.logger.info("停止跨进程日志桥接服务")
                self.log_bridge.stop_server()
                self.log_bridge = None
                self.logger.info("跨进程日志桥接服务已停止")
        except Exception as e:
            self.logger.error(f"停止跨进程日志桥接服务失败: {e}")
    
    def _on_ocr_log_received(self, level: str, message: str):
        """
        处理从OCR池接收到的日志消息
        """
        try:
            # 为OCR池日志添加标识前缀
            ocr_message = f"[OCR池] {message}"
            
            # 通过现有的日志回调机制显示到主界面
            self._log_callback(level, ocr_message)
        except Exception as e:
            self.logger.error(f"处理OCR池日志失败: {e}")
    
    def _on_stop_ocr_service_clicked(self):
        """
        停止OCR实例池服务按钮点击事件
        """
        self.logger.info("用户点击停止OCR实例池服务按钮")
        self.logger.debug("开始停止OCR实例池服务进程")
        
        try:
            # 检查服务是否在运行
            service_running = False
            if requests:
                try:
                    response = requests.get('http://127.0.0.1:8900/health', timeout=2)
                    if response.status_code == 200:
                        service_running = True
                except:
                    pass
            
            if not service_running:
                self.logger.info("OCR实例池服务未启动，无需停止操作")
                self.logger.info("OCR实例池服务状态: 未运行")
                self.logger.info("建议: 如需使用OCR功能，请先启动OCR实例池服务")
                QMessageBox.information(self, "服务状态", "OCR实例池服务未在运行")
                return
            
            # OCR实例池服务没有提供shutdown端点，直接通过进程终止
            # 查找并终止OCR实例池服务进程
            import psutil
            import signal
            
            self.logger.debug("正在查找OCR实例池服务进程")
            terminated_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and any('ocr_pool_service.py' in arg or 'ocr.services.ocr_pool_service' in arg for arg in cmdline):
                        self.logger.debug(f"找到OCR实例池服务进程: PID {proc.info['pid']}")
                        proc.terminate()
                        terminated_processes.append(proc.info['pid'])
                        self.logger.info(f"已终止OCR实例池服务进程: PID {proc.info['pid']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            if terminated_processes:
                # 停止OCR日志轮询定时器
                if hasattr(self, 'ocr_log_timer') and self.ocr_log_timer:
                    self.ocr_log_timer.stop()
                    self.logger.info("OCR日志轮询定时器已停止")
                
                # 停止跨进程日志桥接服务
                self._stop_log_bridge_service()
                
                QMessageBox.information(self, "停止成功", f"OCR实例池服务已停止\n终止的进程PID: {', '.join(map(str, terminated_processes))}")
            else:
                self.logger.warning("未找到OCR实例池服务进程")
                QMessageBox.warning(self, "停止失败", "未找到正在运行的OCR实例池服务进程")
                
        except ImportError as e:
            self.logger.error(f"导入模块失败: {e}")
            QMessageBox.critical(self, "停止失败", f"导入必要模块失败: {e}")
        except Exception as e:
            self.logger.error(f"停止OCR实例池服务失败: {e}")
            QMessageBox.critical(self, "停止失败", f"停止OCR实例池服务失败\n\n错误详情: {str(e)}")
    
    def _on_ocr_pool_clicked(self):
        """
        OCR实例池管理按钮点击事件
        """
        self.logger.info("用户点击OCR实例池管理按钮")
        self.logger.debug("开始检查OCR实例池服务连接状态")
        
        # 检查OCR池服务状态
        ocr_pool_available = False
        connection_error_msg = None
        
        try:
            if requests:
                self.logger.debug("正在连接OCR实例池服务(127.0.0.1:8900)")
                response = requests.get('http://127.0.0.1:8900/health', timeout=3)
                if response.status_code == 200:
                    self.logger.info("OCR实例池服务连接成功，状态正常")
                    ocr_pool_available = True
                else:
                    self.logger.warning(f"OCR实例池服务状态异常，返回状态码: {response.status_code}")
                    connection_error_msg = f"OCR实例池服务返回状态码: {response.status_code}"
            else:
                self.logger.error("requests模块不可用，无法检查OCR实例池服务状态")
                connection_error_msg = "requests模块不可用"
        except (requests.exceptions.ConnectionError, ConnectionRefusedError) as e:
            self.logger.error(f"无法连接到OCR实例池服务(127.0.0.1:8900): {e}")
            connection_error_msg = "无法连接到OCR实例池服务，服务可能未启动"
        except requests.exceptions.Timeout as e:
            self.logger.error(f"连接OCR实例池服务超时: {e}")
            connection_error_msg = "连接OCR实例池服务超时"
        except (OSError, IOError) as e:
            self.logger.error(f"网络连接错误: {e}")
            connection_error_msg = "网络连接错误"
        except Exception as e:
            # 捕获所有其他异常，包括urllib3异常
            error_type = type(e).__name__
            error_str = str(e)
            
            # 特别处理urllib3相关异常
            if 'urllib3' in error_type or 'NewConnectionError' in error_str or 'ConnectionError' in error_type:
                self.logger.error(f"网络连接异常 ({error_type}): {e}")
                connection_error_msg = "网络连接被拒绝，OCR实例池服务未启动"
            else:
                self.logger.error(f"检查OCR实例池服务状态失败 ({error_type}): {e}")
                connection_error_msg = f"检查OCR实例池服务状态失败: {error_type}"
        
        # 如果OCR池服务不可用，直接提醒用户并返回
        if not ocr_pool_available:
            self.logger.warning(f"OCR实例池服务未连接，拒绝打开管理界面。原因: {connection_error_msg}")
            QMessageBox.warning(
                self, 
                "OCR实例池服务未连接", 
                f"OCR实例池服务未连接，无法打开管理界面。\n\n错误详情: {connection_error_msg}\n\n请先启动OCR实例池服务后再试。",
                QMessageBox.Ok
            )
            return
        
        # OCR池服务可用，打开管理窗口
        try:
            self.logger.debug("OCR实例池服务连接正常，准备打开管理窗口")
            # 导入并打开OCR实例池窗口
            from src.ui.windows.ocr_pool_window import OCRPoolWindow
            self.ocr_pool_window = OCRPoolWindow(parent=self)
            self.ocr_pool_window.show()
            self.logger.info("OCR实例池管理窗口已成功打开")
        except ImportError as e:
            self.logger.error(f"无法导入OCR实例池窗口模块: {e}")
            QMessageBox.warning(self, "模块导入错误", "OCR实例池窗口模块导入失败")
        except Exception as e:
            self.logger.error(f"打开OCR实例池管理窗口失败: {e}")
            QMessageBox.critical(self, "打开失败", f"打开OCR实例池管理窗口失败\n\n错误详情: {str(e)}")
    
    def _on_select_area_clicked(self):
        """
        选择监控区域按钮点击事件
        """
        self.logger.info("用户点击选择监控区域按钮")
        self.logger.debug("开始执行监控区域选择流程")
        
        try:
            # 记录当前监控区域配置
            current_area = self.config.get('monitor_area', None)
            self.logger.debug(f"当前监控区域配置: {current_area}")
            
            # 导入并打开区域选择窗口
            self.logger.debug("尝试导入区域选择窗口模块")
            from src.ui.windows.area_selector_window import AreaSelectorWindow
            
            self.logger.debug("创建区域选择窗口实例")
            self.area_selector = AreaSelectorWindow()
            self.area_selector.area_selected.connect(self._on_area_selected)
            
            self.logger.debug("显示区域选择窗口")
            self.area_selector.show()
            self.logger.info("区域选择窗口已成功打开")
            
        except ImportError as e:
            self.logger.error(f"无法导入区域选择窗口模块: {e}")
            self.logger.warning("区域选择功能模块不可用，可能尚未实现")
            QMessageBox.warning(self, "功能提示", "区域选择功能尚未实现\n\n将在后续版本中提供可视化区域选择工具")
        except Exception as e:
            self.logger.error(f"打开区域选择窗口失败: {e}")
            QMessageBox.critical(self, "操作失败", f"打开区域选择窗口失败\n\n错误详情: {str(e)}")
    
    def _on_area_selected(self, area_info):
        """
        区域选择完成事件
        """
        self.logger.debug(f"接收到区域选择结果: {area_info}")
        
        try:
            # 验证区域信息有效性
            required_keys = ['x', 'y', 'width', 'height']
            if not all(key in area_info for key in required_keys):
                self.logger.error(f"区域信息不完整，缺少必要字段: {required_keys}")
                QMessageBox.warning(self, "区域信息错误", "选择的区域信息不完整")
                return
            
            # 检查区域尺寸合理性
            if area_info['width'] <= 0 or area_info['height'] <= 0:
                self.logger.warning(f"区域尺寸无效: 宽度={area_info['width']}, 高度={area_info['height']}")
                QMessageBox.warning(self, "区域尺寸错误", "选择的区域尺寸无效")
                return
            
            # 更新配置
            old_area = self.config.get('monitor_area', None)
            self.config['monitor_area'] = area_info
            
            # 更新界面显示
            area_text = f"X: {area_info['x']}, Y: {area_info['y']}, 宽度: {area_info['width']}, 高度: {area_info['height']}"
            self.area_display.setText(area_text)
            
            self.logger.info(f"监控区域已更新: {area_text}")
            if old_area:
                self.logger.debug(f"原区域配置: {old_area}")
            
        except Exception as e:
            self.logger.error(f"处理区域选择结果失败: {e}")
            QMessageBox.critical(self, "处理失败", f"处理区域选择结果失败\n\n错误详情: {str(e)}")
    
    def _on_start_clicked(self):
        """
        启动按钮点击事件
        """
        self.logger.info("用户点击启动按钮")
        self.logger.debug("开始启动自动化操作流程")
        
        try:
            # 检查配置参数
            self.logger.debug(f"当前配置参数: 关键字='{self.config['keyword']}', 点击间隔={self.config['click_interval']}ms, 鼠标按键={self.config['mouse_button']}, 监控频率={self.config['monitor_frequency']}s")
            
            # 获取当前选择的算法类型
            algorithm_type = "ocr_pool" if self.ocr_pool_radio.isChecked() else "image_reference"
            
            # 验证配置有效性
            if algorithm_type == "ocr_pool":
                if not self.config['keyword'].strip():
                    self.logger.warning("关键字为空，无法启动OCR池算法")
                    QMessageBox.warning(self, "配置错误", "请先设置关键字")
                    return
                
                # 检查并启动OCR池服务
                self.logger.info("检查OCR池服务状态...")
                if not self._ensure_ocr_service_ready():
                    self.logger.error("OCR池服务未就绪，无法启动任务")
                    QMessageBox.critical(self, "服务未就绪", "OCR池服务未就绪，请先启动OCR池服务")
                    return
                    
            elif algorithm_type == "image_reference":
                if not self.selected_image_path or not os.path.exists(self.selected_image_path):
                    self.logger.warning("未选择有效的参照图片，无法启动图片参照算法")
                    QMessageBox.warning(self, "配置错误", "请先选择有效的参照图片")
                    return
            
            # 准备任务配置
            task_config = {
                'algorithm_type': algorithm_type,
                'keyword': self.config['keyword'],
                'image_path': self.selected_image_path if algorithm_type == "image_reference" else None,
                'click_interval': self.config['click_interval'],
                'mouse_button': self.config['mouse_button'],
                'monitor_frequency': self.config['monitor_frequency'],
                'monitor_area': self.config['monitor_area']
            }
            
            # 启动模拟任务
            self.logger.debug(f"准备启动模拟任务，配置: {task_config}")
            self.logger.info(f"调用simulation_task_service.start_task，参数: {task_config}")
            
            try:
                success = self.simulation_task_service.start_task(task_config)
                self.logger.info(f"simulation_task_service.start_task返回结果: {success}")
            except Exception as start_exception:
                self.logger.error(f"调用simulation_task_service.start_task时发生异常: {start_exception}")
                import traceback
                self.logger.error(f"异常堆栈: {traceback.format_exc()}")
                success = False
            
            if success:
                # 更新界面状态
                self.running_status = "运行中"
                self.running_status_label.setText(f"运行状态：{self.running_status}")
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                
                self.logger.info(f"模拟任务已启动 - 算法类型: {algorithm_type}, 关键字: '{self.config['keyword']}', 监控区域: {self.config['monitor_area']}")
            else:
                self.logger.error(f"模拟任务启动失败 - 算法类型: {algorithm_type}, 配置: {task_config}")
                QMessageBox.critical(self, "启动失败", "模拟任务启动失败，请检查日志获取详细信息")
            
        except Exception as e:
            self.logger.error(f"启动自动化操作失败: {e}")
            QMessageBox.critical(self, "启动失败", f"启动自动化操作失败\n\n错误详情: {str(e)}")
    
    def _on_stop_clicked(self):
        """
        停止按钮点击事件
        """
        self.logger.info("用户点击停止按钮")
        self.logger.debug("开始停止自动化操作流程")
        
        try:
            # 停止模拟任务
            success = self.simulation_task_service.stop_task()
            
            if success:
                # 更新界面状态
                self.running_status = "已停止"
                self.running_status_label.setText(f"运行状态：{self.running_status}")
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                
                self.logger.info("模拟任务已成功停止")
            else:
                self.logger.warning("模拟任务停止时出现问题，请检查日志")
            
        except Exception as e:
            self.logger.error(f"停止自动化操作失败: {e}")
            QMessageBox.critical(self, "停止失败", f"停止自动化操作失败\n\n错误详情: {str(e)}")
    
    def _on_test_clicked(self):
        """
        测试按钮点击事件 - 根据算法类型执行不同的测试逻辑
        """
        self.logger.info("用户点击测试按钮")
        
        try:
            # 判断当前选择的算法类型
            if self.ocr_pool_radio.isChecked():
                self.logger.info("当前算法类型: OCR池")
                self._test_ocr_pool_algorithm()
            elif self.image_ref_radio.isChecked():
                self.logger.info("当前算法类型: 图片参照")
                self._test_image_reference_algorithm()
            else:
                self.logger.error("未选择算法类型")
                return
                
        except Exception as e:
            self.logger.error(f"执行测试失败: {e}")
    
    def _test_ocr_pool_algorithm(self):
        """
        OCR池算法测试逻辑
        """
        self.logger.debug("开始执行OCR池算法测试流程")
        
        try:
            # 检查关键词配置
            keyword = self.config.get('keyword', '').strip()
            if not keyword:
                self.logger.warning("关键词配置为空，无法执行OCR池测试")
                self.logger.warning("请先配置关键词后再执行测试")
                return
            
            # 检查OCR服务状态
            self.logger.debug("检查OCR实例池服务状态")
            try:
                if requests:
                    response = requests.get('http://127.0.0.1:8900/health', timeout=3)
                    if response.status_code == 200:
                        self.logger.info("OCR实例池服务已连接，状态正常")
                    else:
                        self.logger.error(f"OCR实例池服务状态异常: {response.status_code}")
                        self.logger.error("请手动启动OCR实例池服务后再执行测试")
                        return
                else:
                    self.logger.error("requests模块不可用")
                    self.logger.error("无法检查OCR实例池服务状态")
                    return
            except Exception as e:
                self.logger.error(f"OCR实例池服务连接失败: {e}")
                self.logger.error("请手动启动OCR实例池服务后再执行测试")
                return
            
            # 导入智能点击服务
            try:
                from src.ui.services.smart_click_service import SmartClickService
                from src.core.ocr.utils.keyword_matcher import MatchStrategy
            except ImportError as e:
                self.logger.error(f"导入智能点击服务失败: {e}")
                self.logger.error("请检查智能点击服务模块路径是否正确")
                return
            
            # 创建智能点击服务实例
            click_service = SmartClickService()
            
            # 配置点击服务
            click_interval = self.config.get('click_interval', 1000)
            click_service.configure_click_behavior(
                click_interval=click_interval,
                min_confidence=0.3,
                min_similarity=0.5
            )
            
            # 启用关键词标记功能
            click_service.configure_keyword_marker(enabled=True)
            self.logger.info("已启用关键词匹配蓝色标记功能")
            
            # 动画功能已移除
            
            # 连接信号
            click_service.log_message.connect(lambda msg: self.logger.info(msg))
            click_service.click_performed.connect(
                lambda x, y, text: self.logger.info(f"执行点击: '{text}' at ({x}, {y})")
            )
            
            self.logger.info(f"开始测试流程 - 关键词: '{keyword}'")
            
            # 获取监控区域配置
            monitor_area = self.config.get('monitor_area', None)
            
            # 判断是否使用用户指定区域
            if monitor_area and all(key in monitor_area for key in ['x', 'y', 'width', 'height']):
                # 检查是否为默认全屏配置（通常x=0, y=0且为屏幕尺寸）
                import tkinter as tk
                root = tk.Tk()
                screen_width = root.winfo_screenwidth()
                screen_height = root.winfo_screenheight()
                root.destroy()
                
                is_fullscreen = (
                    monitor_area['x'] == 0 and 
                    monitor_area['y'] == 0 and 
                    monitor_area['width'] == screen_width and 
                    monitor_area['height'] == screen_height
                )
                
                if is_fullscreen:
                    self.logger.info("使用默认全屏截图模式")
                    self.logger.debug(f"全屏区域: 宽度={screen_width}, 高度={screen_height}")
                    monitor_area_param = None  # 使用全屏
                else:
                    self.logger.info(f"使用用户指定区域截图模式 - X:{monitor_area['x']}, Y:{monitor_area['y']}, 宽度:{monitor_area['width']}, 高度:{monitor_area['height']}")
                    self.logger.debug(f"指定区域详情: {monitor_area}")
                    monitor_area_param = monitor_area
            else:
                self.logger.info("使用默认全屏截图模式（未配置监控区域）")
                self.logger.debug("监控区域配置无效或未设置，使用全屏模式")
                monitor_area_param = None
            
            # 执行智能点击（启用精确定位功能）
            result = click_service.smart_click_targets(
                target_keyword=keyword,
                monitor_area=monitor_area_param,
                max_targets=5,
                strategy=MatchStrategy.CONTAINS
            )
            
            self.logger.info(f"OCR池测试已启用精确定位功能，提高点击位置准确性")
            
            # 处理结果
            if result.get('success'):
                click_details = result.get('click_details', {})
                successful_clicks = click_details.get('successful_clicks', [])
                failed_clicks = click_details.get('failed_clicks', [])
                
                success_count = len(successful_clicks)
                fail_count = len(failed_clicks)
                
                self.logger.info(f"测试完成 - 成功点击: {success_count}, 失败: {fail_count}")
                
                if success_count > 0:
                    click_details = []
                    for i, click_info in enumerate(successful_clicks[:3]):  # 只显示前3个
                        text = click_info.get('text', '')
                        position = click_info.get('position', (0, 0))
                        click_details.append(f"• '{text}' at ({position[0]}, {position[1]})")
                    
                    details_text = "\n".join(click_details)
                    if success_count > 3:
                        details_text += f"\n... 还有 {success_count - 3} 个点击"
                    
                    self.logger.info(f"测试执行完成 - 成功点击: {success_count} 个目标, 失败: {fail_count} 个目标")
                    self.logger.info(f"点击详情:\n{details_text}")
                else:
                    self.logger.info(f"测试执行完成 - 未找到匹配的关键词 '{keyword}'")
                    self.logger.info("请检查关键词配置或屏幕内容")
            else:
                error_msg = result.get('error', '未知错误')
                self.logger.error(f"测试执行失败: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"执行OCR池测试失败: {e}")
    
    def _test_image_reference_algorithm(self):
        """
        图片参照算法测试逻辑
        """
        self.logger.debug("开始执行图片参照算法测试流程")
        
        try:
            # 检查图片参照配置 - 优先使用selected_image_path
            image_path = getattr(self, 'selected_image_path', '').strip()
            if not image_path:
                # 回退到config中的配置
                image_path = self.config.get('reference_image_path', '').strip()
                if not image_path:
                    self.logger.warning("请先上传参照图片后再执行测试")
                    return
            
            # 检查图片文件是否存在
            import os
            if not os.path.exists(image_path):
                self.logger.error(f"参照图片文件不存在: {image_path}")
                self.logger.error("请重新选择有效的参照图片")
                return
            
            # 更新config中的参照图片路径
            self.config['reference_image_path'] = image_path
            
            self.logger.info(f"使用参照图片: {image_path}")
            
            # 导入图片匹配服务
            try:
                from src.ui.services.smart_click_service import SmartClickService
            except ImportError as e:
                self.logger.error(f"导入智能点击服务失败: {e}")
                return
            
            # 创建智能点击服务实例
            click_service = SmartClickService()
            
            # 获取用户配置的匹配阈值
            similarity_threshold = self.config.get('similarity_threshold', 0.15)
            
            # 配置点击服务
            click_interval = self.config.get('click_interval', 1000)
            click_service.configure_click_behavior(
                click_interval=click_interval,
                min_confidence=0.3,
                min_similarity=similarity_threshold  # 使用用户配置的匹配阈值
            )
            
            # 动画功能已移除
            
            # 连接信号
            click_service.log_message.connect(lambda msg: self.logger.info(msg))
            click_service.click_performed.connect(
                lambda x, y, text: self.logger.info(f"执行点击: 图片匹配 at ({x}, {y})")
            )
            
            self.logger.info(f"开始图片匹配测试流程")
            
            # 获取监控区域配置
            monitor_area = self.config.get('monitor_area', None)
            
            # 判断是否使用用户指定区域
            if monitor_area and all(key in monitor_area for key in ['x', 'y', 'width', 'height']):
                # 检查是否为默认全屏配置
                import tkinter as tk
                root = tk.Tk()
                screen_width = root.winfo_screenwidth()
                screen_height = root.winfo_screenheight()
                root.destroy()
                
                is_fullscreen = (
                    monitor_area['x'] == 0 and 
                    monitor_area['y'] == 0 and 
                    monitor_area['width'] == screen_width and 
                    monitor_area['height'] == screen_height
                )
                
                if is_fullscreen:
                    self.logger.info("使用默认全屏截图模式进行图片匹配")
                    monitor_area_param = None
                else:
                    self.logger.info(f"使用用户指定区域进行图片匹配 - X:{monitor_area['x']}, Y:{monitor_area['y']}, 宽度:{monitor_area['width']}, 高度:{monitor_area['height']}")
                    monitor_area_param = monitor_area
            else:
                self.logger.info("使用默认全屏截图模式进行图片匹配（未配置监控区域）")
                monitor_area_param = None
            
            self.logger.info(f"使用匹配阈值: {similarity_threshold:.2f}")
            
            # 执行图片匹配点击（启用精确匹配功能）
            result = click_service.smart_click_by_image(
                reference_image_path=image_path,
                monitor_area=monitor_area_param,
                max_targets=5,
                similarity_threshold=similarity_threshold,
                use_precise_matching=True
            )
            
            self.logger.info(f"图片参照测试已启用精确匹配功能，提高匹配准确性")
            
            # 处理结果
            if result.get('success'):
                click_details = result.get('click_details', {})
                successful_clicks = click_details.get('successful_clicks', [])
                failed_clicks = click_details.get('failed_clicks', [])
                
                success_count = len(successful_clicks)
                fail_count = len(failed_clicks)
                
                self.logger.info(f"图片匹配测试完成 - 成功点击: {success_count}, 失败: {fail_count}")
                
                if success_count > 0:
                    click_details_list = []
                    for i, click_info in enumerate(successful_clicks[:3]):  # 只显示前3个
                        # 从字典中获取相似度和位置信息
                        target = click_info.get('target')
                        position = click_info.get('position', (0, 0))
                        if target and hasattr(target, 'similarity'):
                            similarity = target.similarity
                        else:
                            similarity = click_info.get('confidence', 0.0)
                        click_details_list.append(f"• 匹配度: {similarity:.2f} at ({position[0]}, {position[1]})")
                    
                    details_text = "\n".join(click_details_list)
                    if success_count > 3:
                        details_text += f"\n... 还有 {success_count - 3} 个匹配点击"
                    
                    self.logger.info(f"图片匹配测试执行完成 - 成功点击: {success_count} 个目标, 失败: {fail_count} 个目标")
                    self.logger.info(f"匹配详情:\n{details_text}")
                else:
                    self.logger.info(f"图片匹配测试执行完成 - 未找到匹配的图片区域")
                    self.logger.info("请检查参照图片或屏幕内容")
            else:
                error_msg = result.get('error', '未知错误')
                self.logger.error(f"图片匹配测试执行失败: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"执行图片参照测试失败: {e}")
    
    def _on_save_log_clicked(self):
        """
        保存日志按钮点击事件
        """
        self.logger.info("用户点击保存日志按钮")
        self.logger.debug("开始执行日志保存流程")
        
        try:
            # 获取当前日志内容
            log_content = self.log_display.toPlainText()
            self.logger.debug(f"获取到日志内容长度: {len(log_content)} 字符")
            
            if not log_content.strip():
                self.logger.warning("日志内容为空，无需保存")
                QMessageBox.information(self, "保存提示", "当前没有日志内容可保存")
                return
            
            # 生成保存文件名和路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"HonyGo_UI_Log_{timestamp}.txt"
            
            # 优先保存到项目日志目录，如果失败则保存到桌面
            try:
                # 确保项目日志目录存在
                project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
                if project_root_env:
                    project_root = Path(project_root_env)
                else:
                    # 备用方案：从当前文件路径计算
                    project_root = Path(__file__).parent.parent.parent.parent
                project_log_dir = project_root / "data" / "logs"
                project_log_dir.mkdir(parents=True, exist_ok=True)
                log_path = project_log_dir / log_filename
                self.logger.debug(f"尝试保存到项目日志目录: {log_path}")
            except Exception as e:
                self.logger.warning(f"无法使用项目日志目录，改为保存到桌面: {e}")
                log_path = Path.home() / "Desktop" / log_filename
                self.logger.debug(f"保存到桌面: {log_path}")
            
            # 保存日志文件
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"HonyGo 界面日志导出\n")
                f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"日志内容长度: {len(log_content)} 字符\n")
                f.write(f"导出路径: {log_path}\n")
                f.write("=" * 60 + "\n\n")
                f.write(log_content)
            
            self.logger.info(f"日志已成功保存到: {log_path}")
            QMessageBox.information(self, "保存成功", f"日志已保存到:\n{log_path}\n\n文件大小: {len(log_content)} 字符")
            
        except Exception as e:
            self.logger.error(f"保存日志失败: {e}")
            QMessageBox.critical(self, "保存失败", f"保存日志失败\n\n错误详情: {str(e)}")
    
    def _on_log_level_changed(self, level):
        """
        日志级别变更事件
        """
        self.logger.info(f"用户修改日志级别筛选: {level}")
        self.logger.debug(f"日志级别筛选已更新，当前筛选级别: {level}")
        # 重新应用筛选
        self._apply_log_filters()
    
    def _on_log_filter_changed(self, text):
        """
        日志筛选文本变更事件（不立即触发筛选）
        """
        # 只记录文本变化，不立即触发筛选
        pass
    
    def _on_log_filter_enter_pressed(self):
        """
        日志筛选回车键事件（触发筛选）
        """
        text = self.log_filter_input.text().strip()
        if text:
            self.logger.info(f"用户按回车键触发日志筛选，关键字: '{text}'")
            self.logger.debug(f"日志筛选功能已启用，筛选关键字长度: {len(text)} 字符")
        else:
            self.logger.info("用户按回车键，筛选关键字为空，默认不筛选")
            self.logger.debug("日志筛选功能已禁用，显示所有日志")
        # 重新应用筛选
        self._apply_log_filters()
    
    # 清空日志功能已删除
    
    def _on_auto_scroll_clicked(self):
        """
        自动滚动按钮点击事件
        """
        try:
            self.auto_scroll_enabled = not self.auto_scroll_enabled
            
            # 更新按钮文本
            if self.auto_scroll_enabled:
                self.auto_scroll_button.setText("停止滚动")
                self.logger.info("日志自动滚动已开启")
                
                # 恢复滚动时，显示所有缓存的日志
                if self.pending_log_entries:
                    for log_entry in self.pending_log_entries:
                        if self._should_show_log_entry(log_entry):
                            # 根据级别设置颜色
                            color_map = {
                                "DEBUG": "#888888",
                                "INFO": "#ffffff",
                                "WARNING": "#ff8800",
                                "ERROR": "#ff4444",
                                "CRITICAL": "#ff0000"
                            }
                            color = color_map.get(log_entry['level'], "#ffffff")
                            
                            self.log_display.setTextColor(color)
                            self.log_display.append(log_entry['formatted_message'])
                    
                    # 清空缓存的日志
                    self.pending_log_entries.clear()
                    
                    # 滚动到底部
                    scrollbar = self.log_display.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())
            else:
                self.auto_scroll_button.setText("恢复滚动")
                self.logger.info("日志自动滚动已停止")
                
        except Exception as e:
            self.logger.error(f"切换自动滚动状态失败: {e}")
    

    # 注意：已移除_poll_ocr_logs方法，OCR日志现在通过统一日志服务直接传递
    
    def closeEvent(self, event):
        """
        窗口关闭事件
        """
        self.logger.info("主界面窗口正在关闭")
        
        try:
            # 1. 停止模拟任务服务
            self.logger.info("正在停止模拟任务服务...")
            if hasattr(self, 'simulation_task_service') and self.simulation_task_service:
                self.simulation_task_service.stop_task()
                self.logger.info("模拟任务服务已停止")
            
            # 2. 停止OCR实例池服务
            self.logger.info("正在停止OCR实例池服务...")
            self._stop_ocr_service_on_exit()
            
            # 3. 停止跨进程日志桥接服务
            self.logger.info("正在停止跨进程日志桥接服务...")
            self._stop_log_bridge_service()
            
            # 4. 清理智能点击服务资源
            self.logger.info("正在清理智能点击服务资源...")
            self._cleanup_smart_click_service()
            
            # 5. 停止日志线程
            if hasattr(self, 'log_thread') and self.log_thread and self.log_thread.isRunning():
                self.logger.info("正在停止日志线程...")
                self.log_thread.stop()
                self.logger.info("日志线程已停止")
            
            self.logger.info("所有资源清理完成")
            
        except Exception as e:
            self.logger.error(f"资源清理过程中发生异常: {e}")
        
        self.logger.info("主界面窗口已关闭")
        event.accept()
    
    def _stop_ocr_service_on_exit(self):
        """
        退出时停止OCR服务
        """
        try:
            # 检查服务是否在运行
            service_running = False
            if requests:
                try:
                    response = requests.get('http://127.0.0.1:8900/health', timeout=2)
                    if response.status_code == 200:
                        service_running = True
                except:
                    pass
            
            if not service_running:
                self.logger.info("OCR实例池服务未运行，无需停止")
                return
            
            # 查找并终止OCR实例池服务进程
            import psutil
            import signal
            
            self.logger.debug("正在查找OCR实例池服务进程")
            terminated_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('ocr_pool_service.py' in str(arg) for arg in cmdline):
                        self.logger.info(f"找到OCR实例池服务进程 PID: {proc.info['pid']}")
                        proc.terminate()
                        terminated_processes.append(proc.info['pid'])
                        
                        # 等待进程优雅退出
                        try:
                            proc.wait(timeout=3)
                            self.logger.info(f"OCR实例池服务进程 {proc.info['pid']} 已优雅退出")
                        except psutil.TimeoutExpired:
                            self.logger.warning(f"OCR实例池服务进程 {proc.info['pid']} 未在超时时间内退出，强制终止")
                            proc.kill()
                            self.logger.info(f"OCR实例池服务进程 {proc.info['pid']} 已强制终止")
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            if terminated_processes:
                self.logger.info(f"已停止 {len(terminated_processes)} 个OCR实例池服务进程")
            else:
                self.logger.info("未找到运行中的OCR实例池服务进程")
                
        except Exception as e:
            self.logger.error(f"停止OCR服务时发生异常: {e}")
    
    def _ensure_ocr_service_ready(self) -> bool:
        """
        确保OCR池服务完全就绪，包括模型加载
        
        Returns:
            bool: 服务是否就绪
        """
        try:
            self.logger.info("检查OCR池服务状态...")
            
            # 检查服务是否运行
            if requests:
                try:
                    response = requests.get('http://127.0.0.1:8900/health', timeout=3)
                    if response.status_code != 200:
                        self.logger.warning("OCR池服务未运行，尝试启动...")
                        self._start_ocr_service_internal()
                        
                        # 等待服务启动
                        import time
                        for i in range(10):  # 最多等待10秒
                            time.sleep(1)
                            try:
                                response = requests.get('http://127.0.0.1:8900/health', timeout=2)
                                if response.status_code == 200:
                                    break
                            except:
                                continue
                        else:
                            self.logger.error("OCR池服务启动超时")
                            return False
                            
                except Exception as e:
                    self.logger.error(f"无法连接OCR池服务: {e}")
                    self.logger.warning("尝试启动OCR池服务...")
                    self._start_ocr_service_internal()
                    
                    # 等待服务启动
                    import time
                    for i in range(15):  # 最多等待15秒
                        time.sleep(1)
                        try:
                            response = requests.get('http://127.0.0.1:8900/health', timeout=2)
                            if response.status_code == 200:
                                break
                        except:
                            continue
                    else:
                        self.logger.error("OCR池服务启动失败")
                        return False
            
            # 检查实例池状态
            try:
                response = requests.get('http://127.0.0.1:8900/status', timeout=5)
                if response.status_code == 200:
                    pool_status = response.json()
                    if pool_status.get('status') == 'success':
                        data = pool_status.get('data', {})
                        running_instances = data.get('running_instances', 0)
                        total_instances = data.get('total_instances', 0)
                        
                        self.logger.info(f"OCR池状态: {running_instances}/{total_instances} 实例运行中")
                        
                        if running_instances > 0:
                            self.logger.info("OCR池服务已就绪")
                            return True
                        else:
                            self.logger.warning("OCR池中没有运行的实例")
                        return False
                else:
                    self.logger.error(f"获取OCR池状态失败: {response.status_code}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"检查OCR池状态失败: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"确保OCR服务就绪时发生异常: {e}")
            return False
    
    def _cleanup_smart_click_service(self):
        """
        清理智能点击服务资源
        """
        try:
            from src.ui.services.smart_click_service import SmartClickService
            
            # 创建临时实例进行清理（如果有全局实例的话）
            temp_service = SmartClickService()
            temp_service.cleanup()
            
            self.logger.info("智能点击服务资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理智能点击服务时发生异常: {e}")


if __name__ == "__main__":
    import signal
    import atexit
    
    # 设置Qt DPI感知模式环境变量（在QApplication创建前）
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
    os.environ['QT_SCALE_FACTOR'] = '1'
    
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 设置Qt DPI感知属性
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 设置应用程序属性
    app.setApplicationName("HonyGo")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Mr.Rey")
    
    # 设置Qt应用程序退出时清理资源
    app.setQuitOnLastWindowClosed(True)
    
    window = None
    
    def cleanup_on_exit():
        """程序退出时的清理函数"""
        if window:
            try:
                window.close()
            except:
                pass
    
    def signal_handler(signum, frame):
        """信号处理函数"""
        cleanup_on_exit()
        app.quit()
    
    # 注册信号处理器和退出清理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(cleanup_on_exit)
    
    try:
        # 创建并显示主窗口
        window = MainWindow()
        window.show()
        
        # 运行应用程序
        exit_code = app.exec()
        
    except Exception as e:
        # 应用程序启动失败时，统一日志服务可能未初始化，使用标准错误输出
        import sys
        try:
            from src.ui.services.logging_service import get_logger
            error_logger = get_logger("MainWindowError", "UI")
            error_logger.error(f"应用程序启动失败: {e}")
        except:
            print(f"应用程序启动失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            exit_code = 1
    
    finally:
        cleanup_on_exit()
    
    sys.exit(exit_code)