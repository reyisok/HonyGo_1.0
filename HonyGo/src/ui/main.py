#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HonyGo UI Main Entry Point

@author: Mr.Rey Copyright © 2025
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
if project_root_env:
    project_root = Path(project_root_env)
else:
    # 备用方案：从当前文件路径计算
    project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入主窗口
from src.ui.windows.main_window import MainWindow
from src.ui.services.logging_service import get_logger

def main():
    """
    主程序入口点
    """
    logger = get_logger("UIMain", "Application")
    logger.info("启动HonyGo UI主程序")
    
    try:
        # 设置环境变量（如果尚未设置）
        if 'HONYGO_PROJECT_ROOT' not in os.environ:
            os.environ['HONYGO_PROJECT_ROOT'] = str(project_root)
        
        # 创建并运行主窗口
        import sys
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        
        # 创建应用程序实例
        app = QApplication(sys.argv)
        app.setApplicationName("HonyGo")
        app.setApplicationVersion("1.0.0")
        
        # 设置高DPI支持
        app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        
        # 创建主窗口
        window = MainWindow()
        window.show()
        
        logger.info("HonyGo UI主程序启动完成")
        
        # 运行应用程序
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"启动HonyGo UI主程序失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()