#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab同步工具主入口
提供统一的命令行接口
"""

import sys
import os
import argparse
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.auto_sync_manager import AutoSyncManager
from scripts.health_check import HealthChecker
from scripts.monitor import SystemMonitor
from scripts.monitor_progress import ProgressMonitoringService
from utils.helpers import backup_database

def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='GitLab同步工具')
    parser.add_argument('command',
                       choices=['sync-progress', 'sync-issues', 'sync-queue', 'sync-full',
                               'backup', 'health-check', 'monitor', 'monitor-progress', 'setup'],
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

    # 初始化同步管理器
    sync_manager = AutoSyncManager()

    # 执行相应命令
    if args.command == 'sync-progress':
        print("🔄 开始同步进度...")
        result = sync_manager.sync_progress()
        print(f"进度同步完成: 更新 {result['updated']} 个，跳过 {result['skipped']} 个，失败 {result['failed']} 个，关闭 {result['closed']} 个")

    elif args.command == 'sync-issues':
        print("🔄 开始同步议题...")
        result = sync_manager.sync_new_issues()
        print(f"议题同步完成: 创建 {result['created']} 个，失败 {result['failed']} 个")
        if result['failed'] > 0:
            sys.exit(1)

    elif args.command == 'sync-queue':
        print("🔄 开始处理同步队列...")
        result = sync_manager.process_sync_queue()
        print(f"队列处理完成: 处理 {result['processed']} 个，失败 {result['failed']} 个")

    elif args.command == 'sync-full':
        print("🔄 开始完整同步...")
        result = sync_manager.run_full_sync()
        print(f"完整同步完成，耗时 {result['duration']:.2f} 秒")

    elif args.command == 'backup':
        print("🔄 开始备份数据库...")
        if not backup_database():
            sys.exit(1)

    elif args.command == 'health-check':
        print("🔍 开始健康检查...")
        checker = HealthChecker()
        success = checker.run_health_check()
        if not success:
            sys.exit(1)

    elif args.command == 'monitor':
        print("📊 开始系统监控...")
        monitor = SystemMonitor()
        report = monitor.generate_report()
        print(report)
        print("✅ 系统监控完成")

    elif args.command == 'monitor-progress':
        print("🔍 开始GitLab进度监控...")
        progress_service = ProgressMonitoringService()
        results = progress_service.run_single_monitoring()
        print(f"进度监控完成: 更新 {results.get('updated', 0)} 个，失败 {results.get('failed', 0)} 个，跳过 {results.get('skipped', 0)} 个")

    elif args.command == 'setup':
        print("🔧 设置自动化同步...")
        setup_script = Path(__file__).parent / 'setup_automation.sh'
        if setup_script.exists():
            os.system(f'bash {setup_script}')
        else:
            print("❌ 设置脚本不存在")
            sys.exit(1)

if __name__ == "__main__":
    main()
