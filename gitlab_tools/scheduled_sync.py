#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时同步脚本
每天上午8点和下午1点同步GitLab进度
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/update_issue/gitlab_tools/sync.log'),
        logging.StreamHandler()
    ]
)

def run_sync():
    """
    运行同步任务
    """
    try:
        logging.info("=" * 60)
        logging.info("开始定时同步任务")
        logging.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("=" * 60)

        # 运行进度同步
        result = subprocess.run([
            'python3', '/root/update_issue/gitlab_tools/sync_gitlab_progress.py'
        ], capture_output=True, text=True, cwd='/root/update_issue/gitlab_tools')

        if result.returncode == 0:
            logging.info("✅ 进度同步完成")
            logging.info(f"输出: {result.stdout}")
        else:
            logging.error("❌ 进度同步失败")
            logging.error(f"错误: {result.stderr}")

        # 运行议题同步（处理新增的open状态议题）
        result2 = subprocess.run([
            'python3', '/root/update_issue/gitlab_tools/enhanced_sync_database_to_gitlab.py'
        ], capture_output=True, text=True, cwd='/root/update_issue/gitlab_tools')

        if result2.returncode == 0:
            logging.info("✅ 议题同步完成")
            logging.info(f"输出: {result2.stdout}")
        else:
            logging.error("❌ 议题同步失败")
            logging.error(f"错误: {result2.stderr}")

        logging.info("定时同步任务完成")

    except Exception as e:
        logging.error(f"定时同步任务异常: {e}")

if __name__ == "__main__":
    run_sync()
