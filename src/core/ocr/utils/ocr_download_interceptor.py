# -*- coding: utf-8 -*-
"""
OCR模型下载拦截器
用于拦截EasyOCR的在线下载行为，强制使用本地模型

@author: Mr.Rey Copyright © 2025
@created: 2025-01-14 15:35:00
@modified: 2025-01-14 15:35:00
@version: 1.0.0
"""

import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import torch.hub

from src.core.ocr.utils.ocr_logger import ocr_logger


class OCRDownloadInterceptor:
    """
    OCR模型下载拦截器
    拦截EasyOCR的网络下载行为，强制使用本地模型文件
    """
    
    def __init__(self):
        """
        初始化下载拦截器
        """
        self.logger = ocr_logger
        self.is_intercepting = False
        
        # 设置模型目录 - 使用绝对路径，优先使用环境变量
        import os
        project_root_env = os.environ.get('HONYGO_PROJECT_ROOT')
        if project_root_env:
            project_root = Path(project_root_env)
        else:
            # 回退到基于文件路径的计算
            current_file = Path(__file__)
            # 从 src/core/ocr/utils 回到项目根目录需要5个parent
            project_root = current_file.parent.parent.parent.parent.parent
        self.model_directory = project_root / "src" / "core" / "ocr" / "third_party" / "ocr" / "easyocr-models"
        
        # 保存原始函数引用
        self.original_urlopen = urllib.request.urlopen
        self.original_urlretrieve = urllib.request.urlretrieve
        self.original_requests_get = requests.get
        self.original_requests_post = requests.post
        self.original_torch_hub_download = torch.hub.download_url_to_file
        
        # 模型文件映射 - 基于实际存在的模型文件
        self.model_mapping = {
            'craft_mlt_25k.pth': {
                'description': 'CRAFT文本检测模型',
                'url': 'https://github.com/clovaai/CRAFT-pytorch/releases/download/v1.0/craft_mlt_25k.zip'
            },
            'english_g2.pth': {
                'description': '英文识别模型',
                'url': 'https://github.com/JaidedAI/EasyOCR/releases/download/v1.3.2/english_g2.zip'
            },
            'zh_sim_g2.pth': {
                'description': '简体中文识别模型',
                'url': 'https://github.com/JaidedAI/EasyOCR/releases/download/v1.3.2/zh_sim_g2.zip'
            },
            'pretrained_ic15_res18.pt': {
                'description': 'ResNet18预训练模型',
                'url': 'https://github.com/JaidedAI/EasyOCR/releases/download/v1.3.2/pretrained_ic15_res18.zip'
            },
            'pretrained_ic15_res50.pt': {
                'description': 'ResNet50预训练模型',
                'url': 'https://github.com/JaidedAI/EasyOCR/releases/download/v1.3.2/pretrained_ic15_res50.zip'
            },
            'resnet18-5c106cde.pth': {
                'description': 'ResNet18基础模型',
                'url': 'https://download.pytorch.org/models/resnet18-5c106cde.pth'
            }
        }
    
    def start_intercepting(self):
        """
        开始拦截网络下载
        """
        if self.is_intercepting:
            self.logger.info("OCR模型下载拦截器已在运行")
            return
        
        # 替换网络请求函数
        urllib.request.urlopen = self._intercept_urlopen
        urllib.request.urlretrieve = self._intercept_urlretrieve
        requests.get = self._intercept_requests_get
        requests.post = self._intercept_requests_post
        torch.hub.download_url_to_file = self._intercept_torch_download
        
        self.is_intercepting = True
        self.logger.info("OCR模型下载拦截器已启动")
        
        # 检查本地模型状态
        self._check_local_models()
    
    def stop_intercepting(self):
        """
        停止拦截网络下载
        """
        if not self.is_intercepting:
            self.logger.info("OCR模型下载拦截器未在运行")
            return
        
        # 恢复原始函数
        urllib.request.urlopen = self.original_urlopen
        urllib.request.urlretrieve = self.original_urlretrieve
        requests.get = self.original_requests_get
        requests.post = self.original_requests_post
        torch.hub.download_url_to_file = self.original_torch_hub_download
        
        self.is_intercepting = False
        self.logger.info("OCR模型下载拦截器已停止")
    
    def _intercept_urlopen(self, url, *args, **kwargs):
        """
        拦截urllib.request.urlopen
        """
        self._log_download_attempt(url, "urlopen")
        raise urllib.error.URLError("网络下载已被拦截，请使用本地模型文件")
    
    def _intercept_urlretrieve(self, url, filename=None, *args, **kwargs):
        """
        拦截urllib.request.urlretrieve
        """
        self._log_download_attempt(url, "urlretrieve", filename)
        raise urllib.error.URLError("网络下载已被拦截，请使用本地模型文件")
    
    def _intercept_requests_get(self, url, *args, **kwargs):
        """
        拦截requests.get
        """
        self._log_download_attempt(url, "requests.get")
        raise Exception("网络下载已被拦截，请使用本地模型文件")
    
    def _intercept_requests_post(self, url, *args, **kwargs):
        """
        拦截requests.post
        """
        self._log_download_attempt(url, "requests.post")
        raise Exception("网络下载已被拦截，请使用本地模型文件")
    
    def _intercept_torch_download(self, url, dst, *args, **kwargs):
        """
        拦截torch.hub.download_url_to_file
        """
        self._log_download_attempt(url, "torch.hub.download_url_to_file", dst)
        raise Exception("网络下载已被拦截，请使用本地模型文件")
    
    def _log_download_attempt(self, url: str, method: str, filename: Optional[str] = None):
        """
        记录下载尝试
        """
        self.logger.warning(f"拦截到网络下载尝试 - 方法: {method}")
        self.logger.warning(f"下载地址: {url}")
        
        if filename:
            self.logger.warning(f"目标文件: {filename}")
        
        # 分析缺失的模型文件
        missing_model = self._analyze_missing_model(url)
        if missing_model:
            model_info = self.model_mapping.get(missing_model)
            if model_info:
                self.logger.error(f"缺少模型文件: {missing_model}")
                self.logger.error(f"模型描述: {model_info['description']}")
                self.logger.error(f"官方下载地址: {model_info['url']}")
                self.logger.error(f"请手动下载并放置到: {self.model_directory}")
            else:
                self.logger.error(f"检测到未知模型下载: {url}")
        
        # 检查本地模型文件状态
        self._check_local_models()
    
    def _analyze_missing_model(self, url: str) -> Optional[str]:
        """
        分析缺失的模型文件
        """
        # 从URL中提取可能的模型文件名
        for model_file, model_info in self.model_mapping.items():
            if model_info['url'] in url or url in model_info['url']:
                return model_file
        
        # 尝试从URL路径中提取文件名
        if '.zip' in url:
            zip_name = url.split('/')[-1]
            # 移除.zip后缀，添加.pth后缀
            if zip_name.endswith('.zip'):
                model_name = zip_name[:-4] + '.pth'
                return model_name
        
        return None
    
    def _check_local_models(self):
        """
        检查本地模型文件状态
        """
        if not self.model_directory.exists():
            self.logger.error(f"模型目录不存在: {self.model_directory}")
            return
        
        existing_models = []
        missing_models = []
        
        for model_file in self.model_mapping.keys():
            model_path = self.model_directory / model_file
            if model_path.exists():
                existing_models.append(model_file)
            else:
                missing_models.append(model_file)
        
        self.logger.info(f"本地已有模型文件 ({len(existing_models)}个): {', '.join(existing_models)}")
        if missing_models:
            self.logger.warning(f"本地缺失模型文件 ({len(missing_models)}个): {', '.join(missing_models)}")
    
    def get_model_status(self) -> Dict[str, Any]:
        """
        获取模型状态信息
        """
        status = {
            'intercepting': self.is_intercepting,
            'model_directory': str(self.model_directory),
            'existing_models': [],
            'missing_models': [],
            'all_models_available': True
        }
        
        if self.model_directory.exists():
            for model_file in self.model_mapping.keys():
                model_path = self.model_directory / model_file
                if model_path.exists():
                    status['existing_models'].append({
                        'file': model_file,
                        'description': self.model_mapping[model_file]['description'],
                        'size': model_path.stat().st_size
                    })
                else:
                    status['missing_models'].append({
                        'file': model_file,
                        'description': self.model_mapping[model_file]['description'],
                        'url': self.model_mapping[model_file]['url']
                    })
                    status['all_models_available'] = False
        else:
            # 目录不存在，所有模型都缺失
            for model_file in self.model_mapping.keys():
                status['missing_models'].append({
                    'file': model_file,
                    'description': self.model_mapping[model_file]['description'],
                    'url': self.model_mapping[model_file]['url']
                })
            status['all_models_available'] = False
        
        return status


# 全局拦截器实例
_interceptor = None


def get_interceptor() -> OCRDownloadInterceptor:
    """
    获取全局拦截器实例
    """
    global _interceptor
    if _interceptor is None:
        _interceptor = OCRDownloadInterceptor()
    return _interceptor


def start_download_interception():
    """
    启动下载拦截
    """
    interceptor = get_interceptor()
    interceptor.start_intercepting()


def stop_download_interception():
    """
    停止下载拦截
    """
    interceptor = get_interceptor()
    interceptor.stop_intercepting()


def get_model_status():
    """
    获取模型状态
    """
    interceptor = get_interceptor()
    return interceptor.get_model_status()