#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目构建和依赖检查日志记录服务

@author: Mr.Rey Copyright © 2025

功能:
1. 项目构建过程日志记录
2. 依赖检查和安装日志
3. 环境验证日志记录
4. 构建错误检测和修复
5. 构建性能监控
"""

from datetime import datetime
from importlib.metadata import distributions, version
from pathlib import Path
from typing import Dict, List, Tuple, Any
import importlib
import json
import os
import subprocess
import sys
import time

from dataclasses import dataclass, field
from importlib_metadata import distributions, version
import platform
import psutil

from src.ui.services.logging_service import get_logger















@dataclass
class BuildResult:
    """构建结果数据类"""
    success: bool
    duration: float
    output: str = ""
    error: str = ""
    exit_code: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DependencyInfo:
    """依赖信息数据类"""
    name: str
    version: str = ""
    required_version: str = ""
    installed: bool = False
    compatible: bool = False
    location: str = ""
    error: str = ""


@dataclass
class EnvironmentInfo:
    """环境信息数据类"""
    python_version: str
    platform_info: str
    architecture: str
    cpu_count: int
    memory_total: int
    disk_space: int
    working_directory: str
    python_path: List[str]
    environment_variables: Dict[str, str]


class BuildLoggingService:
    """项目构建和依赖检查日志记录服务"""
    
    # 包名到导入模块名的映射
    PACKAGE_MODULE_MAPPING = {
        'Pillow': 'PIL',
        'opencv-python': 'cv2', 
        'pyyaml': 'yaml',
        'pytest-qt': 'pytestqt',
        'nvidia-ml-py': 'pynvml'
    }
    
    def __init__(self):
        """初始化构建日志服务
        
        @author: Mr.Rey Copyright © 2025
        """
        start_time = time.time()
        
        # 获取项目根目录
        # 优先使用环境变量中的项目根目录路径
        project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
        if project_root_env:
            self.project_root = Path(project_root_env)
        else:
            # 备用方案：从当前文件路径计算
            self.project_root = Path(__file__).parent.parent.parent.parent
        
        # 初始化日志记录器
        self.logger = get_logger("BuildLoggingService", "System")
        self.build_logger = get_logger("BuildProcess", "System")
        self.dependency_logger = get_logger("DependencyCheck", "System")
        self.environment_logger = get_logger("EnvironmentCheck", "System")
        
        # 构建历史记录
        self.build_history: List[BuildResult] = []
        self.dependency_cache: Dict[str, DependencyInfo] = {}
        
        # 记录初始化耗时
        init_duration = time.time() - start_time
        self.logger.info(f"构建日志服务初始化完成，耗时: {init_duration:.3f}秒")
        self.logger.info(f"项目根目录: {self.project_root}")
        
        # 记录系统环境信息
        try:
            env_info = self.log_environment_info()
            self.logger.info(f"系统环境检查完成 - Python: {env_info.python_version}, 平台: {env_info.platform_info}")
        except Exception as e:
            self.logger.error(f"系统环境检查失败: {e}")
    
    def log_environment_info(self) -> EnvironmentInfo:
        """记录环境信息"""
        self.environment_logger.info("开始收集环境信息")
        
        try:
            # 收集系统信息
            env_info = EnvironmentInfo(
                python_version=sys.version,
                platform_info=platform.platform(),
                architecture=platform.architecture()[0],
                cpu_count=psutil.cpu_count(),
                memory_total=psutil.virtual_memory().total // (1024**3),  # GB
                disk_space=psutil.disk_usage(str(self.project_root)).free // (1024**3),  # GB
                working_directory=os.getcwd(),
                python_path=sys.path.copy(),
                environment_variables=dict(os.environ)
            )
            
            # 记录详细环境信息
            self.environment_logger.info(f"Python版本: {env_info.python_version}")
            self.environment_logger.info(f"操作系统: {env_info.platform_info}")
            self.environment_logger.info(f"系统架构: {env_info.architecture}")
            self.environment_logger.info(f"CPU核心数: {env_info.cpu_count}")
            self.environment_logger.info(f"内存总量: {env_info.memory_total}GB")
            self.environment_logger.info(f"可用磁盘空间: {env_info.disk_space}GB")
            self.environment_logger.info(f"工作目录: {env_info.working_directory}")
            
            # 记录关键环境变量
            key_env_vars = ['PYTHONPATH', 'PATH', 'HONYGO_ROOT']
            for var in key_env_vars:
                if var in env_info.environment_variables:
                    self.environment_logger.info(f"环境变量 {var}: {env_info.environment_variables[var]}")
            
            self.environment_logger.info("环境信息收集完成")
            return env_info
            
        except Exception as e:
            self.environment_logger.error(f"收集环境信息失败: {e}")
            raise
    
    def check_python_version(self, min_version: Tuple[int, int] = (3, 8)) -> bool:
        """检查Python版本"""
        self.dependency_logger.info(f"检查Python版本，最低要求: {min_version[0]}.{min_version[1]}")
        
        try:
            current_version = sys.version_info[:2]
            self.dependency_logger.info(f"当前Python版本: {current_version[0]}.{current_version[1]}")
            
            if current_version >= min_version:
                self.dependency_logger.info("Python版本检查通过")
                return True
            else:
                self.dependency_logger.error(
                    f"Python版本不满足要求，当前: {current_version[0]}.{current_version[1]}, "
                    f"最低要求: {min_version[0]}.{min_version[1]}"
                )
                return False
                
        except Exception as e:
            self.dependency_logger.error(f"Python版本检查失败: {e}")
            return False
    
    def check_dependency(self, package_name: str, required_version: str = "") -> DependencyInfo:
        """检查单个依赖包"""
        self.dependency_logger.info(f"检查依赖包: {package_name}")
        
        # 检查缓存
        cache_key = f"{package_name}:{required_version}"
        if cache_key in self.dependency_cache:
            cached_info = self.dependency_cache[cache_key]
            self.dependency_logger.info(f"使用缓存的依赖信息: {package_name}")
            return cached_info
        
        dep_info = DependencyInfo(name=package_name, required_version=required_version)
        
        try:
            # 尝试导入包
            try:
                # 获取实际的导入模块名
                import_name = self.PACKAGE_MODULE_MAPPING.get(package_name, package_name)
                module = importlib.import_module(import_name)
                dep_info.installed = True
                self.dependency_logger.info(f"依赖包 {package_name} 已安装")
                
                # 获取版本信息
                try:
                    if hasattr(module, '__version__'):
                        dep_info.version = module.__version__
                    else:
                        # 尝试通过importlib.metadata获取版本
                        dep_info.version = version(package_name)
                        # 获取包位置
                        for dist in distributions():
                            if dist.metadata['name'].lower() == package_name.lower():
                                dep_info.location = str(dist.locate_file(''))
                                break
                        else:
                            dep_info.location = getattr(module, '__file__', 'unknown')
                    
                    self.dependency_logger.info(f"依赖包 {package_name} 版本: {dep_info.version}")
                    
                    # 检查版本兼容性
                    if required_version:
                        dep_info.compatible = self._check_version_compatibility(
                            dep_info.version, required_version
                        )
                        if dep_info.compatible:
                            self.dependency_logger.info(f"依赖包 {package_name} 版本兼容")
                        else:
                            self.dependency_logger.warning(
                                f"依赖包 {package_name} 版本不兼容，当前: {dep_info.version}, "
                                f"要求: {required_version}"
                            )
                    else:
                        dep_info.compatible = True
                        
                except Exception as ve:
                    self.dependency_logger.warning(f"获取 {package_name} 版本信息失败: {ve}")
                    dep_info.version = "unknown"
                    dep_info.compatible = True  # 无版本要求时默认兼容
                    
            except ImportError as ie:
                dep_info.installed = False
                dep_info.error = str(ie)
                self.dependency_logger.error(f"依赖包 {package_name} 未安装: {ie}")
                
        except Exception as e:
            dep_info.error = str(e)
            self.dependency_logger.error(f"检查依赖包 {package_name} 失败: {e}")
        
        # 缓存结果
        self.dependency_cache[cache_key] = dep_info
        return dep_info
    
    def check_all_dependencies(self, requirements_file: str = "requirements.txt") -> Dict[str, DependencyInfo]:
        """检查所有依赖包
        
        @author: Mr.Rey Copyright © 2025
        """
        start_time = time.time()
        self.dependency_logger.info(f"开始检查所有依赖包，配置文件: {requirements_file}")
        
        dependencies = {}
        requirements_path = self.project_root / requirements_file
        
        try:
            if requirements_path.exists():
                self.dependency_logger.info(f"读取依赖配置文件: {requirements_path}")
                
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 解析依赖包名和版本要求
                        if '>=' in line:
                            package_name, version = line.split('>=')
                            required_version = version.strip()
                        elif '==' in line:
                            package_name, version = line.split('==')
                            required_version = version.strip()
                        else:
                            package_name = line
                            required_version = ""
                        
                        package_name = package_name.strip()
                        dep_info = self.check_dependency(package_name, required_version)
                        dependencies[package_name] = dep_info
            else:
                self.dependency_logger.warning(f"依赖配置文件不存在: {requirements_path}")
                
                # 检查核心依赖
                core_dependencies = [
                    ('PySide6', '6.5.0'),
                    ('easyocr', '1.7.0'),
                    ('opencv-python', '4.8.0'),
                    ('numpy', '1.24.0'),
                    ('Pillow', '10.0.0'),
                    ('psutil', '5.9.0'),
                    ('schedule', '1.2.0'),
                    ('flask', '2.3.0'),
                    ('requests', '2.31.0')
                ]
                
                for package_name, version in core_dependencies:
                    dep_info = self.check_dependency(package_name, version)
                    dependencies[package_name] = dep_info
            
            # 统计检查结果
            check_duration = time.time() - start_time
            total_deps = len(dependencies)
            installed_deps = sum(1 for dep in dependencies.values() if dep.installed)
            compatible_deps = sum(1 for dep in dependencies.values() if dep.compatible)
            
            self.dependency_logger.info(
                f"依赖检查完成，耗时: {check_duration:.3f}秒 - 总计: {total_deps}, 已安装: {installed_deps}, "
                f"版本兼容: {compatible_deps}"
            )
            
            # 记录未安装的依赖
            missing_deps = [name for name, dep in dependencies.items() if not dep.installed]
            if missing_deps:
                self.dependency_logger.error(f"缺失依赖包({len(missing_deps)}个): {', '.join(missing_deps)}")
            
            # 记录版本不兼容的依赖
            incompatible_deps = [
                name for name, dep in dependencies.items() 
                if dep.installed and not dep.compatible
            ]
            if incompatible_deps:
                self.dependency_logger.warning(f"版本不兼容的依赖包({len(incompatible_deps)}个): {', '.join(incompatible_deps)}")
            
            # 更新缓存
            cache_before = len(self.dependency_cache)
            self.dependency_cache.update(dependencies)
            cache_after = len(self.dependency_cache)
            self.dependency_logger.info(f"依赖缓存已更新: {cache_before} -> {cache_after}")
            
            return dependencies
            
        except Exception as e:
            self.dependency_logger.error(f"检查依赖包失败: {e}")
            return {}
    
    def install_missing_dependencies(self, dependencies: Dict[str, DependencyInfo]) -> BuildResult:
        """安装缺失的依赖包"""
        self.build_logger.info("开始安装缺失的依赖包")
        
        start_time = time.time()
        missing_deps = [name for name, dep in dependencies.items() if not dep.installed]
        
        if not missing_deps:
            self.build_logger.info("没有缺失的依赖包需要安装")
            return BuildResult(
                success=True,
                duration=time.time() - start_time,
                output="没有缺失的依赖包"
            )
        
        self.build_logger.info(f"需要安装的依赖包: {', '.join(missing_deps)}")
        
        try:
            # 构建pip安装命令
            cmd = [sys.executable, '-m', 'pip', 'install'] + missing_deps
            self.build_logger.info(f"执行安装命令: {' '.join(cmd)}")
            
            # 执行安装
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=300  # 5分钟超时
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                self.build_logger.info(f"依赖包安装成功，耗时: {duration:.2f}秒")
                self.build_logger.info(f"安装输出: {result.stdout}")
                
                # 清除已安装依赖的缓存，强制重新检查
                self.build_logger.info("清除已安装依赖的缓存")
                cache_keys_to_remove = []
                for cache_key in self.dependency_cache.keys():
                    package_name = cache_key.split(':')[0]
                    if package_name in missing_deps:
                        cache_keys_to_remove.append(cache_key)
                
                for cache_key in cache_keys_to_remove:
                    del self.dependency_cache[cache_key]
                    self.build_logger.info(f"已清除缓存: {cache_key}")
                
                build_result = BuildResult(
                    success=True,
                    duration=duration,
                    output=result.stdout,
                    exit_code=result.returncode
                )
            else:
                self.build_logger.error(f"依赖包安装失败，退出码: {result.returncode}")
                self.build_logger.error(f"错误输出: {result.stderr}")
                
                build_result = BuildResult(
                    success=False,
                    duration=duration,
                    output=result.stdout,
                    error=result.stderr,
                    exit_code=result.returncode
                )
            
            self.build_history.append(build_result)
            return build_result
            
        except subprocess.TimeoutExpired:
            error_msg = "依赖包安装超时"
            self.build_logger.error(error_msg)
            
            build_result = BuildResult(
                success=False,
                duration=time.time() - start_time,
                error=error_msg,
                exit_code=-1
            )
            self.build_history.append(build_result)
            return build_result
            
        except Exception as e:
            error_msg = f"依赖包安装异常: {e}"
            self.build_logger.error(error_msg)
            
            build_result = BuildResult(
                success=False,
                duration=time.time() - start_time,
                error=error_msg,
                exit_code=-1
            )
            self.build_history.append(build_result)
            return build_result
    
    def run_build_command(self, command: List[str], description: str = "") -> BuildResult:
        """执行构建命令
        
        @author: Mr.Rey Copyright © 2025
        """
        desc = description or f"执行命令: {' '.join(command)}"
        self.build_logger.info(f"开始{desc}")
        self.build_logger.info(f"命令详情: {command}")
        self.build_logger.info(f"工作目录: {self.project_root}")
        
        start_time = time.time()
        
        try:
            self.build_logger.info(f"执行命令: {' '.join(command)}")
            self.build_logger.info(f"工作目录: {self.project_root}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=600  # 10分钟超时
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                self.build_logger.info(f"{desc}成功，耗时: {duration:.3f}秒，退出码: {result.returncode}")
                if result.stdout:
                    stdout_lines = len(result.stdout.splitlines())
                    self.build_logger.info(f"命令输出({stdout_lines}行): {result.stdout[:500]}{'...' if len(result.stdout) > 500 else ''}")
                
                build_result = BuildResult(
                    success=True,
                    duration=duration,
                    output=result.stdout,
                    exit_code=result.returncode
                )
                self.build_logger.info(f"构建成功记录已添加到历史")
            else:
                self.build_logger.error(f"{desc}失败，耗时: {duration:.3f}秒，退出码: {result.returncode}")
                if result.stderr:
                    stderr_lines = len(result.stderr.splitlines())
                    self.build_logger.error(f"错误输出({stderr_lines}行): {result.stderr[:500]}{'...' if len(result.stderr) > 500 else ''}")
                if result.stdout:
                    stdout_lines = len(result.stdout.splitlines())
                    self.build_logger.info(f"标准输出({stdout_lines}行): {result.stdout[:500]}{'...' if len(result.stdout) > 500 else ''}")
                
                build_result = BuildResult(
                    success=False,
                    duration=duration,
                    output=result.stdout,
                    error=result.stderr,
                    exit_code=result.returncode
                )
                self.build_logger.error(f"构建失败记录已添加到历史")
            
            self.build_history.append(build_result)
            return build_result
            
        except subprocess.TimeoutExpired:
            error_msg = f"{desc}超时"
            self.build_logger.error(error_msg)
            
            build_result = BuildResult(
                success=False,
                duration=time.time() - start_time,
                error=error_msg,
                exit_code=-1
            )
            self.build_history.append(build_result)
            return build_result
            
        except Exception as e:
            error_msg = f"{desc}异常: {e}"
            self.build_logger.error(error_msg)
            
            build_result = BuildResult(
                success=False,
                duration=time.time() - start_time,
                error=error_msg,
                exit_code=-1
            )
            self.build_history.append(build_result)
            return build_result
    
    def check_project_structure(self) -> bool:
        """检查项目结构
        
        @author: Mr.Rey Copyright © 2025
        """
        start_time = time.time()
        self.build_logger.info("开始检查项目结构")
        self.build_logger.info(f"项目根目录: {self.project_root}")
        
        try:
            # 检查关键目录
            required_dirs = [
                'src',
                'src/ui',
                'src/core',
                'src/config',
                'data/logs',
                'tests',
                'docs'
            ]
            
            missing_dirs = []
            for dir_path in required_dirs:
                full_path = self.project_root / dir_path
                if not full_path.exists():
                    missing_dirs.append(dir_path)
                    self.build_logger.warning(f"缺失目录: {dir_path}")
                else:
                    self.build_logger.info(f"目录存在: {dir_path}")
            
            # 检查关键文件
            required_files = [
                'pyproject.toml',
                'requirements.txt',
                'start_honygo.py',
                'src/ui/main.py'
            ]
            
            missing_files = []
            for file_path in required_files:
                full_path = self.project_root / file_path
                if not full_path.exists():
                    missing_files.append(file_path)
                    self.build_logger.warning(f"缺失文件: {file_path}")
                else:
                    self.build_logger.info(f"文件存在: {file_path}")
            
            # 记录检查结果
            check_duration = time.time() - start_time
            
            if missing_dirs or missing_files:
                self.build_logger.error(
                    f"项目结构检查失败，耗时: {check_duration:.3f}秒 - 缺失目录({len(missing_dirs)}个): {missing_dirs}, 缺失文件({len(missing_files)}个): {missing_files}"
                )
                return False
            else:
                self.build_logger.info(
                    f"项目结构检查通过，耗时: {check_duration:.3f}秒 - 检查了{len(required_dirs)}个目录和{len(required_files)}个文件"
                )
                return True
                
        except Exception as e:
            self.build_logger.error(f"项目结构检查异常: {e}")
            return False
    
    def generate_build_report(self) -> Dict[str, Any]:
        """生成构建报告
        
        @author: Mr.Rey Copyright © 2025
        """
        start_time = time.time()
        self.logger.info("开始生成构建报告")
        
        try:
            # 统计构建历史
            total_builds = len(self.build_history)
            successful_builds = sum(1 for build in self.build_history if build.success)
            failed_builds = total_builds - successful_builds
            
            # 计算平均构建时间
            if self.build_history:
                avg_duration = sum(build.duration for build in self.build_history) / total_builds
                max_duration = max(build.duration for build in self.build_history)
                min_duration = min(build.duration for build in self.build_history)
            else:
                avg_duration = max_duration = min_duration = 0
            
            # 统计依赖信息
            total_deps = len(self.dependency_cache)
            installed_deps = sum(1 for dep in self.dependency_cache.values() if dep.installed)
            compatible_deps = sum(1 for dep in self.dependency_cache.values() if dep.compatible)
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'project_root': str(self.project_root),
                'build_statistics': {
                    'total_builds': total_builds,
                    'successful_builds': successful_builds,
                    'failed_builds': failed_builds,
                    'success_rate': (successful_builds / total_builds * 100) if total_builds > 0 else 0,
                    'average_duration': avg_duration,
                    'max_duration': max_duration,
                    'min_duration': min_duration
                },
                'dependency_statistics': {
                    'total_dependencies': total_deps,
                    'installed_dependencies': installed_deps,
                    'compatible_dependencies': compatible_deps,
                    'installation_rate': (installed_deps / total_deps * 100) if total_deps > 0 else 0,
                    'compatibility_rate': (compatible_deps / total_deps * 100) if total_deps > 0 else 0
                },
                'recent_builds': [
                    {
                        'timestamp': build.timestamp.isoformat(),
                        'success': build.success,
                        'duration': build.duration,
                        'exit_code': build.exit_code,
                        'has_error': bool(build.error)
                    }
                    for build in self.build_history[-10:]  # 最近10次构建
                ],
                'dependency_details': {
                    name: {
                        'installed': dep.installed,
                        'version': dep.version,
                        'required_version': dep.required_version,
                        'compatible': dep.compatible,
                        'has_error': bool(dep.error)
                    }
                    for name, dep in self.dependency_cache.items()
                }
            }
            
            # 记录报告生成耗时
            report_duration = time.time() - start_time
            report['generation_info'] = {
                'generation_time': datetime.now().isoformat(),
                'generation_duration': report_duration,
                'report_size_kb': len(str(report)) / 1024
            }
            
            self.logger.info(
                f"构建报告生成完成，耗时: {report_duration:.3f}秒，报告大小: {report['generation_info']['report_size_kb']:.2f}KB"
            )
            return report
            
        except Exception as e:
            generation_duration = time.time() - start_time
            self.logger.error(f"生成构建报告失败，耗时: {generation_duration:.3f}秒，错误: {e}")
            return {}
    
    def save_build_report(self, report: Dict[str, Any], filename: str = None) -> bool:
        """保存构建报告"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"build_report_{timestamp}.json"
            
            report_path = self.project_root / "data" / "logs" / filename
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"构建报告已保存: {report_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存构建报告失败: {e}")
            return False
    
    def _check_version_compatibility(self, current_version: str, required_version: str) -> bool:
        """检查版本兼容性"""
        try:
            # 简单的版本比较，支持 >= 格式
            current_parts = [int(x) for x in current_version.split('.') if x.isdigit()]
            required_parts = [int(x) for x in required_version.split('.') if x.isdigit()]
            
            # 补齐版本号长度
            max_len = max(len(current_parts), len(required_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            required_parts.extend([0] * (max_len - len(required_parts)))
            
            return current_parts >= required_parts
            
        except Exception:
            # 版本比较失败时默认兼容
            return True
    
    def cleanup(self):
        """清理资源"""
        self.logger.info("构建日志服务清理资源")
        self.build_history.clear()
        self.dependency_cache.clear()


# 全局实例
_build_logging_service = None


def get_build_logging_service() -> BuildLoggingService:
    """获取构建日志服务实例"""
    global _build_logging_service
    if _build_logging_service is None:
        _build_logging_service = BuildLoggingService()
    return _build_logging_service


def cleanup_build_logging_service():
    """清理构建日志服务"""
    global _build_logging_service
    if _build_logging_service is not None:
        _build_logging_service.cleanup()
        _build_logging_service = None