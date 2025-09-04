#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR性能监控Web界面
提供实时性能监控、报告查看和系统控制功能

@author: Mr.Rey Copyright © 2025
"""

from datetime import datetime

from flask import (
    Flask,
    jsonify,
    render_template_string,
    request
)

from src.core.ocr.monitoring.performance_monitor import PerformanceMonitor
from src.ui.services.logging_service import get_logger
















class PerformanceDashboard:
    """
    OCR性能监控Web界面
    """
    
    def __init__(self, monitor: PerformanceMonitor, host: str = '127.0.0.1', port: int = 8081):
        """
        初始化性能监控界面
        
        Args:
            monitor: 性能监控实例
            host: 服务主机
            port: 服务端口
        """
        self.logger = get_logger("PerformanceDashboard", "Application")
        self.monitor = monitor
        self.host = host
        self.port = port
        
        # 创建Flask应用
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'ocr_performance_dashboard_2025'
        
        # 注册路由
        self._register_routes()
        
        self.logger.info(f"性能监控界面初始化完成，地址: http://{host}:{port}")
    
    def _register_routes(self):
        """注册Web路由"""
        
        @self.app.route('/')
        def dashboard():
            """主监控界面"""
            return render_template_string(self._get_dashboard_template())
        
        @self.app.route('/api/status')
        def get_status():
            """获取监控状态"""
            try:
                status = self.monitor.get_current_status()
                return jsonify({
                    'success': True,
                    'data': status
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/metrics')
        def get_metrics():
            """获取实时性能指标"""
            try:
                # 获取最近的指标数据
                limit = request.args.get('limit', 100, type=int)
                metrics_data = list(self.monitor.metrics_history)[-limit:]
                
                # 转换为JSON格式
                metrics_json = []
                for metric in metrics_data:
                    metrics_json.append({
                        'timestamp': metric.timestamp,
                        'datetime': datetime.fromtimestamp(metric.timestamp).isoformat(),
                        'cpu_usage': metric.cpu_usage,
                        'memory_usage': metric.memory_usage,
                        'gpu_usage': metric.gpu_usage,
                        'gpu_memory_usage': metric.gpu_memory_usage,
                        'response_time': metric.response_time,
                        'throughput': metric.throughput,
                        'error_rate': metric.error_rate,
                        'cache_hit_rate': metric.cache_hit_rate,
                        'active_instances': metric.active_instances,
                        'queue_length': metric.queue_length
                    })
                
                return jsonify({
                    'success': True,
                    'data': metrics_json
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/optimizations')
        def get_optimizations():
            """获取优化历史"""
            try:
                limit = request.args.get('limit', 50, type=int)
                optimizations = list(self.monitor.optimization_history)[-limit:]
                
                optimizations_json = []
                for opt in optimizations:
                    optimizations_json.append({
                        'timestamp': opt.timestamp,
                        'datetime': datetime.fromtimestamp(opt.timestamp).isoformat(),
                        'action_type': opt.action_type,
                        'description': opt.description,
                        'parameters': opt.parameters,
                        'expected_improvement': opt.expected_improvement,
                        'actual_result': opt.actual_result
                    })
                
                return jsonify({
                    'success': True,
                    'data': optimizations_json
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/report')
        def generate_report():
            """生成性能报告"""
            try:
                hours = request.args.get('hours', 24, type=int)
                report = self.monitor.get_performance_report(hours=hours)
                
                return jsonify({
                    'success': True,
                    'data': report
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/report/save', methods=['POST'])
        def save_report():
            """保存性能报告"""
            try:
                data = request.get_json()
                hours = data.get('hours', 24)
                filename = data.get('filename')
                
                report = self.monitor.get_performance_report(hours=hours)
                report_path = self.monitor.save_report(report, filename)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'report_path': report_path,
                        'message': '报告保存成功'
                    }
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/control/start', methods=['POST'])
        def start_monitoring():
            """启动监控"""
            try:
                self.monitor.start_monitoring()
                return jsonify({
                    'success': True,
                    'message': '监控已启动'
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/control/stop', methods=['POST'])
        def stop_monitoring():
            """停止监控"""
            try:
                self.monitor.stop_monitoring()
                return jsonify({
                    'success': True,
                    'message': '监控已停止'
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/control/toggle-auto-optimize', methods=['POST'])
        def toggle_auto_optimize():
            """切换自动优化"""
            try:
                self.monitor.auto_optimize = not self.monitor.auto_optimize
                return jsonify({
                    'success': True,
                    'data': {
                        'auto_optimize': self.monitor.auto_optimize,
                        'message': f'自动优化已{"启用" if self.monitor.auto_optimize else "禁用"}'
                    }
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/thresholds', methods=['GET', 'POST'])
        def manage_thresholds():
            """管理性能阈值"""
            if request.method == 'GET':
                return jsonify({
                    'success': True,
                    'data': self.monitor.thresholds
                })
            
            try:
                data = request.get_json()
                for key, value in data.items():
                    if key in self.monitor.thresholds:
                        self.monitor.thresholds[key] = float(value)
                
                return jsonify({
                    'success': True,
                    'data': self.monitor.thresholds,
                    'message': '阈值更新成功'
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def _get_dashboard_template(self) -> str:
        """获取监控界面HTML模板"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCR性能监控界面</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
            font-weight: 300;
        }
        
        .status-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 15px;
            background: rgba(52, 152, 219, 0.1);
            border-radius: 20px;
            border: 1px solid rgba(52, 152, 219, 0.3);
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #e74c3c;
        }
        
        .status-indicator.active {
            background: #27ae60;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .controls {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn-primary {
            background: #3498db;
            color: white;
        }
        
        .btn-success {
            background: #27ae60;
            color: white;
        }
        
        .btn-danger {
            background: #e74c3c;
            color: white;
        }
        
        .btn-warning {
            background: #f39c12;
            color: white;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        
        .card h3 {
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.3em;
            font-weight: 500;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin-bottom: 15px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .metric-item {
            text-align: center;
            padding: 15px;
            background: rgba(52, 152, 219, 0.1);
            border-radius: 10px;
            border: 1px solid rgba(52, 152, 219, 0.2);
        }
        
        .metric-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        
        .metric-label {
            font-size: 0.9em;
            color: #7f8c8d;
        }
        
        .optimization-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .optimization-item {
            padding: 10px;
            margin-bottom: 10px;
            background: rgba(46, 204, 113, 0.1);
            border-radius: 8px;
            border-left: 4px solid #2ecc71;
        }
        
        .optimization-item.error {
            background: rgba(231, 76, 60, 0.1);
            border-left-color: #e74c3c;
        }
        
        .optimization-time {
            font-size: 0.8em;
            color: #7f8c8d;
            margin-bottom: 5px;
        }
        
        .optimization-desc {
            font-weight: 500;
            margin-bottom: 3px;
        }
        
        .optimization-result {
            font-size: 0.9em;
            color: #555;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
        }
        
        .error {
            color: #e74c3c;
            text-align: center;
            padding: 20px;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
            
            .status-bar {
                flex-direction: column;
                align-items: stretch;
            }
            
            .controls {
                justify-content: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>OCR性能监控界面</h1>
            <div class="status-bar">
                <div class="status-item">
                    <div class="status-indicator" id="monitoring-status"></div>
                    <span id="monitoring-text">监控状态: 未知</span>
                </div>
                <div class="status-item">
                    <div class="status-indicator" id="auto-optimize-status"></div>
                    <span id="auto-optimize-text">自动优化: 未知</span>
                </div>
                <div class="controls">
                    <button class="btn btn-success" onclick="startMonitoring()">启动监控</button>
                    <button class="btn btn-danger" onclick="stopMonitoring()">停止监控</button>
                    <button class="btn btn-warning" onclick="toggleAutoOptimize()">切换自动优化</button>
                    <button class="btn btn-primary" onclick="generateReport()">生成报告</button>
                </div>
            </div>
        </div>
        
        <div class="dashboard-grid">
            <div class="card">
                <h3>系统性能指标</h3>
                <div class="chart-container">
                    <canvas id="systemChart"></canvas>
                </div>
                <div class="metrics-grid" id="systemMetrics">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            
            <div class="card">
                <h3>OCR服务指标</h3>
                <div class="chart-container">
                    <canvas id="ocrChart"></canvas>
                </div>
                <div class="metrics-grid" id="ocrMetrics">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            
            <div class="card">
                <h3>优化历史</h3>
                <div class="optimization-list" id="optimizationList">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            
            <div class="card">
                <h3>性能趋势</h3>
                <div class="chart-container">
                    <canvas id="trendChart"></canvas>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let systemChart, ocrChart, trendChart;
        let metricsData = [];
        
        // 初始化图表
        function initCharts() {
            const chartOptions = {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                }
            };
            
            // 系统性能图表
            systemChart = new Chart(document.getElementById('systemChart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'CPU使用率 (%)',
                            data: [],
                            borderColor: '#e74c3c',
                            backgroundColor: 'rgba(231, 76, 60, 0.1)',
                            tension: 0.4
                        },
                        {
                            label: '内存使用率 (%)',
                            data: [],
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            tension: 0.4
                        }
                    ]
                },
                options: chartOptions
            });
            
            // OCR服务图表
            ocrChart = new Chart(document.getElementById('ocrChart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: '响应时间 (秒)',
                            data: [],
                            borderColor: '#f39c12',
                            backgroundColor: 'rgba(243, 156, 18, 0.1)',
                            tension: 0.4,
                            yAxisID: 'y1'
                        },
                        {
                            label: '缓存命中率 (%)',
                            data: [],
                            borderColor: '#27ae60',
                            backgroundColor: 'rgba(39, 174, 96, 0.1)',
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    ...chartOptions,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            position: 'left'
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            beginAtZero: true,
                            max: 20,
                            grid: {
                                drawOnChartArea: false
                            }
                        }
                    }
                }
            });
            
            // 性能趋势图表
            trendChart = new Chart(document.getElementById('trendChart'), {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: '吞吐量 (请求/秒)',
                            data: [],
                            backgroundColor: 'rgba(155, 89, 182, 0.8)',
                            borderColor: '#9b59b6',
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    ...chartOptions,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        // 更新状态
        async function updateStatus() {
            try {
                const response = await fetch('/api/status');
                const result = await response.json();
                
                if (result.success) {
                    const data = result.data;
                    
                    // 更新监控状态
                    const monitoringStatus = document.getElementById('monitoring-status');
                    const monitoringText = document.getElementById('monitoring-text');
                    
                    if (data.is_monitoring) {
                        monitoringStatus.classList.add('active');
                        monitoringText.textContent = '监控状态: 运行中';
                    } else {
                        monitoringStatus.classList.remove('active');
                        monitoringText.textContent = '监控状态: 已停止';
                    }
                    
                    // 更新自动优化状态
                    const autoOptimizeStatus = document.getElementById('auto-optimize-status');
                    const autoOptimizeText = document.getElementById('auto-optimize-text');
                    
                    if (data.auto_optimize) {
                        autoOptimizeStatus.classList.add('active');
                        autoOptimizeText.textContent = '自动优化: 已启用';
                    } else {
                        autoOptimizeStatus.classList.remove('active');
                        autoOptimizeText.textContent = '自动优化: 已禁用';
                    }
                }
            } catch (error) {
                console.error('更新状态失败:', error);
            }
        }
        
        // 更新指标
        async function updateMetrics() {
            try {
                const response = await fetch('/api/metrics?limit=50');
                const result = await response.json();
                
                if (result.success && result.data.length > 0) {
                    metricsData = result.data;
                    updateCharts();
                    updateMetricsDisplay();
                }
            } catch (error) {
                console.error('更新指标失败:', error);
            }
        }
        
        // 更新图表
        function updateCharts() {
            if (metricsData.length === 0) return;
            
            const labels = metricsData.map(m => new Date(m.timestamp * 1000).toLocaleTimeString());
            const latest20 = metricsData.slice(-20);
            const labels20 = latest20.map(m => new Date(m.timestamp * 1000).toLocaleTimeString());
            
            // 更新系统性能图表
            systemChart.data.labels = labels20;
            systemChart.data.datasets[0].data = latest20.map(m => m.cpu_usage);
            systemChart.data.datasets[1].data = latest20.map(m => m.memory_usage);
            systemChart.update('none');
            
            // 更新OCR服务图表
            ocrChart.data.labels = labels20;
            ocrChart.data.datasets[0].data = latest20.map(m => m.response_time);
            ocrChart.data.datasets[1].data = latest20.map(m => m.cache_hit_rate);
            ocrChart.update('none');
            
            // 更新趋势图表
            trendChart.data.labels = labels20;
            trendChart.data.datasets[0].data = latest20.map(m => m.throughput);
            trendChart.update('none');
        }
        
        // 更新指标显示
        function updateMetricsDisplay() {
            if (metricsData.length === 0) return;
            
            const latest = metricsData[metricsData.length - 1];
            
            // 系统指标
            document.getElementById('systemMetrics').innerHTML = `
                <div class="metric-item">
                    <div class="metric-value">${latest.cpu_usage.toFixed(1)}%</div>
                    <div class="metric-label">CPU使用率</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">${latest.memory_usage.toFixed(1)}%</div>
                    <div class="metric-label">内存使用率</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">${latest.gpu_usage.toFixed(1)}%</div>
                    <div class="metric-label">GPU使用率</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">${latest.active_instances}</div>
                    <div class="metric-label">活跃实例</div>
                </div>
            `;
            
            // OCR指标
            document.getElementById('ocrMetrics').innerHTML = `
                <div class="metric-item">
                    <div class="metric-value">${latest.response_time.toFixed(2)}s</div>
                    <div class="metric-label">响应时间</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">${latest.throughput.toFixed(1)}</div>
                    <div class="metric-label">吞吐量</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">${latest.cache_hit_rate.toFixed(1)}%</div>
                    <div class="metric-label">缓存命中率</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">${latest.error_rate.toFixed(1)}%</div>
                    <div class="metric-label">错误率</div>
                </div>
            `;
        }
        
        // 更新优化历史
        async function updateOptimizations() {
            try {
                const response = await fetch('/api/optimizations?limit=10');
                const result = await response.json();
                
                if (result.success) {
                    const optimizations = result.data;
                    const listElement = document.getElementById('optimizationList');
                    
                    if (optimizations.length === 0) {
                        listElement.innerHTML = '<div class="loading">暂无优化记录</div>';
                        return;
                    }
                    
                    listElement.innerHTML = optimizations.reverse().map(opt => `
                        <div class="optimization-item ${opt.actual_result && opt.actual_result.includes('失败') ? 'error' : ''}">
                            <div class="optimization-time">${new Date(opt.timestamp * 1000).toLocaleString()}</div>
                            <div class="optimization-desc">${opt.description}</div>
                            <div class="optimization-result">${opt.actual_result || '执行中...'}</div>
                        </div>
                    `).join('');
                }
            } catch (error) {
                console.error('更新优化历史失败:', error);
            }
        }
        
        // 控制函数
        async function startMonitoring() {
            try {
                const response = await fetch('/api/control/start', { method: 'POST' });
                const result = await response.json();
                alert(result.success ? result.message : result.error);
                updateStatus();
            } catch (error) {
                alert('启动监控失败: ' + error.message);
            }
        }
        
        async function stopMonitoring() {
            try {
                const response = await fetch('/api/control/stop', { method: 'POST' });
                const result = await response.json();
                alert(result.success ? result.message : result.error);
                updateStatus();
            } catch (error) {
                alert('停止监控失败: ' + error.message);
            }
        }
        
        async function toggleAutoOptimize() {
            try {
                const response = await fetch('/api/control/toggle-auto-optimize', { method: 'POST' });
                const result = await response.json();
                alert(result.success ? result.data.message : result.error);
                updateStatus();
            } catch (error) {
                alert('切换自动优化失败: ' + error.message);
            }
        }
        
        async function generateReport() {
            try {
                const hours = prompt('请输入报告时间范围（小时）:', '24');
                if (!hours) return;
                
                const response = await fetch(`/api/report?hours=${hours}`);
                const result = await response.json();
                
                if (result.success) {
                    // 保存报告
                    const saveResponse = await fetch('/api/report/save', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ hours: parseInt(hours) })
                    });
                    
                    const saveResult = await saveResponse.json();
                    alert(saveResult.success ? saveResult.data.message : saveResult.error);
                } else {
                    alert('生成报告失败: ' + result.error);
                }
            } catch (error) {
                alert('生成报告失败: ' + error.message);
            }
        }
        
        // 初始化
        document.addEventListener('DOMContentLoaded', function() {
            initCharts();
            updateStatus();
            updateMetrics();
            updateOptimizations();
            
            // 定期更新
            setInterval(updateStatus, 5000);
            setInterval(updateMetrics, 10000);
            setInterval(updateOptimizations, 15000);
        });
    </script>
</body>
</html>
        """
    
    def run(self, debug: bool = False):
        """启动Web界面"""
        try:
            self.logger.info(f"启动性能监控Web界面: http://{self.host}:{self.port}")
            self.app.run(host=self.host, port=self.port, debug=debug, threaded=True)
        except Exception as e:
            self.logger.error(f"启动Web界面失败: {e}")
            raise


if __name__ == "__main__":
    # 创建性能监控实例
    monitor = PerformanceMonitor()
    
    # 创建Web界面
    dashboard = PerformanceDashboard(monitor)
    
    try:
        # 启动监控
        monitor.start_monitoring()
        
        # 启动Web界面
        dashboard.run(debug=False)
        
    except KeyboardInterrupt:
        test_logger = get_logger("PerformanceDashboardTest", "MONITOR")
        test_logger.info("正在关闭...")
    finally:
        monitor.stop_monitoring()
        test_logger = get_logger("PerformanceDashboardTest", "MONITOR")
        test_logger.info("性能监控已停止")