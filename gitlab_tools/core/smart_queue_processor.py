#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能队列处理器
高效处理同步队列，支持优先级、重试、批量处理
"""

from datetime import datetime
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from database_manager import DatabaseManager
from gitlab_operations import GitLabOperations
from config_manager import ConfigManager

class SmartQueueProcessor:
    """智能队列处理器"""

    def __init__(self, max_workers: int = 3):
        self.db_manager = DatabaseManager()
        self.gitlab_ops = GitLabOperations()
        self.config_manager = ConfigManager()
        self.max_workers = max_workers
        self.processing_lock = threading.Lock()

    def get_ready_tasks(self, batch_size: int = 10, max_priority: int = 5) -> List[Dict]:
        """获取准备执行的任务"""
        query = """
            SELECT id, issue_id, action, priority, retry_count, max_retries, metadata
            FROM sync_queue
            WHERE status = 'pending'
            AND priority <= %s
            AND scheduled_at <= NOW()
            ORDER BY priority ASC, created_at ASC
            LIMIT %s
        """

        tasks = self.db_manager.execute_query(query.replace('%s', str(max_priority)).replace('%s', str(batch_size)))
        return tasks or []

    def mark_task_processing(self, task_id: int) -> bool:
        """标记任务为处理中"""
        query = """
            UPDATE sync_queue
            SET status = 'processing', processed_at = NOW()
            WHERE id = %s AND status = 'pending'
        """

        return self.db_manager.execute_update(query, (task_id,))

    def mark_task_completed(self, task_id: int, result: Dict = None):
        """标记任务为完成"""
        query = """
            UPDATE sync_queue
            SET status = 'completed', processed_at = NOW()
            WHERE id = %s
        """

        self.db_manager.execute_update(query, (task_id,))

        # 记录统计信息
        if result:
            self._update_statistics(result)

    def mark_task_failed(self, task_id: int, error_message: str, retry: bool = True):
        """标记任务为失败"""
        if retry:
            # 检查是否可以重试
            query = """
                SELECT retry_count, max_retries FROM sync_queue WHERE id = %s
            """
            result = self.db_manager.execute_query(query, (task_id,))

            if result:
                retry_count = result[0]['retry_count']
                max_retries = result[0]['max_retries']

                if retry_count < max_retries:
                    # 重试
                    retry_delay = min(300, 60 * (2 ** retry_count))  # 指数退避
                    query = """
                        UPDATE sync_queue
                        SET status = 'retry',
                            retry_count = retry_count + 1,
                            scheduled_at = DATE_ADD(NOW(), INTERVAL %s SECOND),
                            error_message = %s
                        WHERE id = %s
                    """
                    self.db_manager.execute_update(query, (retry_delay, error_message, task_id))
                    return

        # 标记为最终失败
        query = """
            UPDATE sync_queue
            SET status = 'failed',
                processed_at = NOW(),
                error_message = %s
            WHERE id = %s
        """
        self.db_manager.execute_update(query, (error_message, task_id))

    def process_single_task(self, task: Dict) -> Dict:
        """处理单个任务"""
        task_id = task['id']
        issue_id = task['issue_id']
        action = task['action']
        # metadata = json.loads(task.get('metadata', '{}'))  # 暂时未使用

        try:
            # 获取议题详情
            issue_data = self.db_manager.get_issue_by_id(issue_id)
            if not issue_data:
                raise Exception(f"议题 #{issue_id} 不存在")

            result = {'task_id': task_id, 'action': action, 'success': False}

            if action == 'create':
                result = self._create_gitlab_issue(issue_data, task_id)
            elif action == 'update':
                result = self._update_gitlab_issue(issue_data, task_id)
            elif action == 'close':
                result = self._close_gitlab_issue(issue_data, task_id)
            elif action == 'sync_progress':
                result = self._sync_gitlab_progress(issue_data, task_id)
            else:
                raise Exception(f"未知的操作类型: {action}")

            return result

        except Exception as e:
            error_msg = f"处理任务失败: {str(e)}"
            print(f"❌ 任务 #{task_id} 失败: {error_msg}")
            return {
                'task_id': task_id,
                'action': action,
                'success': False,
                'error': error_msg
            }

    def _create_gitlab_issue(self, issue_data: Dict, task_id: int) -> Dict:
        """创建GitLab议题"""
        try:
            result = self.gitlab_ops.create_issue(
                issue_data,
                self.config_manager.get_gitlab_config(),
                self.config_manager.get_user_mapping()
            )

            if result and result.get('success', False):
                # 更新数据库
                self.db_manager.update_issue_gitlab_info(
                    issue_data['id'],
                    result['url'],
                    result.get('progress', ''),
                    'synced'
                )

                return {
                    'task_id': task_id,
                    'action': 'create',
                    'success': True,
                    'gitlab_url': result['url']
                }
            else:
                error_msg = result.get('error', '创建失败') if result else '创建失败'
                raise Exception(error_msg)

        except Exception as e:
            raise Exception(f"创建GitLab议题失败: {str(e)}")

    def _update_gitlab_issue(self, issue_data: Dict, task_id: int) -> Dict:
        """更新GitLab议题"""
        try:
            gitlab_issue_id = self.gitlab_ops.extract_issue_id_from_url(issue_data.get('gitlab_url', ''))
            if not gitlab_issue_id:
                raise Exception("无法提取GitLab议题ID")

            success = self.gitlab_ops.update_issue(gitlab_issue_id, issue_data)

            if success:
                return {
                    'task_id': task_id,
                    'action': 'update',
                    'success': True,
                    'gitlab_id': gitlab_issue_id
                }
            else:
                raise Exception("更新GitLab议题失败")

        except Exception as e:
            raise Exception(f"更新GitLab议题失败: {str(e)}")

    def _close_gitlab_issue(self, issue_data: Dict, task_id: int) -> Dict:
        """关闭GitLab议题"""
        try:
            gitlab_issue_id = self.gitlab_ops.extract_issue_id_from_url(issue_data.get('gitlab_url', ''))
            if not gitlab_issue_id:
                raise Exception("无法提取GitLab议题ID")

            success = self.gitlab_ops.close_issue(gitlab_issue_id, issue_data)

            if success:
                # 清除进度信息
                self.db_manager.update_issue_progress(issue_data['id'], '')

                return {
                    'task_id': task_id,
                    'action': 'close',
                    'success': True,
                    'gitlab_id': gitlab_issue_id
                }
            else:
                raise Exception("关闭GitLab议题失败")

        except Exception as e:
            raise Exception(f"关闭GitLab议题失败: {str(e)}")

    def _sync_gitlab_progress(self, issue_data: Dict, task_id: int) -> Dict:
        """同步GitLab进度"""
        try:
            gitlab_issue_id = self.gitlab_ops.extract_issue_id_from_url(issue_data.get('gitlab_url', ''))
            if not gitlab_issue_id:
                raise Exception("无法提取GitLab议题ID")

            # 获取GitLab议题信息
            gitlab_issue = self.gitlab_ops.manager.get_issue(gitlab_issue_id)
            if not gitlab_issue:
                raise Exception("无法获取GitLab议题信息")

            # 提取进度信息
            progress = self.gitlab_ops.extract_progress_from_labels(gitlab_issue.get('labels', []))

            # 更新数据库
            self.db_manager.update_issue_progress(issue_data['id'], progress)

            return {
                'task_id': task_id,
                'action': 'sync_progress',
                'success': True,
                'progress': progress
            }

        except Exception as e:
            raise Exception(f"同步GitLab进度失败: {str(e)}")

    def _update_statistics(self, result: Dict):
        """更新统计信息"""
        try:
            today = datetime.now().date()
            action = result['action']
            success = result['success']

            # 使用存储过程更新统计
            query = """
                INSERT INTO sync_statistics (date, action_type, success_count, failure_count)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    success_count = success_count + VALUES(success_count),
                    failure_count = failure_count + VALUES(failure_count)
            """

            success_count = 1 if success else 0
            failure_count = 0 if success else 1

            self.db_manager.execute_update(query, (today, action, success_count, failure_count))

        except Exception as e:
            print(f"⚠️ 更新统计信息失败: {str(e)}")

    def process_batch(self, batch_size: int = 10, max_priority: int = 5) -> Dict:
        """批量处理任务"""
        with self.processing_lock:
            # 获取准备执行的任务
            tasks = self.get_ready_tasks(batch_size, max_priority)

            if not tasks:
                return {'processed': 0, 'success': 0, 'failed': 0, 'retry': 0}

            print(f"🔄 开始处理 {len(tasks)} 个任务...")

            results = {'processed': 0, 'success': 0, 'failed': 0, 'retry': 0}

            # 使用线程池并发处理
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交任务
                future_to_task = {}
                for task in tasks:
                    task_id = task['id']

                    # 标记为处理中
                    if self.mark_task_processing(task_id):
                        future = executor.submit(self.process_single_task, task)
                        future_to_task[future] = task
                    else:
                        print(f"⚠️ 无法标记任务 #{task_id} 为处理中")

                # 处理结果
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    task_id = task['id']

                    try:
                        result = future.result()
                        results['processed'] += 1

                        if result['success']:
                            self.mark_task_completed(task_id, result)
                            results['success'] += 1
                            print(f"✅ 任务 #{task_id} 完成: {result['action']}")
                        else:
                            error_msg = result.get('error', '处理失败')
                            self.mark_task_failed(task_id, error_msg)
                            results['failed'] += 1
                            print(f"❌ 任务 #{task_id} 失败: {error_msg}")

                    except Exception as e:
                        error_msg = f"处理异常: {str(e)}"
                        self.mark_task_failed(task_id, error_msg)
                        results['failed'] += 1
                        print(f"❌ 任务 #{task_id} 异常: {error_msg}")

            return results

    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        query = """
            SELECT
                status,
                COUNT(*) as count,
                AVG(TIMESTAMPDIFF(SECOND, created_at, COALESCE(processed_at, NOW()))) as avg_processing_time
            FROM sync_queue
            GROUP BY status
        """

        status_data = self.db_manager.execute_query(query)

        status_summary = {}
        for row in status_data:
            status_summary[row['status']] = {
                'count': row['count'],
                'avg_processing_time': row['avg_processing_time'] or 0
            }

        return status_summary

    def cleanup_old_tasks(self, days_to_keep: int = 30):
        """清理旧任务"""
        try:
            query = "CALL CleanupSyncData(%s)"
            result = self.db_manager.execute_query(query, (days_to_keep,))

            if result:
                print(f"✅ 清理完成，保留 {days_to_keep} 天的数据")
            else:
                print("⚠️ 清理操作完成，但无返回结果")

        except Exception as e:
            print(f"❌ 清理操作失败: {str(e)}")

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='智能队列处理器')
    parser.add_argument('action', choices=['process', 'status', 'cleanup'], help='操作类型')
    parser.add_argument('--batch-size', type=int, default=10, help='批处理大小')
    parser.add_argument('--max-priority', type=int, default=5, help='最大优先级')
    parser.add_argument('--workers', type=int, default=3, help='并发工作线程数')
    parser.add_argument('--days', type=int, default=30, help='清理时保留的天数')

    args = parser.parse_args()

    processor = SmartQueueProcessor(max_workers=args.workers)

    if args.action == 'process':
        result = processor.process_batch(args.batch_size, args.max_priority)
        print(f"📊 处理结果: {result}")
    elif args.action == 'status':
        status = processor.get_queue_status()
        print("📋 队列状态:")
        for status_name, data in status.items():
            print(f"  {status_name}: {data['count']} 个任务, 平均处理时间: {data['avg_processing_time']:.2f}秒")
    elif args.action == 'cleanup':
        processor.cleanup_old_tasks(args.days)

if __name__ == "__main__":
    main()
