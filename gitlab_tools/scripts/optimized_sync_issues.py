#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版议题同步脚本
支持多人指派、智能映射、详细日志
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from gitlab_tools.core.database_manager import DatabaseManager
from gitlab_tools.core.gitlab_operations import GitLabOperations
from gitlab_tools.core.config_manager import ConfigManager
from gitlab_tools.utils.helpers import setup_logging

class OptimizedIssueSyncer:
    """优化版议题同步器"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config_manager = ConfigManager()
        self.logger = setup_logging('optimized_sync')

        # 加载配置
        self.gitlab_config = self.config_manager.load_gitlab_config()
        self.user_mapping_config = self.config_manager.load_user_mapping()
        self.user_mapping = self.user_mapping_config.get('user_mapping', {}) if self.user_mapping_config else {}

        # 初始化GitLab操作
        self.gitlab_ops = GitLabOperations()

        self.stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'failed': 0,
            'skipped': 0,
            'assignee_stats': {}
        }

    def sync_new_issues(self, limit: int = 20) -> Dict[str, int]:
        """同步新议题到GitLab"""
        self.logger.info("🔄 开始同步新议题...")

        try:
            # 获取需要同步的议题
            issues = self.db_manager.execute_query(f'''
                SELECT id, project_name, problem_category, severity_level, problem_description,
                       solution, action_priority, action_record, initiator, responsible_person,
                       status, start_time, target_completion_time, actual_completion_time,
                       remarks, gitlab_url, sync_status, last_sync_time, gitlab_progress
                FROM issues
                WHERE (gitlab_url IS NULL OR gitlab_url = '')
                AND status = 'open'
                AND (sync_status IS NULL OR sync_status = 'pending' OR sync_status = 'failed')
                ORDER BY id
                LIMIT {limit}
            ''')

            if not issues:
                self.logger.info("✅ 没有需要同步的新议题")
                return {'created': 0, 'failed': 0, 'skipped': 0}

            self.logger.info(f"📋 找到 {len(issues)} 个需要同步的议题")

            for issue in issues:
                self.stats['total_processed'] += 1
                try:
                    self.logger.info(f"🔍 处理议题 #{issue['id']}: {issue['project_name']}")

                    # 记录责任人信息
                    responsible_person = issue.get('responsible_person', '')
                    if responsible_person:
                        self._record_assignee_stats(responsible_person)

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
                        self.stats['created'] += 1
                        self.logger.info(f"✅ 议题 #{issue['id']} 同步成功: {result['url']}")

                        # 记录指派信息
                        assignee_count = result.get('assignee_count', 0)
                        not_found_users = result.get('not_found_users', [])
                        if assignee_count > 0:
                            self.logger.info(f"👥 指派了 {assignee_count} 个用户")
                        if not_found_users:
                            self.logger.warning(f"⚠️ 未找到映射的用户: {', '.join(not_found_users)}")

                    else:
                        # 更新失败状态
                        self.db_manager.execute_update(f'''
                            UPDATE issues SET
                                sync_status = 'failed',
                                last_sync_time = NOW()
                            WHERE id = {issue['id']}
                        ''')
                        self.stats['failed'] += 1
                        error_msg = result.get('error', '未知错误') if result else '创建失败'
                        self.logger.error(f"❌ 议题 #{issue['id']} 同步失败: {error_msg}")

                except Exception as e:
                    self.logger.error(f"❌ 处理议题 #{issue['id']} 时发生异常: {str(e)}")
                    self.stats['failed'] += 1

            return {'created': self.stats['created'], 'failed': self.stats['failed'], 'skipped': self.stats['skipped']}

        except Exception as e:
            self.logger.error(f"❌ 同步新议题时发生异常: {str(e)}")
            return {'created': 0, 'failed': 0, 'skipped': 0}

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

    def _record_assignee_stats(self, responsible_person: str):
        """记录指派人统计信息"""
        if responsible_person not in self.stats['assignee_stats']:
            self.stats['assignee_stats'][responsible_person] = 0
        self.stats['assignee_stats'][responsible_person] += 1

    def generate_sync_report(self) -> str:
        """生成同步报告"""
        report = f"""
=== 优化版议题同步报告 ===
同步时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
总处理数: {self.stats['total_processed']}
创建成功: {self.stats['created']}
更新成功: {self.stats['updated']}
处理失败: {self.stats['failed']}
跳过数量: {self.stats['skipped']}

=== 指派人统计 ===
"""

        for person, count in sorted(self.stats['assignee_stats'].items(), key=lambda x: x[1], reverse=True):
            report += f"👤 {person}: {count} 个议题\n"

        return report

    def run_full_sync(self, limit: int = 20) -> Dict[str, Any]:
        """运行完整同步流程"""
        start_time = datetime.now()
        self.logger.info("=" * 60)
        self.logger.info("🚀 开始优化版议题同步流程")
        self.logger.info(f"⏰ 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 60)

        # 1. 同步新议题
        new_issues_result = self.sync_new_issues(limit)
        self.logger.info(f"📊 新议题同步结果: 创建 {new_issues_result['created']} 个，失败 {new_issues_result['failed']} 个")

        # 2. 同步进度
        progress_result = self.sync_progress()
        self.logger.info(f"📊 进度同步结果: 更新 {progress_result['updated']} 个，跳过 {progress_result['skipped']} 个，失败 {progress_result['failed']} 个，关闭 {progress_result['closed']} 个")

        # 3. 生成总结报告
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        self.logger.info("=" * 60)
        self.logger.info("📊 同步完成总结")
        self.logger.info(f"⏰ 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"⏱️ 总耗时: {duration:.2f} 秒")
        self.logger.info(f"🆕 新议题: {new_issues_result['created']} 创建, {new_issues_result['failed']} 失败")
        self.logger.info(f"🔄 进度同步: {progress_result['updated']} 更新, {progress_result['skipped']} 跳过, {progress_result['failed']} 失败, {progress_result['closed']} 关闭")
        self.logger.info("=" * 60)

        # 生成详细报告
        report = self.generate_sync_report()
        self.logger.info(report)

        return {
            'new_issues': new_issues_result,
            'progress': progress_result,
            'duration': duration,
            'stats': self.stats
        }

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='优化版议题同步工具')
    parser.add_argument('command', choices=['sync-new', 'sync-progress', 'sync-full'],
                       help='同步命令')
    parser.add_argument('--limit', type=int, default=20,
                       help='同步议题数量限制（默认20）')

    args = parser.parse_args()

    syncer = OptimizedIssueSyncer()

    if args.command == 'sync-new':
        result = syncer.sync_new_issues(args.limit)
        print(f"新议题同步完成: 创建 {result['created']} 个，失败 {result['failed']} 个")

    elif args.command == 'sync-progress':
        result = syncer.sync_progress()
        print(f"进度同步完成: 更新 {result['updated']} 个，跳过 {result['skipped']} 个，失败 {result['failed']} 个，关闭 {result['closed']} 个")

    elif args.command == 'sync-full':
        result = syncer.run_full_sync(args.limit)
        print(f"完整同步完成，耗时 {result['duration']:.2f} 秒")
        print(syncer.generate_sync_report())

if __name__ == "__main__":
    main()
