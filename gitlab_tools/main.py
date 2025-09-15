#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab同步工具主入口
提供统一的命令行接口
"""

import sys
import os
import argparse

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scripts.sync_progress import sync_gitlab_progress
from scripts.sync_issues import sync_issues_to_gitlab
from utils.helpers import backup_database

def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='GitLab同步工具')
    parser.add_argument('command', choices=['sync-progress', 'sync-issues', 'backup'],
                       help='要执行的命令')
    parser.add_argument('--limit', type=int, default=20,
                       help='同步议题数量限制（默认20）')
    parser.add_argument('--backup', action='store_true',
                       help='执行前备份数据库')

    args = parser.parse_args()

    # 如果需要备份数据库
    if args.backup:
        print("🔄 备份数据库...")
        if not backup_database():
            print("❌ 数据库备份失败，退出")
            sys.exit(1)
        print("✅ 数据库备份完成")

    # 执行相应命令
    if args.command == 'sync-progress':
        print("🔄 开始同步进度...")
        sync_gitlab_progress()
    elif args.command == 'sync-issues':
        print("🔄 开始同步议题...")
        success = sync_issues_to_gitlab(args.limit)
        if not success:
            sys.exit(1)
    elif args.command == 'backup':
        print("🔄 开始备份数据库...")
        if not backup_database():
            sys.exit(1)

if __name__ == "__main__":
    main()
