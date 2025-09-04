#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HonyGo 统一启动脚本

负责整个HonyGo应用程序的启动、进程管理、状态监控和资源清理。
提供统一的启动入口和完整的生命周期管理。

@author: Mr.Rey Copyright © 2025
@created: 2025-01-03 03:37:00
@modified: 2025-01-03 03:37:00
@version: 1.0.0
"""

from datetime import datetime
from pathlib import Path
import argparse
import os
import subprocess
import sys
import threading
import time
import traceback

import signal
import psutil

# 在导入任何项目模块之前，先设置项目根目录环境变量和Python路径
# 这确保所有模块在初始化时都能获得正确的项目根目录路径
script_path = Path(__file__).resolve()
project_root = script_path.parent
os.environ['HONYGO_PROJECT_ROOT'] = str(project_root)

# 将项目根目录添加到Python路径，确保模块可以正确导入
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.services.service_registry import auto_register_all_services
from src.core.services.startup_monitoring_service import StartupPhase, get_startup_monitoring_service
from src.core.services.system_manager_service import get_system_manager_service
from src.core.services.unified_config_service import get_config_service
from src.ui.services.logging_service import get_logger


class HonyGoLauncher:
    """
    HonyGo应用程序启动器
    
    负责应用程序的完整生命周期管理，包括：
    - 环境检查和初始化
    - 服务注册和启动
    - 进程监控和管理
    - 资源清理和关闭
    """
    
    def __init__(self):
        """初始化启动器"""
        self.logger = None
        self.startup_monitoring = None
        self.system_manager = None
        self.config_service = None
        self.main_process = None
        self.startup_success = False
        self.shutdown_requested = False
        self.monitoring_thread = None
        
        # 初始化基础服务
        self._init_basic_services()
    
    def _init_basic_services(self):
        """初始化基础服务"""
        try:
            # 初始化日志服务
            self.logger = get_logger("HonyGoLauncher")
            self.logger.info("HonyGo启动器初始化开始")
            
            # 初始化配置服务
            self.config_service = get_config_service()
            
            # 初始化启动监控服务
            self.startup_monitoring = get_startup_monitoring_service()
            
            # 初始化系统管理服务
            self.system_manager = get_system_manager_service()
            
            self.logger.info("基础服务初始化完成")
            
        except Exception as e:
            error_message = f"基础服务初始化失败: {str(e)}"
            print(f"[错误] {error_message}")
            
            traceback_info = traceback.format_exc()
            print(f"[详细] {traceback_info}")
            
            if self.logger:
                self.logger.error(error_message)
                self.logger.error(f"异常详情: {traceback_info}")
            
            raise
    
    def check_environment(self) -> bool:
        """检查运行环境"""
        try:
            self.logger.info("开始环境检查")
            self.startup_monitoring.start_phase(StartupPhase.INITIALIZATION, "环境检查阶段")
            
            # 检查Python版本
            python_version = sys.version_info
            if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
                raise RuntimeError(f"Python版本过低: {python_version.major}.{python_version.minor}, 需要3.8+")
            
            self.logger.info(f"Python版本检查通过: {python_version.major}.{python_version.minor}.{python_version.micro}")
            
            # 获取已设置的项目根目录路径
            project_root = Path(os.environ['HONYGO_PROJECT_ROOT'])
            
            # 验证项目根目录结构
            if not (project_root / "src").exists():
                raise RuntimeError(f"项目结构异常: 未找到src目录 - {project_root}")
            
            # 确保项目根目录路径正确
            script_path = project_root / "start_honygo.py"
            if not script_path.exists():
                raise RuntimeError(f"启动脚本路径异常: {script_path}")
            
            self.logger.info(f"项目根目录验证通过: {project_root}")
            self.logger.info(f"启动脚本路径: {script_path}")
            
            # 检查必要的目录
            required_dirs = [
                "src/config",
                "src/core",
                "src/ui",
                "data/logs"
            ]
            
            for dir_path in required_dirs:
                full_path = project_root / dir_path
                if not full_path.exists():
                    self.logger.warning(f"创建缺失目录: {full_path}")
                    full_path.mkdir(parents=True, exist_ok=True)
            
            # 完成初始化阶段
            self.startup_monitoring.complete_phase(StartupPhase.INITIALIZATION)
            self.logger.info("环境检查完成")
            return True
            
        except Exception as e:
            error_message = f"环境检查失败: {str(e)}"
            self.logger.error(error_message)
            self.logger.error(f"异常详情: {traceback.format_exc()}")
            self.startup_monitoring.fail_phase(StartupPhase.INITIALIZATION, error_message)
            return False
    
    def load_configuration(self) -> bool:
        """加载配置"""
        try:
            self.logger.info("开始配置加载")
            self.startup_monitoring.start_phase(StartupPhase.CONFIG_LOADING, "配置加载阶段")
            
            # 这里可以添加具体的配置加载逻辑
            # 目前配置服务已在基础服务初始化中完成
            
            self.startup_monitoring.complete_phase(StartupPhase.CONFIG_LOADING)
            self.logger.info("配置加载完成")
            return True
            
        except Exception as e:
            error_message = f"配置加载失败: {str(e)}"
            self.logger.error(error_message)
            self.logger.error(f"异常详情: {traceback.format_exc()}")
            self.startup_monitoring.fail_phase(StartupPhase.CONFIG_LOADING, error_message)
            return False
    
    def check_existing_processes(self) -> bool:
        """检查是否存在重复进程"""
        try:
            self.logger.info("检查现有进程")
            
            current_pid = os.getpid()
            process_name = "python"
            script_name = "start_honygo.py"
            
            existing_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and process_name in proc.info['name'].lower():
                        cmdline = proc.info['cmdline']
                        if cmdline and any(script_name in arg for arg in cmdline):
                            if proc.info['pid'] != current_pid:
                                existing_processes.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if existing_processes:
                self.logger.warning(f"发现重复进程: {existing_processes}")
                
                # 尝试终止重复进程
                for pid in existing_processes:
                    try:
                        proc = psutil.Process(pid)
                        proc.terminate()
                        proc.wait(timeout=5)
                        self.logger.info(f"成功终止重复进程: {pid}")
                    except Exception as e:
                        self.logger.error(f"终止进程{pid}失败: {str(e)}")
            
            return True
            
        except Exception as e:
            error_message = f"进程检查失败: {str(e)}"
            self.logger.error(error_message)
            self.logger.error(f"异常详情: {traceback.format_exc()}")
            return False
    
    def register_services(self) -> bool:
        """注册所有服务"""
        try:
            self.logger.info("开始服务注册")
            self.startup_monitoring.start_phase(StartupPhase.SERVICE_REGISTRATION, "服务注册阶段")
            
            # 自动注册所有服务
            auto_register_all_services()
            
            # 完成服务注册阶段
            self.startup_monitoring.complete_phase(StartupPhase.SERVICE_REGISTRATION)
            self.logger.info("服务注册完成")
            return True
            
        except Exception as e:
            error_message = f"服务注册失败: {str(e)}"
            self.logger.error(error_message)
            self.logger.error(f"异常详情: {traceback.format_exc()}")
            self.startup_monitoring.fail_phase(StartupPhase.SERVICE_REGISTRATION, error_message)
            return False
    
    def initialize_services(self) -> bool:
        """初始化服务"""
        try:
            self.logger.info("开始服务初始化")
            self.startup_monitoring.start_phase(StartupPhase.SERVICE_INITIALIZATION, "服务初始化阶段")
            
            # 这里可以添加具体的服务初始化逻辑
            # 目前服务初始化在服务注册时已完成
            
            self.startup_monitoring.complete_phase(StartupPhase.SERVICE_INITIALIZATION)
            self.logger.info("服务初始化完成")
            return True
            
        except Exception as e:
            error_message = f"服务初始化失败: {str(e)}"
            self.logger.error(error_message)
            self.logger.error(f"异常详情: {traceback.format_exc()}")
            self.startup_monitoring.fail_phase(StartupPhase.SERVICE_INITIALIZATION, error_message)
            return False
    
    def start_main_application(self) -> bool:
        """启动主应用程序"""
        try:
            self.logger.info("启动主应用程序")
            self.startup_monitoring.start_phase(StartupPhase.SERVICE_STARTUP, "应用程序启动阶段")
            
            # 获取项目根目录
            project_root = Path(os.environ.get('HONYGO_PROJECT_ROOT', Path(__file__).resolve().parent))
            
            # 启动主界面
            main_script = project_root / "src" / "ui" / "windows" / "main_window.py"
            if not main_script.exists():
                raise FileNotFoundError(f"主程序文件不存在: {main_script}")
            
            # 设置环境变量，确保能找到src模块
            env = os.environ.copy()
            env['PYTHONPATH'] = str(project_root)
            
            # 设置DPI相关环境变量，确保高DPI支持
            env['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
            env['QT_SCALE_FACTOR'] = '1'
            env['QT_ENABLE_HIGHDPI_SCALING'] = '1'
            
            # 使用subprocess启动主程序
            self.main_process = subprocess.Popen(
                [sys.executable, str(main_script)],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            self.logger.info(f"主程序已启动，PID: {self.main_process.pid}")
            
            # 等待一段时间确认启动成功
            time.sleep(3)
            
            if self.main_process.poll() is None:
                self.startup_success = True
                self.startup_monitoring.complete_phase(StartupPhase.SERVICE_STARTUP)
                self.logger.info("主应用程序启动成功")
                return True
            else:
                stdout, stderr = self.main_process.communicate()
                error_msg = f"主程序启动失败，退出码: {self.main_process.returncode}"
                if stderr:
                    error_msg += f"\n错误输出: {stderr}"
                raise RuntimeError(error_msg)
            
        except Exception as e:
            error_message = f"主应用程序启动失败: {str(e)}"
            self.logger.error(error_message)
            self.logger.error(f"异常详情: {traceback.format_exc()}")
            self.startup_monitoring.fail_phase(StartupPhase.SERVICE_STARTUP, error_message)
            return False
    
    def initialize_ui(self) -> bool:
        """初始化UI"""
        try:
            self.logger.info("开始UI初始化")
            self.startup_monitoring.start_phase(StartupPhase.UI_INITIALIZATION, "UI初始化阶段")
            
            # UI初始化已在start_main_application中完成
            # 这里可以添加额外的UI初始化逻辑
            
            self.startup_monitoring.complete_phase(StartupPhase.UI_INITIALIZATION)
            self.logger.info("UI初始化完成")
            return True
            
        except Exception as e:
            error_message = f"UI初始化失败: {str(e)}"
            self.logger.error(error_message)
            self.logger.error(f"异常详情: {traceback.format_exc()}")
            self.startup_monitoring.fail_phase(StartupPhase.UI_INITIALIZATION, error_message)
            return False
    
    def final_validation(self) -> bool:
        """最终验证"""
        try:
            self.logger.info("开始最终验证")
            self.startup_monitoring.start_phase(StartupPhase.FINAL_VALIDATION, "最终验证阶段")
            
            # 验证主进程是否正常运行
            if self.main_process and self.main_process.poll() is None:
                self.logger.info("主进程运行正常")
            else:
                raise RuntimeError("主进程未正常运行")
            
            # 验证启动成功标志
            if not self.startup_success:
                raise RuntimeError("启动成功标志未设置")
            
            self.startup_monitoring.complete_phase(StartupPhase.FINAL_VALIDATION)
            self.logger.info("最终验证完成")
            return True
            
        except Exception as e:
            error_message = f"最终验证失败: {str(e)}"
            self.logger.error(error_message)
            self.logger.error(f"异常详情: {traceback.format_exc()}")
            self.startup_monitoring.fail_phase(StartupPhase.FINAL_VALIDATION, error_message)
            return False
    
    def start_monitoring(self):
        """启动进程监控"""
        def monitor_process():
            """监控主进程状态"""
            while not self.shutdown_requested and self.startup_success:
                try:
                    if self.main_process and self.main_process.poll() is not None:
                        self.logger.error(f"主进程异常退出，退出码: {self.main_process.returncode}")
                        
                        # 获取进程输出
                        try:
                            stdout, stderr = self.main_process.communicate(timeout=1)
                            if stderr:
                                self.logger.error(f"主进程错误输出: {stderr}")
                        except subprocess.TimeoutExpired:
                            pass
                        
                        self.startup_success = False
                        break
                    
                    time.sleep(3)  # 每3秒检查一次
                    
                except Exception as e:
                    self.logger.error(f"进程监控异常: {str(e)}")
                    time.sleep(5)
        
        if not self.monitoring_thread or not self.monitoring_thread.is_alive():
            self.monitoring_thread = threading.Thread(target=monitor_process, daemon=True)
            self.monitoring_thread.start()
            self.logger.info("进程监控已启动")
    
    def cleanup_processes(self):
        """清理所有进程"""
        try:
            self.logger.info("开始清理进程")
            
            if self.main_process:
                try:
                    if self.main_process.poll() is None:
                        self.logger.info("终止主进程")
                        self.main_process.terminate()
                        self.main_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.logger.warning("主进程未响应终止信号，强制杀死")
                    self.main_process.kill()
                except Exception as e:
                    self.logger.error(f"终止主进程失败: {str(e)}")
            
            self.logger.info("进程清理完成")
            
        except Exception as e:
            self.logger.error(f"进程清理异常: {str(e)}")
    
    def shutdown(self):
        """关闭应用程序"""
        try:
            self.logger.info("开始关闭HonyGo应用程序")
            self.shutdown_requested = True
            
            # 清理进程
            self.cleanup_processes()
            
            # 等待监控线程结束
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
            
            self.logger.info("HonyGo应用程序已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭应用程序异常: {str(e)}")
    
    def run(self) -> bool:
        """运行启动流程"""
        try:
            self.logger.info("="*50)
            self.logger.info("HonyGo应用程序启动")
            self.logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info("="*50)
            
            # 1. 环境检查 (INITIALIZATION阶段)
            if not self.check_environment():
                return False
            
            # 2. 配置加载 (CONFIG_LOADING阶段)
            if not self.load_configuration():
                return False
            
            # 3. 检查重复进程
            if not self.check_existing_processes():
                return False
            
            # 4. 服务注册 (SERVICE_REGISTRATION阶段)
            if not self.register_services():
                return False
            
            # 5. 服务初始化 (SERVICE_INITIALIZATION阶段)
            if not self.initialize_services():
                return False
            
            # 6. 启动主应用程序 (SERVICE_STARTUP阶段)
            if not self.start_main_application():
                return False
            
            # 7. UI初始化 (UI_INITIALIZATION阶段)
            if not self.initialize_ui():
                return False
            
            # 8. 最终验证 (FINAL_VALIDATION阶段)
            if not self.final_validation():
                return False
            
            # 9. 启动监控
            self.start_monitoring()
            
            # 开始完成阶段
            self.startup_monitoring.start_phase(StartupPhase.COMPLETED, "启动流程完成")
            
            # 完成启动
            self.startup_monitoring.complete_phase(StartupPhase.COMPLETED)
            
            # 强制生成启动报告
            report = self.startup_monitoring.generate_startup_report()
            self.startup_monitoring.save_startup_report(report)
            
            self.logger.info("HonyGo应用程序启动完成")
            return True
            
        except Exception as e:
            error_message = f"启动流程异常: {str(e)}"
            self.logger.error(error_message)
            self.logger.error(f"异常详情: {traceback.format_exc()}")
            return False
        
        finally:
            if not self.startup_success:
                self.cleanup_processes()


def setup_signal_handlers(launcher: HonyGoLauncher):
    """
    设置信号处理器
    
    Args:
        launcher: HonyGo启动器实例
    """
    def signal_handler(signum, frame):
        print(f"\n收到信号 {signum}，正在关闭应用程序...")
        launcher.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def parse_arguments():
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(
        description="HonyGo统一启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python start_honygo.py              # 正常启动
  python start_honygo.py --debug      # 调试模式启动
  python start_honygo.py --no-monitor # 不启动进程监控
        """
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="禁用进程监控"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="设置日志级别"
    )
    
    return parser.parse_args()


def main():
    """
    主函数
    """
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 创建启动器
        launcher = HonyGoLauncher()
        
        # 设置信号处理器
        setup_signal_handlers(launcher)
        
        # 运行启动流程
        success = launcher.run()
        
        if success:
            print("HonyGo应用程序启动成功！")
            print("按 Ctrl+C 退出程序")
            
            # 主循环 - 保持程序运行
            try:
                while launcher.startup_success and not launcher.shutdown_requested:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n用户中断，正在关闭...")
            
        else:
            print("HonyGo应用程序启动失败！")
            return 1
    
    except Exception as e:
        print(f"启动脚本异常: {str(e)}")
        print(f"详细信息: {traceback.format_exc()}")
        return 1
    
    finally:
        if 'launcher' in locals():
            launcher.shutdown()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())