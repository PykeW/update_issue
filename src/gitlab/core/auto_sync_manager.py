#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化同步管理器
统一管理所有GitLab同步功能
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.gitlab.core.database_manager import DatabaseManager
from src.gitlab.core.gitlab_operations import GitLabOperations
from src.gitlab.core.config_manager import ConfigManager
from src.utils.helpers import setup_logging

class AutoSyncManager:
    """自动化同步管理器"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config_manager = ConfigManager()
        self.logger = setup_logging('auto_sync')

        # 加载配置
        self.gitlab_config = self.config_manager.load_gitlab_config()
        self.user_mapping_config = self.config_manager.load_user_mapping()
        self.user_mapping = self.user_mapping_config.get('user_mapping', {}) if self.user_mapping_config else {}

        # 初始化GitLab操作
        self.gitlab_ops = GitLabOperations()

    def sync_new_issues(self) -> Dict[str, int]:
        """同步新议题到GitLab"""
        self.logger.info("🔄 开始同步新议题...")

        try:
            # 获取需要同步的议题
            issues = self.db_manager.execute_query('''
                SELECT id, project_name, problem_category, severity_level, problem_description,
                       solution, action_priority, action_record, initiator, responsible_person,
                       status, start_time, target_completion_time, actual_completion_time,
                       remarks, gitlab_url, sync_status, last_sync_time, gitlab_progress
                FROM issues
                WHERE (gitlab_url IS NULL OR gitlab_url = '')
                AND status = 'open'
                AND (sync_status IS NULL OR sync_status = 'pending' OR sync_status = 'failed')
                ORDER BY id
                LIMIT 50
            ''')

            if not issues:
                self.logger.info("✅ 没有需要同步的新议题")
                return {'created': 0, 'failed': 0}

            self.logger.info(f"📋 找到 {len(issues)} 个需要同步的议题")

            created = 0
            failed = 0

            for issue in issues:
                try:
                    self.logger.info(f"🔍 处理议题 #{issue['id']}: {issue['project_name']}")

                    # 创建GitLab议题
                    result = self.gitlab_ops.create_issue(issue, self.gitlab_config or {}, self.user_mapping)

                    if result and result.get('success', False):
                        # 更新数据库
                        self.db_manager.update_issue_gitlab_info(
                            issue['id'],
                            result['url'],
                            result.get('progress', ''),
                            'synced'
                        )
                        created += 1
                        self.logger.info(f"✅ 议题 #{issue['id']} 同步成功: {result['url']}")
                    else:
                        # 更新失败状态
                        self.db_manager.execute_update(f'''
                            UPDATE issues SET
                                sync_status = 'failed',
                                last_sync_time = NOW()
                            WHERE id = {issue['id']}
                        ''')
                        failed += 1
                        error_msg = result.get('error', '未知错误') if result else '创建失败'
                        self.logger.error(f"❌ 议题 #{issue['id']} 同步失败: {error_msg}")

                except Exception as e:
                    self.logger.error(f"❌ 处理议题 #{issue['id']} 时发生异常: {str(e)}")
                    failed += 1

            return {'created': created, 'failed': failed}

        except Exception as e:
            self.logger.error(f"❌ 同步新议题时发生异常: {str(e)}")
            return {'created': 0, 'failed': 0}

    def sync_progress(self) -> Dict[str, int]:
        """同步GitLab进度到数据库"""
        self.logger.info("🔄 开始同步进度...")

        try:
            # 获取所有有GitLab URL的议题
            issues = self.db_manager.execute_query('''
                SELECT id, project_name, gitlab_url, status, gitlab_progress
                FROM issues
                WHERE gitlab_url IS NOT NULL AND gitlab_url != ''
                ORDER BY id
            ''')

            if not issues:
                self.logger.info("✅ 没有需要同步进度的议题")
                return {'updated': 0, 'skipped': 0, 'failed': 0, 'closed': 0}

            self.logger.info(f"📋 找到 {len(issues)} 个有GitLab URL的议题")

            updated = 0
            skipped = 0
            failed = 0
            closed = 0

            for issue in issues:
                try:
                    self.logger.info(f"🔍 处理议题 #{issue['id']}: {issue['project_name']}")

                    # 提取议题ID
                    issue_id = self.gitlab_ops.extract_issue_id_from_url(issue['gitlab_url'])
                    if not issue_id:
                        self.logger.warning(f"⚠️ 无法从URL提取议题ID: {issue['gitlab_url']}")
                        continue

                    # 获取GitLab议题详情
                    gitlab_issue = self.gitlab_ops.get_issue(issue_id)
                    if not gitlab_issue:
                        self.logger.warning(f"⚠️ 无法获取GitLab议题 #{issue_id}")
                        continue

                    # 提取进度标签
                    gitlab_progress = self.gitlab_ops.get_issue_progress(gitlab_issue)
                    current_progress = issue.get('gitlab_progress', '')

                    # 检查数据库状态
                    if issue['status'] == 'closed':
                        # 关闭GitLab议题
                        if self.gitlab_ops.close_issue(issue_id, issue):
                            self.db_manager.update_issue_progress(issue['id'], '')
                            closed += 1
                            self.logger.info(f"🔒 议题 #{issue['id']} 已关闭")
                        else:
                            failed += 1
                            self.logger.error(f"❌ 关闭议题 #{issue['id']} 失败")
                    else:
                        # 同步进度
                        if gitlab_progress != current_progress:
                            self.db_manager.update_issue_progress(issue['id'], gitlab_progress)
                            updated += 1
                            self.logger.info(f"🔄 更新进度: {current_progress} → {gitlab_progress}")
                        else:
                            skipped += 1
                            self.logger.info(f"⏭️ 进度无变化，跳过")

                except Exception as e:
                    self.logger.error(f"❌ 处理议题 #{issue['id']} 时发生异常: {str(e)}")
                    failed += 1

            return {'updated': updated, 'skipped': skipped, 'failed': failed, 'closed': closed}

        except Exception as e:
            self.logger.error(f"❌ 同步进度时发生异常: {str(e)}")
            return {'updated': 0, 'skipped': 0, 'failed': 0, 'closed': 0}

    def process_sync_queue(self) -> Dict[str, int]:
        """处理同步队列"""
        self.logger.info("🔄 开始处理同步队列...")

        try:
            # 获取待处理的队列项
            queue_items = self.db_manager.execute_query('''
                SELECT id, issue_id, action, created_at
                FROM sync_queue
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT 20
            ''')

            if not queue_items:
                self.logger.info("✅ 没有待处理的同步队列项")
                return {'processed': 0, 'failed': 0}

            self.logger.info(f"📋 找到 {len(queue_items)} 个待处理的队列项")

            processed = 0
            failed = 0

            for item in queue_items:
                try:
                    queue_id = item['id']
                    issue_id = item['issue_id']
                    operation = item['action']

                    self.logger.info(f"🔍 处理队列项 #{queue_id}: {operation} 议题 #{issue_id}")

                    # 获取议题详情
                    issue = self.db_manager.get_issue_by_id(issue_id)
                    if not issue:
                        self.logger.error(f"❌ 未找到议题 #{issue_id}")
                        self.db_manager.update_queue_status(queue_id, 'failed', '议题不存在')
                        failed += 1
                        continue

                    if operation == 'create':
                        # 创建GitLab议题
                        result = self.gitlab_ops.create_issue(issue, self.gitlab_config or {}, self.user_mapping)
                        if result and result.get('success', False):
                            self.db_manager.update_issue_gitlab_info(
                                issue_id,
                                result['url'],
                                result.get('progress', ''),
                                'synced'
                            )
                            self.db_manager.update_queue_status(queue_id, 'completed')
                            processed += 1
                            self.logger.info(f"✅ 队列项 #{queue_id} 处理成功")
                        else:
                            error_msg = result.get('error', '创建失败') if result else '创建失败'
                            self.db_manager.update_queue_status(queue_id, 'failed', error_msg)
                            failed += 1
                            self.logger.error(f"❌ 队列项 #{queue_id} 处理失败")

                    elif operation == 'close':
                        # 关闭GitLab议题
                        gitlab_issue_id = self.gitlab_ops.extract_issue_id_from_url(issue.get('gitlab_url', ''))
                        if gitlab_issue_id:
                            if self.gitlab_ops.close_issue(gitlab_issue_id, issue):
                                self.db_manager.update_issue_progress(issue_id, '')
                                self.db_manager.update_queue_status(queue_id, 'completed')
                                processed += 1
                                self.logger.info(f"✅ 队列项 #{queue_id} 处理成功")
                            else:
                                self.db_manager.update_queue_status(queue_id, 'failed', '关闭失败')
                                failed += 1
                                self.logger.error(f"❌ 队列项 #{queue_id} 处理失败")
                        else:
                            self.db_manager.update_queue_status(queue_id, 'failed', '无效的GitLab URL')
                            failed += 1
                            self.logger.error(f"❌ 队列项 #{queue_id} 处理失败: 无效的GitLab URL")

                except Exception as e:
                    self.logger.error(f"❌ 处理队列项 #{item['id']} 时发生异常: {str(e)}")
                    self.db_manager.update_queue_status(item['id'], 'failed', str(e))
                    failed += 1

            return {'processed': processed, 'failed': failed}

        except Exception as e:
            self.logger.error(f"❌ 处理同步队列时发生异常: {str(e)}")
            return {'processed': 0, 'failed': 0}

    def run_full_sync(self) -> Dict[str, Any]:
        """运行完整同步流程"""
        start_time = datetime.now()
        self.logger.info("=" * 60)
        self.logger.info("🚀 开始自动化同步流程")
        self.logger.info(f"⏰ 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 60)

        # 1. 处理同步队列
        queue_result = self.process_sync_queue()
        self.logger.info(f"📊 队列处理结果: 处理 {queue_result['processed']} 个，失败 {queue_result['failed']} 个")

        # 2. 同步新议题
        new_issues_result = self.sync_new_issues()
        self.logger.info(f"📊 新议题同步结果: 创建 {new_issues_result['created']} 个，失败 {new_issues_result['failed']} 个")

        # 3. 同步进度
        progress_result = self.sync_progress()
        self.logger.info(f"📊 进度同步结果: 更新 {progress_result['updated']} 个，跳过 {progress_result['skipped']} 个，失败 {progress_result['failed']} 个，关闭 {progress_result['closed']} 个")

        # 4. 生成总结报告
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        self.logger.info("=" * 60)
        self.logger.info("📊 同步完成总结")
        self.logger.info(f"⏰ 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"⏱️ 总耗时: {duration:.2f} 秒")
        self.logger.info(f"📋 队列处理: {queue_result['processed']} 成功, {queue_result['failed']} 失败")
        self.logger.info(f"🆕 新议题: {new_issues_result['created']} 创建, {new_issues_result['failed']} 失败")
        self.logger.info(f"🔄 进度同步: {progress_result['updated']} 更新, {progress_result['skipped']} 跳过, {progress_result['failed']} 失败, {progress_result['closed']} 关闭")
        self.logger.info("=" * 60)

        return {
            'queue': queue_result,
            'new_issues': new_issues_result,
            'progress': progress_result,
            'duration': duration
        }
