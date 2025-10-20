#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理核心模块
统一管理所有配置文件
"""

import os
import json
from typing import Dict, Any, Optional

class ConfigManager:
    """配置管理器"""

    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            # 从当前文件位置向上找到项目根目录
            current_file = os.path.abspath(__file__)
            # src/gitlab/core/config_manager.py -> 项目根目录
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
        self.base_path = base_path

    def load_gitlab_config(self) -> Optional[Dict[str, Any]]:
        """
        加载GitLab配置
        """
        try:
            config_path = os.path.join(self.base_path, 'config', 'wps_gitlab_config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                full_config = json.load(f)
                # 提取gitlab配置部分
                gitlab_config = full_config.get('gitlab', {})
                if gitlab_config:
                    # 重命名字段以匹配期望的格式
                    return {
                        'gitlab_url': gitlab_config.get('url'),
                        'private_token': gitlab_config.get('token'),
                        'project_id': gitlab_config.get('project_id'),
                        'project_path': gitlab_config.get('project_path')
                    }
                return None
        except Exception as e:
            print(f"❌ 加载GitLab配置失败: {e}")
            return None

    def load_full_config(self) -> Optional[Dict[str, Any]]:
        """
        加载完整配置（包括标签映射等）
        """
        try:
            config_path = os.path.join(self.base_path, 'config', 'wps_gitlab_config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载完整配置失败: {e}")
            return None

    def load_user_mapping(self) -> Optional[Dict[str, Any]]:
        """
        加载用户映射配置
        """
        try:
            mapping_path = os.path.join(self.base_path, 'config', 'user_mapping.json')
            with open(mapping_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载用户映射配置失败: {e}")
            return None

    def load_gitlab_env(self) -> Optional[Dict[str, str]]:
        """
        加载GitLab环境变量
        """
        try:
            env_path = os.path.join(self.base_path, 'config', 'gitlab.env')
            config = {}
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key] = value
            return config
        except Exception as e:
            print(f"❌ 加载GitLab环境配置失败: {e}")
            return None
