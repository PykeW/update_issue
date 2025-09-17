#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab进度监控集成脚本
集成到主程序中的进度监控功能
"""

import sys
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from gitlab_tools.core.progress_monitor import ProgressMonitor
from gitlab_tools.utils.helpers import setup_logging

class ProgressMonitoringService:
    """进度监控服务"""

    def __init__(self):
        self.monitor = ProgressMonitor()
        self.logger = setup_logging('progress_monitor')

    def run_single_monitoring(self) -> Dict[str, int]:
        """运行单次进度监控"""
        self.logger.info("🔍 开始单次进度监控...")

        try:
            results = self.monitor.run_single_check()

            self.logger.info(f"📊 进度监控完成: 更新 {results.get('updated', 0)} 个，失败 {results.get('failed', 0)} 个，跳过 {results.get('skipped', 0)} 个")

            return results

        except Exception as e:
            self.logger.error(f"❌ 进度监控时发生错误: {str(e)}")
            return {'updated': 0, 'failed': 0, 'skipped': 0}

    def run_continuous_monitoring(self, interval: int = 300):
        """运行持续进度监控"""
        self.logger.info(f"🔄 开始持续进度监控，间隔: {interval}秒")

        try:
            self.monitor.run_continuous_monitoring(interval)
        except Exception as e:
            self.logger.error(f"❌ 持续监控时发生错误: {str(e)}")

    def get_monitoring_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        try:
            stats = self.monitor.get_monitoring_stats()
            return stats
        except Exception as e:
            self.logger.error(f"❌ 获取监控状态失败: {str(e)}")
            return {'error': str(e)}

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='GitLab进度监控集成脚本')
    parser.add_argument('action', choices=['monitor', 'continuous', 'status'], help='操作类型')
    parser.add_argument('--interval', type=int, default=300, help='持续监控间隔（秒）')

    args = parser.parse_args()

    service = ProgressMonitoringService()

    if args.action == 'monitor':
        results = service.run_single_monitoring()
        print(f"📊 监控结果: {results}")

    elif args.action == 'continuous':
        service.run_continuous_monitoring(args.interval)

    elif args.action == 'status':
        status = service.get_monitoring_status()
        print("📊 监控状态:")
        for key, value in status.items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    main()
