#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块
提供通用的辅助函数
"""

import os
import subprocess
import logging
from typing import Dict, Any, Optional
from datetime import datetime

def backup_database() -> bool:
    """
    备份数据库
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"/root/update_issue/database_backup_{timestamp}.sql"

        cmd = [
            'mysqldump', '-u', 'issue', '-phszc8888',
            'issue_database', '>', backup_file
        ]

        result = subprocess.run(' '.join(cmd), shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ 数据库备份成功: {backup_file}")
            return True
        else:
            print(f"❌ 数据库备份失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 数据库备份异常: {e}")
        return False

def setup_logging(log_file: Optional[str] = None) -> logging.Logger:
    """
    设置日志配置
    """
    import logging

    if log_file is None:
        log_file = '/root/update_issue/gitlab_tools/logs/sync.log'

    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # 创建logger
    logger = logging.getLogger('auto_sync')
    logger.setLevel(logging.INFO)

    # 避免重复添加handler
    if not logger.handlers:
        # 创建文件handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # 创建控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 创建formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加handler
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

def print_stats(stats: Dict[str, int], title: str = "统计结果") -> None:
    """
    打印统计信息
    """
    print(f"\n📊 {title}:")
    for key, value in stats.items():
        if key == 'total':
            print(f"  📋 总议题数: {value}")
        elif key == 'updated':
            print(f"  🔄 已更新: {value}")
        elif key == 'skipped':
            print(f"  ⏭️  跳过: {value}")
        elif key == 'closed':
            print(f"  🔒 已关闭: {value}")
        elif key == 'failed':
            print(f"  ❌ 失败: {value}")
        elif key == 'not_found':
            print(f"  🔍 未找到: {value}")
        elif key == 'created':
            print(f"  ✅ 已创建: {value}")
        else:
            print(f"  {key}: {value}")

def validate_issue_data(issue_data: Dict[str, Any]) -> bool:
    """
    验证议题数据
    """
    required_fields = ['id', 'project_name', 'problem_description']

    for field in required_fields:
        if not issue_data.get(field):
            print(f"❌ 缺少必需字段: {field}")
            return False

    return True
