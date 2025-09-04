#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR API服务器
提供HTTP接口访问OCR池服务

@author: Mr.Rey Copyright © 2025
@created: 2025-01-14 00:50:00
@modified: 2025-09-03 18:25:00
@version: 1.1.0
"""

import argparse
import sys
import time
import base64
import traceback
import numpy as np
from pathlib import Path
from flask import Flask
from flask import jsonify
from flask import request
from src.core.ocr.services.ocr_pool_manager import get_pool_manager
from src.ui.services.logging_service import get_logger
from src.ui.services.cross_process_log_bridge import create_cross_process_handler

# 全局变量
pool_manager = None
logger = None

def serialize_numpy_types(obj):
    """将numpy类型转换为Python原生类型"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: serialize_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(serialize_numpy_types(item) for item in obj)
    else:
        return obj

def create_app(host='127.0.0.1', port=8900, ocr_pool_manager=None):
    """创建Flask应用"""
    global pool_manager, logger
    
    app = Flask(__name__)
    
    # 在函数内部导入CORS以避免模块级别的导入问题
    try:
        from flask_cors import CORS
        # 启用CORS
        CORS(app, resources={
            r"/*": {
                "origins": "*",
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"]
            }
        })
    except ImportError as e:
        temp_logger = get_logger('OCRAPIServerInit', 'OCR')
        temp_logger.warning(f"无法导入flask_cors: {e}")
        temp_logger.warning("CORS功能将不可用")
    
    # 使用传入的OCR池管理器实例
    if ocr_pool_manager:
        pool_manager = ocr_pool_manager
    
    logger = get_logger('OCRAPIServer', 'OCR')
    
    # 为OCR API服务器添加跨进程日志处理器
    try:
        cross_process_handler = create_cross_process_handler(source="OCRAPIServer")
        logger.addHandler(cross_process_handler)
    except Exception as e:
        logger.warning(f"OCR API服务器添加跨进程日志处理器失败: {e}")
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """健康检查接口"""
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'service': 'OCR API Server'
        })
    
    @app.route('/status', methods=['GET'])
    def get_status():
        """获取OCR池状态"""
        try:
            if pool_manager is None:
                return jsonify({
                    'error': 'OCR池管理器未初始化',
                    'status': 'error'
                }), 500
            
            status = pool_manager.get_pool_status()
            return jsonify({
                'status': 'success',
                'data': {
                    'total_instances': status.total_instances,
                    'running_instances': status.running_instances,
                    'idle_instances': status.idle_instances,
                    'total_requests': status.total_requests,
                    'successful_requests': status.successful_requests,
                    'failed_requests': status.failed_requests,
                    'average_response_time': status.average_response_time,
                    'memory_usage': status.memory_usage,
                    'cpu_usage': status.cpu_usage
                }
            })
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
            return jsonify({
                'error': f'获取状态失败: {str(e)}',
                'status': 'error'
            }), 500
    
    @app.route('/ocr', methods=['POST'])
    def process_ocr():
        """OCR识别接口"""
        try:
            if pool_manager is None:
                return jsonify({
                    'error': 'OCR池管理器未初始化',
                    'status': 'error'
                }), 500
            
            # 获取请求数据
            data = request.get_json()
            if not data:
                return jsonify({
                    'error': '请求数据为空',
                    'status': 'error'
                }), 400
            
            # 检查必需参数
            if 'image' not in data:
                return jsonify({
                    'error': '缺少image参数',
                    'status': 'error'
                }), 400
            
            # 获取参数
            base64_image = data['image']
            request_type = data.get('request_type', 'recognize')
            keywords = data.get('keywords', [])
            
            # 解码base64图像
            try:
                image_data = base64.b64decode(base64_image)
            except Exception as e:
                return jsonify({
                    'error': f'图像解码失败: {str(e)}',
                    'status': 'error'
                }), 400
            
            logger.info(f"收到OCR请求，类型: {request_type}")
            
            # 调用OCR池处理
            start_time = time.time()
            result = pool_manager.process_ocr_request(
                image_data=image_data,
                request_type=request_type,
                keywords=keywords
            )
            processing_time = time.time() - start_time
            
            logger.info(f"OCR处理完成，耗时: {processing_time:.2f}秒")
            
            # 序列化numpy类型
            serialized_result = serialize_numpy_types(result)
            
            return jsonify({
                'status': 'success',
                'data': serialized_result,
                'processing_time': processing_time
            })
            
        except Exception as e:
            logger.error(f"OCR处理失败: {e}")
            logger.error(f"详细错误: {traceback.format_exc()}")
            return jsonify({
                'error': f'OCR处理失败: {str(e)}',
                'status': 'error'
            }), 500
    
    @app.route('/instances', methods=['GET'])
    def get_instances():
        """获取实例列表"""
        try:
            if pool_manager is None:
                return jsonify({
                    'error': 'OCR池管理器未初始化',
                    'status': 'error'
                }), 500
            
            instances = []
            for instance_id, instance_info in pool_manager.instances.items():
                instances.append({
                    'instance_id': instance_id,
                    'port': instance_info.port,
                    'status': instance_info.status.value,
                    'created_at': instance_info.created_at.isoformat(),
                    'last_activity': instance_info.last_activity.isoformat(),
                    'processed_requests': instance_info.processed_requests,
                    'error_count': instance_info.error_count,
                    'memory_usage': instance_info.memory_usage,
                    'cpu_usage': instance_info.cpu_usage
                })
            
            # 序列化numpy类型
            serialized_instances = serialize_numpy_types(instances)
            
            return jsonify({
                'status': 'success',
                'data': serialized_instances
            })
            
        except Exception as e:
            logger.error(f"获取实例列表失败: {e}")
            return jsonify({
                'error': f'获取实例列表失败: {str(e)}',
                'status': 'error'
            }), 500
    
    @app.route('/instances/<instance_id>', methods=['GET'])
    def get_instance_detail(instance_id):
        """获取实例详情"""
        try:
            if pool_manager is None:
                return jsonify({
                    'error': 'OCR池管理器未初始化',
                    'status': 'error'
                }), 500
            
            if instance_id not in pool_manager.instances:
                return jsonify({
                    'error': f'实例 {instance_id} 不存在',
                    'status': 'error'
                }), 404
            
            instance_info = pool_manager.instances[instance_id]
            
            # 获取实例配置信息
            config_info = {
                'model': 'EasyOCR',
                'languages': ['ch_sim', 'en'],
                'gpu_enabled': False,
                'max_concurrent': 1
            }
            
            # 如果实例有服务对象，获取实际配置
            if instance_info.service:
                config_info.update({
                    'languages': instance_info.service.languages,
                    'gpu_enabled': instance_info.service.gpu,
                    'model_storage_directory': instance_info.service.model_storage_directory
                })
            
            detail = {
                'instance_id': instance_id,
                'port': instance_info.port,
                'status': instance_info.status.value,
                'created_at': instance_info.created_at.isoformat(),
                'last_activity': instance_info.last_activity.isoformat(),
                'last_used': instance_info.last_used.isoformat() if instance_info.last_used else None,
                'processed_requests': instance_info.processed_requests,
                'request_count': instance_info.request_count,
                'error_count': instance_info.error_count,
                'memory_usage': instance_info.memory_usage,
                'cpu_usage': instance_info.cpu_usage,
                'response_times': instance_info.response_times[-10:] if instance_info.response_times else [],
                'config': config_info
            }
            
            # 序列化numpy类型
            serialized_detail = serialize_numpy_types(detail)
            
            return jsonify({
                'status': 'success',
                'data': serialized_detail
            })
            
        except Exception as e:
            logger.error(f"获取实例详情失败: {e}")
            return jsonify({
                'error': f'获取实例详情失败: {str(e)}',
                'status': 'error'
            }), 500
    
    @app.route('/instances/<instance_id>/logs', methods=['GET'])
    def get_instance_logs(instance_id):
        """获取实例日志"""
        try:
            if pool_manager is None:
                return jsonify({
                    'error': 'OCR池管理器未初始化',
                    'status': 'error'
                }), 500
            
            if instance_id not in pool_manager.instances:
                return jsonify({
                    'error': f'实例 {instance_id} 不存在',
                    'status': 'error'
                }), 404
            
            # 模拟日志数据（实际应该从日志文件读取）
            logs = [
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] INFO: 实例 {instance_id} 启动",
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] INFO: 实例 {instance_id} 准备就绪",
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] INFO: 实例 {instance_id} 处理请求中"
            ]
            
            return jsonify({
                'status': 'success',
                'data': logs
            })
            
        except Exception as e:
            logger.error(f"获取实例日志失败: {e}")
            return jsonify({
                'error': f'获取实例日志失败: {str(e)}',
                'status': 'error'
            }), 500
    
    @app.route('/instances', methods=['POST'])
    def create_instance():
        """创建新实例"""
        try:
            if pool_manager is None:
                return jsonify({
                    'error': 'OCR池管理器未初始化',
                    'status': 'error'
                }), 500
            
            instance_id = pool_manager.create_instance()
            if instance_id:
                logger.info(f"成功创建实例: {instance_id}")
                return jsonify({
                    'status': 'success',
                    'data': {
                        'instance_id': instance_id,
                        'message': '实例创建成功'
                    }
                })
            else:
                return jsonify({
                    'error': '创建实例失败',
                    'status': 'error'
                }), 500
            
        except Exception as e:
            logger.error(f"创建实例失败: {e}")
            return jsonify({
                'error': f'创建实例失败: {str(e)}',
                'status': 'error'
            }), 500
    
    @app.route('/instances/<instance_id>', methods=['DELETE'])
    def remove_instance(instance_id):
        """移除实例"""
        try:
            if pool_manager is None:
                return jsonify({
                    'error': 'OCR池管理器未初始化',
                    'status': 'error'
                }), 500
            
            success = pool_manager.remove_instance(instance_id)
            if success:
                logger.info(f"成功移除实例: {instance_id}")
                return jsonify({
                    'status': 'success',
                    'data': {
                        'message': f'实例 {instance_id} 移除成功'
                    }
                })
            else:
                return jsonify({
                    'error': f'移除实例 {instance_id} 失败',
                    'status': 'error'
                }), 500
            
        except Exception as e:
            logger.error(f"移除实例失败: {e}")
            return jsonify({
                'error': f'移除实例失败: {str(e)}',
                'status': 'error'
            }), 500
    
    @app.route('/instances/<instance_id>/start', methods=['POST'])
    def start_instance(instance_id):
        """启动实例"""
        try:
            if pool_manager is None:
                return jsonify({
                    'error': 'OCR池管理器未初始化',
                    'status': 'error'
                }), 500
            
            success = pool_manager.start_instance(instance_id)
            if success:
                logger.info(f"成功启动实例: {instance_id}")
                return jsonify({
                    'status': 'success',
                    'data': {
                        'message': f'实例 {instance_id} 启动成功'
                    }
                })
            else:
                return jsonify({
                    'error': f'启动实例 {instance_id} 失败',
                    'status': 'error'
                }), 500
            
        except Exception as e:
            logger.error(f"启动实例失败: {e}")
            return jsonify({
                'error': f'启动实例失败: {str(e)}',
                'status': 'error'
            }), 500
    
    @app.route('/instances/<instance_id>/stop', methods=['POST'])
    def stop_instance(instance_id):
        """停止实例"""
        try:
            if pool_manager is None:
                return jsonify({
                    'error': 'OCR池管理器未初始化',
                    'status': 'error'
                }), 500
            
            success = pool_manager.stop_instance(instance_id)
            if success:
                logger.info(f"成功停止实例: {instance_id}")
                return jsonify({
                    'status': 'success',
                    'data': {
                        'message': f'实例 {instance_id} 停止成功'
                    }
                })
            else:
                return jsonify({
                    'error': f'停止实例 {instance_id} 失败',
                    'status': 'error'
                }), 500
            
        except Exception as e:
            logger.error(f"停止实例失败: {e}")
            return jsonify({
                'error': f'停止实例失败: {str(e)}',
                'status': 'error'
            }), 500
    
    @app.route('/instances/<instance_id>/restart', methods=['POST'])
    def restart_instance(instance_id):
        """重启实例"""
        try:
            if pool_manager is None:
                return jsonify({
                    'error': 'OCR池管理器未初始化',
                    'status': 'error'
                }), 500
            
            # 先停止再启动
            stop_success = pool_manager.stop_instance(instance_id)
            if not stop_success:
                return jsonify({
                    'error': f'停止实例 {instance_id} 失败',
                    'status': 'error'
                }), 500
            
            # 等待一秒确保停止完成
            time.sleep(1)
            
            start_success = pool_manager.start_instance(instance_id)
            if start_success:
                logger.info(f"成功重启实例: {instance_id}")
                return jsonify({
                    'status': 'success',
                    'data': {
                        'message': f'实例 {instance_id} 重启成功'
                    }
                })
            else:
                return jsonify({
                    'error': f'启动实例 {instance_id} 失败',
                    'status': 'error'
                }), 500
            
        except Exception as e:
            logger.error(f"重启实例失败: {e}")
            return jsonify({
                'error': f'重启实例失败: {str(e)}',
                'status': 'error'
            }), 500
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': '接口不存在',
            'status': 'error'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': '服务器内部错误',
            'status': 'error'
        }), 500
    
    return app

def start_api_server(host='127.0.0.1', port=8900, debug=False):
    """启动API服务器"""
    global pool_manager, logger
    
    try:
        # 获取OCR池管理器实例
        pool_manager = get_pool_manager()
        if pool_manager is None:
            raise RuntimeError("无法获取OCR池管理器实例")
        
        # 创建Flask应用
        app = create_app(host, port, pool_manager)
        
        logger = get_logger('OCRAPIServer', 'OCR')
        logger.info(f"启动OCR API服务器 - {host}:{port}")
        
        # 启动服务器
        app.run(host=host, port=port, debug=debug, threaded=True)
        
    except Exception as e:
        if logger:
            logger.error(f"API服务器启动失败: {e}")
        temp_logger = get_logger('OCRAPIServerStart', 'OCR')
        temp_logger.error(f"API服务器启动失败: {e}")
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OCR API服务器')
    parser.add_argument('--host', default='127.0.0.1', help='服务主机地址')
    parser.add_argument('--port', type=int, default=8900, help='服务端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    try:
        start_api_server(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        temp_logger = get_logger('OCRAPIServerMain', 'OCR')
        temp_logger.info("正在关闭OCR API服务器...")
    except Exception as e:
        temp_logger = get_logger('OCRAPIServerMain', 'OCR')
        temp_logger.error(f"OCR API服务器运行失败: {e}")
        sys.exit(1)