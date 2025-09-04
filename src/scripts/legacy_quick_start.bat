@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo [已弃用] OCR优化系统快速启动脚本
echo @author: Mr.Rey Copyright © 2025
echo ========================================
echo.
echo 警告: 此脚本已被弃用！
echo 请使用新的统一启动方式:
echo   cd ..\..\
echo   python start_honygo.py
echo 或者:
echo   cd ..\..\
echo   start_honygo.bat
echo.
echo 按任意键继续使用旧脚本，或按Ctrl+C退出...
pause >nul
echo.
echo ========================================
echo 继续使用遗留启动脚本
echo ========================================

:: 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python环境，请先安装Python 3.8+
    pause
    exit /b 1
)

:: 切换到脚本目录
cd /d "%~dp0"

:: 检查必要文件
if not exist "ocr_pool_service.py" (
    echo 错误: 未找到ocr_pool_service.py文件
    pause
    exit /b 1
)

if not exist "core\ocr\scripts\start_optimized_ocr_system.py" (
echo 错误: 未找到core\ocr\scripts\start_optimized_ocr_system.py文件
    pause
    exit /b 1
)

:: 检查配置文件
set CONFIG_FILE=config\ocr_system_config.json
if not exist "%CONFIG_FILE%" (
    echo 警告: 未找到配置文件，将使用默认配置
    set CONFIG_PARAM=
) else (
    echo 使用配置文件: %CONFIG_FILE%
    set CONFIG_PARAM=--config "%CONFIG_FILE%"
)

:: 显示启动选项
echo.
echo 请选择启动模式:
echo 1. 完整模式 (OCR池 + 性能监控 + Web界面)
echo 2. 基础模式 (仅OCR池服务)
echo 3. 测试模式 (完整模式 + 性能测试)
echo 4. 自定义模式
echo 0. 退出
echo.
set /p choice=请输入选择 (1-4, 0): 

if "%choice%"=="0" exit /b 0
if "%choice%"=="1" goto full_mode
if "%choice%"=="2" goto basic_mode
if "%choice%"=="3" goto test_mode
if "%choice%"=="4" goto custom_mode

echo 无效选择，使用完整模式
goto full_mode

:full_mode
echo.
echo 启动完整模式...
echo 包含: OCR池服务 + 性能监控 + Web监控界面
echo.
python core\ocr\start_optimized_ocr_system.py %CONFIG_PARAM%
goto end

:basic_mode
echo.
echo 启动基础模式...
echo 包含: 仅OCR池服务
echo.
python core\ocr\start_optimized_ocr_system.py %CONFIG_PARAM% --no-monitoring --no-dashboard
goto end

:test_mode
echo.
echo 启动测试模式...
echo 包含: 完整功能 + 性能测试
echo.
python core\ocr\start_optimized_ocr_system.py %CONFIG_PARAM% --test
goto end

:custom_mode
echo.
echo 自定义模式配置:
echo.
set /p host=OCR服务主机 (默认: 127.0.0.1): 
if "%host%"=="" set host=127.0.0.1

set /p port=OCR服务端口 (默认: 8900):
if "%port%"=="" set port=8900

set /p min_inst=最小实例数 (默认: 2): 
if "%min_inst%"=="" set min_inst=2

set /p max_inst=最大实例数 (默认: 8): 
if "%max_inst%"=="" set max_inst=8

set /p dash_port=监控界面端口 (默认: 8081): 
if "%dash_port%"=="" set dash_port=8081

echo.
echo 是否启用以下功能? (y/n)
set /p enable_monitor=性能监控 (y): 
if "%enable_monitor%"=="" set enable_monitor=y

set /p enable_dash=Web界面 (y): 
if "%enable_dash%"=="" set enable_dash=y

set /p enable_cache=缓存功能 (y): 
if "%enable_cache%"=="" set enable_cache=y

set /p enable_scale=自动扩容 (y): 
if "%enable_scale%"=="" set enable_scale=y

set /p run_test=运行测试 (n): 
if "%run_test%"=="" set run_test=n

:: 构建启动参数
set CUSTOM_PARAMS=%CONFIG_PARAM% --host %host% --port %port% --min-instances %min_inst% --max-instances %max_inst% --dashboard-port %dash_port%

if /i "%enable_monitor%"=="n" set CUSTOM_PARAMS=%CUSTOM_PARAMS% --no-monitoring
if /i "%enable_dash%"=="n" set CUSTOM_PARAMS=%CUSTOM_PARAMS% --no-dashboard
if /i "%enable_cache%"=="n" set CUSTOM_PARAMS=%CUSTOM_PARAMS% --no-cache
if /i "%enable_scale%"=="n" set CUSTOM_PARAMS=%CUSTOM_PARAMS% --no-scaling
if /i "%run_test%"=="y" set CUSTOM_PARAMS=%CUSTOM_PARAMS% --test

echo.
echo 启动自定义模式...
echo 参数: %CUSTOM_PARAMS%
echo.
python core\ocr\start_optimized_ocr_system.py %CUSTOM_PARAMS%
goto end

:end
echo.
echo 系统已停止运行
pause