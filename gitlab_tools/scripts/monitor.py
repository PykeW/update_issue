#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统监控和日志记录脚本
提供实时监控、日志分析和告警功能
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from gitlab_tools.core.database_manager import DatabaseManager
from gitlab_tools.core.config_manager import ConfigManager

class SystemMonitor:
    """系统监控器"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config_manager = ConfigManager()
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """设置日志记录器"""
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)

        logger = logging.getLogger('system_monitor')
        logger.setLevel(logging.INFO)

        # 避免重复添加处理器
        if not logger.handlers:
            # 文件处理器
            file_handler = logging.FileHandler(
                log_dir / f"monitor_{datetime.now().strftime('%Y%m%d')}.log",
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)

            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # 格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

        return logger

    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'database': {},
            'sync_queue': {},
            'issues': {},
            'errors': []
        }

        try:
            # 数据库连接状态
            db_test = self.db_manager.execute_query("SELECT 1 as test")
            stats['database']['connected'] = bool(db_test)

            # 议题统计
            issues_query = """
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'open' THEN 1 END) as open_count,
                    COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_count,
                    COUNT(CASE WHEN gitlab_url IS NOT NULL AND gitlab_url != '' THEN 1 END) as synced_count,
                    COUNT(CASE WHEN sync_status = 'pending' THEN 1 END) as pending_sync_count
                FROM issues
            """
            issues_result = self.db_manager.execute_query(issues_query)
            if issues_result:
                stats['issues'] = issues_result[0]

            # 同步队列统计
            queue_query = """
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_count,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count
                FROM sync_queue
            """
            queue_result = self.db_manager.execute_query(queue_query)
            if queue_result:
                stats['sync_queue'] = queue_result[0]

            # 最近24小时的同步活动
            recent_query = """
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM sync_queue
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """
            recent_result = self.db_manager.execute_query(recent_query)
            stats['recent_activity'] = recent_result or []

        except Exception as e:
            stats['errors'].append(f"获取统计信息失败: {str(e)}")
            self.logger.error(f"获取统计信息失败: {str(e)}")

        return stats

    def check_system_health(self) -> Dict[str, Any]:
        """检查系统健康状态"""
        health = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'checks': {},
            'alerts': []
        }

        # 检查数据库连接
        try:
            db_test = self.db_manager.execute_query("SELECT 1 as test")
            health['checks']['database'] = {
                'status': 'ok' if db_test else 'error',
                'message': '数据库连接正常' if db_test else '数据库连接失败'
            }
        except Exception as e:
            health['checks']['database'] = {
                'status': 'error',
                'message': f'数据库连接异常: {str(e)}'
            }
            health['alerts'].append(f"数据库连接异常: {str(e)}")

        # 检查同步队列积压
        try:
            pending_query = "SELECT COUNT(*) as count FROM sync_queue WHERE status = 'pending'"
            pending_result = self.db_manager.execute_query(pending_query)
            pending_count = int(pending_result[0]['count']) if pending_result else 0

            health['checks']['sync_queue'] = {
                'status': 'ok' if pending_count < 50 else 'warning',
                'message': f'待处理队列: {pending_count} 条',
                'pending_count': pending_count
            }

            if pending_count > 100:
                health['alerts'].append(f"同步队列积压严重: {pending_count} 条待处理")
                health['status'] = 'warning'
        except Exception as e:
            health['checks']['sync_queue'] = {
                'status': 'error',
                'message': f'检查同步队列失败: {str(e)}'
            }
            health['alerts'].append(f"检查同步队列失败: {str(e)}")

        # 检查未同步的议题
        try:
            unsynced_query = """
                SELECT COUNT(*) as count
                FROM issues
                WHERE status = 'open'
                AND (gitlab_url IS NULL OR gitlab_url = '')
            """
            unsynced_result = self.db_manager.execute_query(unsynced_query)
            unsynced_count = int(unsynced_result[0]['count']) if unsynced_result else 0

            health['checks']['unsynced_issues'] = {
                'status': 'ok' if unsynced_count < 20 else 'warning',
                'message': f'未同步议题: {unsynced_count} 条',
                'unsynced_count': unsynced_count
            }

            if unsynced_count > 50:
                health['alerts'].append(f"未同步议题过多: {unsynced_count} 条")
                health['status'] = 'warning'
        except Exception as e:
            health['checks']['unsynced_issues'] = {
                'status': 'error',
                'message': f'检查未同步议题失败: {str(e)}'
            }
            health['alerts'].append(f"检查未同步议题失败: {str(e)}")

        # 检查日志文件大小
        try:
            log_dir = Path(__file__).parent.parent / "logs"
            if log_dir.exists():
                log_files = list(log_dir.glob("*.log"))
                total_size = sum(f.stat().st_size for f in log_files)
                size_mb = total_size / (1024 * 1024)

                health['checks']['log_files'] = {
                    'status': 'ok' if size_mb < 100 else 'warning',
                    'message': f'日志文件总大小: {size_mb:.2f} MB',
                    'size_mb': size_mb
                }

                if size_mb > 500:
                    health['alerts'].append(f"日志文件过大: {size_mb:.2f} MB")
                    health['status'] = 'warning'
            else:
                health['checks']['log_files'] = {
                    'status': 'ok',
                    'message': '日志目录不存在'
                }
        except Exception as e:
            health['checks']['log_files'] = {
                'status': 'error',
                'message': f'检查日志文件失败: {str(e)}'
            }

        # 确定整体状态
        if health['alerts']:
            if health['status'] == 'healthy':
                health['status'] = 'warning'

        return health

    def generate_report(self) -> str:
        """生成监控报告"""
        stats = self.get_system_stats()
        health = self.check_system_health()

        report = f"""
=== 系统监控报告 ===
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
整体状态: {health['status'].upper()}

=== 数据库状态 ===
连接状态: {'✅ 正常' if stats['database'].get('connected') else '❌ 异常'}

=== 议题统计 ===
总议题数: {stats['issues'].get('total', 0)}
开放议题: {stats['issues'].get('open_count', 0)}
已关闭议题: {stats['issues'].get('closed_count', 0)}
已同步议题: {stats['issues'].get('synced_count', 0)}
待同步议题: {stats['issues'].get('pending_sync_count', 0)}

=== 同步队列状态 ===
总队列数: {stats['sync_queue'].get('total', 0)}
待处理: {stats['sync_queue'].get('pending_count', 0)}
处理中: {stats['sync_queue'].get('processing_count', 0)}
已完成: {stats['sync_queue'].get('completed_count', 0)}
失败: {stats['sync_queue'].get('failed_count', 0)}

=== 健康检查结果 ===
"""

        for check_name, check_result in health['checks'].items():
            status_icon = '✅' if check_result['status'] == 'ok' else '⚠️' if check_result['status'] == 'warning' else '❌'
            report += f"{status_icon} {check_name}: {check_result['message']}\n"

        if health['alerts']:
            report += "\n=== 告警信息 ===\n"
            for alert in health['alerts']:
                report += f"⚠️ {alert}\n"

        if stats['errors']:
            report += "\n=== 错误信息 ===\n"
            for error in stats['errors']:
                report += f"❌ {error}\n"

        return report

    def log_system_event(self, event_type: str, message: str, data: Optional[Dict] = None):
        """记录系统事件"""
        # 这里可以添加事件记录逻辑
        self.logger.info(f"系统事件: {event_type} - {message}")

        self.logger.info(f"[{event_type}] {message}")

        # 保存到数据库（如果有事件日志表）
        try:
            # 这里可以添加事件日志到数据库的逻辑
            pass
        except Exception as e:
            self.logger.error(f"保存事件日志失败: {str(e)}")

def main():
    """主函数"""
    monitor = SystemMonitor()

    # 生成并打印报告
    report = monitor.generate_report()
    print(report)

    # 记录监控事件
    monitor.log_system_event('monitor', '系统监控检查完成')

if __name__ == "__main__":
    main()
