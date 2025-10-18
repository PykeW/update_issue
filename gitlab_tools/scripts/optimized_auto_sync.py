#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版自动化同步脚本
集成智能变更检测和队列处理
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Union

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from gitlab_tools.core.change_detector import ChangeDetector
from gitlab_tools.core.smart_queue_processor import SmartQueueProcessor
from gitlab_tools.core.database_manager import DatabaseManager
from gitlab_tools.utils.helpers import setup_logging

class OptimizedAutoSync:
    """优化版自动化同步器"""

    def __init__(self):
        self.change_detector = ChangeDetector()
        self.queue_processor = SmartQueueProcessor()
        self.db_manager = DatabaseManager()
        self.logger = setup_logging('optimized_auto_sync')

    def run_single_sync(self, batch_size: int = 10) -> Dict:
        """运行单次同步"""
        self.logger.info("🚀 开始优化版单次同步...")

        start_time = datetime.now()
        results = {
            'changes_detected': 0,
            'queue_processed': {'processed': 0, 'success': 0, 'failed': 0},
            'duration': 0
        }

        try:
            # 1. 检测变更
            self.logger.info("🔍 检测数据库变更...")
            changes_count = self.change_detector.run_single_check()
            results['changes_detected'] = changes_count

            # 2. 处理队列
            self.logger.info("🔄 处理同步队列...")
            queue_result = self.queue_processor.process_batch(batch_size)
            results['queue_processed'] = queue_result

            # 3. 计算耗时
            duration = (datetime.now() - start_time).total_seconds()
            results['duration'] = duration

            self.logger.info(f"✅ 同步完成，耗时: {duration:.2f}秒")
            self.logger.info(f"📊 变更检测: {changes_count} 个")
            self.logger.info(f"📊 队列处理: {queue_result}")

        except Exception as e:
            self.logger.error(f"❌ 同步过程中发生错误: {str(e)}")
            results['error'] = str(e)

        return results

    def run_continuous_sync(self, interval: int = 30, batch_size: int = 10):
        """运行持续同步"""
        self.logger.info(f"🔄 开始持续同步模式，间隔: {interval}秒")

        try:
            while True:
                # 运行单次同步
                result = self.run_single_sync(batch_size)

                # 记录统计信息
                self._log_sync_statistics(result)

                # 等待下次同步
                self.logger.info(f"⏰ 等待 {interval} 秒后进行下次同步...")
                time.sleep(interval)

        except KeyboardInterrupt:
            self.logger.info("🛑 持续同步已停止")
        except Exception as e:
            self.logger.error(f"❌ 持续同步过程中发生错误: {str(e)}")

    def run_change_monitoring(self, interval: int = 10):
        """运行变更监控模式"""
        self.logger.info(f"👁️ 开始变更监控模式，间隔: {interval}秒")

        try:
            self.change_detector.run_continuous_monitoring(interval)
        except KeyboardInterrupt:
            self.logger.info("🛑 变更监控已停止")
        except Exception as e:
            self.logger.error(f"❌ 变更监控过程中发生错误: {str(e)}")

    def run_queue_processing(self, interval: int = 60, batch_size: int = 10):
        """运行队列处理模式"""
        self.logger.info(f"⚙️ 开始队列处理模式，间隔: {interval}秒")

        try:
            while True:
                # 处理队列
                result = self.queue_processor.process_batch(batch_size)

                if result['processed'] > 0:
                    self.logger.info(f"📊 队列处理结果: {result}")
                else:
                    self.logger.info("✅ 队列为空，无需处理")

                # 等待下次处理
                time.sleep(interval)

        except KeyboardInterrupt:
            self.logger.info("🛑 队列处理已停止")
        except Exception as e:
            self.logger.error(f"❌ 队列处理过程中发生错误: {str(e)}")

    def get_system_status(self) -> Dict:
        """获取系统状态"""
        try:
            # 获取队列状态
            queue_status = self.queue_processor.get_queue_status()

            # 获取数据库统计
            db_stats = self._get_database_stats()

            # 获取最近同步统计
            sync_stats = self._get_sync_statistics()

            return {
                'queue_status': queue_status,
                'database_stats': db_stats,
                'sync_statistics': sync_stats,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"❌ 获取系统状态失败: {str(e)}")
            return {'error': str(e)}

    def _get_database_stats(self) -> Dict:
        """获取数据库统计"""
        try:
            query = """
                SELECT
                    COUNT(*) as total_issues,
                    COUNT(CASE WHEN status = 'open' THEN 1 END) as open_issues,
                    COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_issues,
                    COUNT(CASE WHEN gitlab_url IS NOT NULL AND gitlab_url != '' THEN 1 END) as synced_issues
                FROM issues
            """

            result = self.db_manager.execute_query(query)
            return result[0] if result else {}

        except Exception as e:
            return {'error': str(e)}

    def _get_sync_statistics(self) -> Union[List[Dict[str, Any]], Dict[str, str]]:
        """获取同步统计"""
        try:
            query = """
                SELECT
                    action_type,
                    SUM(success_count) as total_success,
                    SUM(failure_count) as total_failure,
                    AVG(avg_processing_time) as avg_time
                FROM sync_statistics
                WHERE date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY action_type
            """

            result = self.db_manager.execute_query(query)
            return result if result else []

        except Exception as e:
            return {'error': str(e)}

    def _log_sync_statistics(self, result: Dict):
        """记录同步统计"""
        try:
            # 这里可以添加统计记录逻辑
            pass
        except Exception as e:
            self.logger.error(f"⚠️ 记录统计信息失败: {str(e)}")

    def cleanup_system(self, days_to_keep: int = 30):
        """清理系统数据"""
        self.logger.info(f"🧹 开始清理系统数据，保留 {days_to_keep} 天...")

        try:
            # 清理队列数据
            self.queue_processor.cleanup_old_tasks(days_to_keep)

            # 清理变更日志
            query = f"""
                DELETE FROM issue_changes
                WHERE change_timestamp < DATE_SUB(NOW(), INTERVAL {days_to_keep} DAY)
                AND processed = TRUE
            """
            self.db_manager.execute_update(query)

            self.logger.info("✅ 系统清理完成")

        except Exception as e:
            self.logger.error(f"❌ 系统清理失败: {str(e)}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='优化版自动化同步脚本')
    parser.add_argument('mode', choices=[
        'single', 'continuous', 'monitor', 'queue', 'status', 'cleanup'
    ], help='运行模式')

    parser.add_argument('--interval', type=int, default=30,
                       help='持续模式间隔（秒）')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='批处理大小')
    parser.add_argument('--days', type=int, default=30,
                       help='清理时保留的天数')

    args = parser.parse_args()

    sync = OptimizedAutoSync()

    if args.mode == 'single':
        result = sync.run_single_sync(args.batch_size)
        print(f"📊 同步结果: {result}")

    elif args.mode == 'continuous':
        sync.run_continuous_sync(args.interval, args.batch_size)

    elif args.mode == 'monitor':
        sync.run_change_monitoring(args.interval)

    elif args.mode == 'queue':
        sync.run_queue_processing(args.interval, args.batch_size)

    elif args.mode == 'status':
        status = sync.get_system_status()
        print("📋 系统状态:")
        print(f"  队列状态: {status.get('queue_status', {})}")
        print(f"  数据库统计: {status.get('database_stats', {})}")
        print(f"  同步统计: {status.get('sync_statistics', {})}")

    elif args.mode == 'cleanup':
        sync.cleanup_system(args.days)

if __name__ == "__main__":
    main()
