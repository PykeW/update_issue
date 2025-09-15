#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时同步脚本
每天上午8点和下午1点同步GitLab进度
"""

import sys
import os
import subprocess
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.helpers import setup_logging

def run_sync():
    """
    运行同步任务
    """
    # 设置日志
    setup_logging('/root/update_issue/gitlab_tools/logs/scheduled_sync.log')

    try:
        logging.info("=" * 60)
        logging.info("开始定时同步任务")
        logging.info(f"执行时间: {os.popen('date').read().strip()}")
        logging.info("=" * 60)

        # 运行进度同步
        result = subprocess.run([
            'python3', '/root/update_issue/gitlab_tools/scripts/sync_progress.py'
        ], capture_output=True, text=True, cwd='/root/update_issue/gitlab_tools')

        if result.returncode == 0:
            logging.info("✅ 进度同步完成")
            logging.info(f"输出: {result.stdout}")
        else:
            logging.error("❌ 进度同步失败")
            logging.error(f"错误: {result.stderr}")

        # 运行议题同步（处理新增的open状态议题）
        result2 = subprocess.run([
            'python3', '/root/update_issue/gitlab_tools/scripts/sync_issues.py'
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
