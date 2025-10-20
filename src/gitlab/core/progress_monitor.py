#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab议题进度监控器
监控未关闭且有GitLab链接的议题，检测进度变化并更新数据库
"""

import sys
import time
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

sys.path.append(str(Path(__file__).parent))

from database_manager import DatabaseManager
from gitlab_operations import GitLabOperations
from config_manager import ConfigManager

@dataclass
class ProgressChange:
    """进度变更记录"""
    issue_id: int
    project_name: str
    gitlab_url: str
    gitlab_id: int
    old_progress: str
    new_progress: str
    change_time: datetime
    labels: List[str]

class ProgressMonitor:
    """GitLab议题进度监控器"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.gitlab_ops = GitLabOperations()
        self.config_manager = ConfigManager()
        self.last_check_time = None
        self.progress_cache = {}

    def get_open_issues_with_gitlab_url(self) -> List[Dict]:
        """获取所有未关闭且有GitLab链接的议题"""
        query = """
            SELECT id, project_name, problem_description, status,
                   gitlab_url, gitlab_progress, updated_at
            FROM issues
            WHERE status = 'open'
            AND gitlab_url IS NOT NULL
            AND gitlab_url != ''
            ORDER BY updated_at DESC
        """

        issues = self.db_manager.execute_query(query)
        return issues or []

    def extract_gitlab_issue_id(self, gitlab_url: str) -> Optional[int]:
        """从GitLab URL中提取议题ID"""
        try:
            return self.gitlab_ops.extract_issue_id_from_url(gitlab_url)
        except Exception as e:
            print(f"❌ 提取GitLab议题ID失败: {str(e)}")
            return None

    def get_gitlab_issue_progress(self, gitlab_issue_id: int) -> Dict[str, Any]:
        """获取GitLab议题的进度信息"""
        try:
            # 获取项目ID
            project_id = self.gitlab_ops.project_id

            # 获取议题详情
            issue_data = self.gitlab_ops.manager.get_issue(project_id, gitlab_issue_id)
            if not issue_data:
                return {'progress': '', 'labels': [], 'error': '议题不存在'}

            # 提取进度标签
            labels = issue_data.get('labels', [])
            progress = self.gitlab_ops.extract_progress_from_labels(labels)

            return {
                'progress': progress,
                'labels': labels,
                'title': issue_data.get('title', ''),
                'state': issue_data.get('state', ''),
                'updated_at': issue_data.get('updated_at', ''),
                'error': None
            }

        except Exception as e:
            return {'progress': '', 'labels': [], 'error': str(e)}

    def calculate_progress_hash(self, progress_data: Dict[str, Any]) -> str:
        """计算进度数据的哈希值"""
        hash_data = {
            'progress': progress_data.get('progress', ''),
            'labels': sorted(progress_data.get('labels', [])),
            'state': progress_data.get('state', ''),
            'updated_at': progress_data.get('updated_at', '')
        }

        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.md5(hash_string.encode()).hexdigest()

    def detect_progress_changes(self) -> List[ProgressChange]:
        """检测进度变化"""
        changes = []

        # 获取所有未关闭且有GitLab链接的议题
        issues = self.get_open_issues_with_gitlab_url()

        print(f"🔍 检查 {len(issues)} 个有GitLab链接的开放议题...")

        for issue in issues:
            issue_id = issue['id']
            project_name = issue['project_name']
            gitlab_url = issue['gitlab_url']
            current_progress = issue.get('gitlab_progress', '')

            # 提取GitLab议题ID
            gitlab_issue_id = self.extract_gitlab_issue_id(gitlab_url)
            if not gitlab_issue_id:
                continue

            # 获取GitLab议题进度信息
            progress_data = self.get_gitlab_issue_progress(gitlab_issue_id)

            if progress_data.get('error'):
                print(f"⚠️ 议题 #{issue_id} ({project_name}) GitLab获取失败: {progress_data['error']}")
                continue

            new_progress = progress_data.get('progress', '')
            labels = progress_data.get('labels', [])

            # 计算当前进度哈希
            current_hash = self.calculate_progress_hash(progress_data)

            # 检查是否有变化
            if issue_id in self.progress_cache:
                old_hash = self.progress_cache[issue_id]
                if old_hash != current_hash:
                    # 检测到变化
                    change = ProgressChange(
                        issue_id=issue_id,
                        project_name=project_name,
                        gitlab_url=gitlab_url,
                        gitlab_id=gitlab_issue_id,
                        old_progress=current_progress,
                        new_progress=new_progress,
                        change_time=datetime.now(),
                        labels=labels
                    )
                    changes.append(change)
                    print(f"🔄 检测到进度变化: 议题 #{issue_id} ({project_name})")
                    print(f"   旧进度: '{current_progress}' -> 新进度: '{new_progress}'")
            else:
                # 首次检查，记录当前状态
                if new_progress != current_progress:
                    change = ProgressChange(
                        issue_id=issue_id,
                        project_name=project_name,
                        gitlab_url=gitlab_url,
                        gitlab_id=gitlab_issue_id,
                        old_progress=current_progress,
                        new_progress=new_progress,
                        change_time=datetime.now(),
                        labels=labels
                    )
                    changes.append(change)
                    print(f"🆕 首次检测进度: 议题 #{issue_id} ({project_name})")
                    print(f"   数据库进度: '{current_progress}' -> GitLab进度: '{new_progress}'")

            # 更新缓存
            self.progress_cache[issue_id] = current_hash

        return changes

    def update_database_progress(self, change: ProgressChange) -> bool:
        """更新数据库中的进度信息"""
        try:
            # 更新议题进度
            success = self.db_manager.update_issue_progress(change.issue_id, change.new_progress)

            if success:
                print(f"✅ 已更新数据库进度: 议题 #{change.issue_id} -> '{change.new_progress}'")

                # 记录变更日志
                self._log_progress_change(change)
                return True
            else:
                print(f"❌ 更新数据库失败: 议题 #{change.issue_id}")
                return False

        except Exception as e:
            print(f"❌ 更新数据库时发生错误: {str(e)}")
            return False

    def _log_progress_change(self, change: ProgressChange):
        """记录进度变更日志"""
        try:
            # 插入变更日志
            query = """
                INSERT INTO issue_changes
                (issue_id, change_type, field_name, old_value, new_value, change_timestamp, processed)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            query_formatted = query.replace('%s', "'{}'").format(
                change.issue_id,
                'UPDATE',
                'gitlab_progress',
                change.old_progress,
                change.new_progress,
                change.change_time,
                True
            )
            self.db_manager.execute_update(query_formatted)

        except Exception as e:
            print(f"⚠️ 记录变更日志失败: {str(e)}")

    def process_progress_changes(self, changes: List[ProgressChange]) -> Dict[str, int]:
        """处理检测到的进度变化"""
        results = {'updated': 0, 'failed': 0, 'skipped': 0}

        for change in changes:
            try:
                # 检查是否需要更新
                if change.new_progress != change.old_progress:
                    if self.update_database_progress(change):
                        results['updated'] += 1
                    else:
                        results['failed'] += 1
                else:
                    results['skipped'] += 1
                    print(f"⏭️ 跳过无变化: 议题 #{change.issue_id}")

            except Exception as e:
                print(f"❌ 处理进度变化时发生错误: {str(e)}")
                results['failed'] += 1

        return results

    def run_single_check(self) -> Dict[str, int]:
        """执行单次进度检查"""
        print("🔍 开始执行GitLab进度监控检查...")

        start_time = datetime.now()

        try:
            # 检测进度变化
            changes = self.detect_progress_changes()

            if changes:
                print(f"📋 检测到 {len(changes)} 个进度变化")

                # 处理变化
                results = self.process_progress_changes(changes)

                print(f"📊 处理结果: 更新 {results['updated']} 个，失败 {results['failed']} 个，跳过 {results['skipped']} 个")

            else:
                print("✅ 未检测到进度变化")
                results = {'updated': 0, 'failed': 0, 'skipped': 0}

            # 记录检查时间
            self.last_check_time = start_time

            return results

        except Exception as e:
            print(f"❌ 进度监控检查时发生错误: {str(e)}")
            return {'updated': 0, 'failed': 0, 'skipped': 0}

    def run_continuous_monitoring(self, interval: int = 300):
        """持续监控模式"""
        print(f"🔄 开始持续进度监控，检查间隔: {interval}秒")

        while True:
            try:
                # 执行检查
                self.run_single_check()

                # 等待下次检查
                print(f"⏰ 等待 {interval} 秒后进行下次检查...")
                time.sleep(interval)

            except KeyboardInterrupt:
                print("\n🛑 进度监控已停止")
                break
            except Exception as e:
                print(f"❌ 持续监控过程中发生错误: {str(e)}")
                time.sleep(interval)

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        try:
            # 获取有GitLab链接的开放议题数量
            open_with_gitlab_query = """
                SELECT COUNT(*) as count
                FROM issues
                WHERE status = 'open'
                AND gitlab_url IS NOT NULL
                AND gitlab_url != ''
            """

            result = self.db_manager.execute_query(open_with_gitlab_query)
            open_with_gitlab_count = result[0]['count'] if result else 0

            # 获取最近24小时的进度变更数量
            recent_changes_query = """
                SELECT COUNT(*) as count
                FROM issue_changes
                WHERE change_type = 'UPDATE'
                AND field_name = 'gitlab_progress'
                AND change_timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """

            result = self.db_manager.execute_query(recent_changes_query)
            recent_changes_count = result[0]['count'] if result else 0

            return {
                'open_issues_with_gitlab': int(open_with_gitlab_count),
                'recent_progress_changes': int(recent_changes_count),
                'cache_size': len(self.progress_cache),
                'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None
            }

        except Exception as e:
            return {'error': str(e)}

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='GitLab议题进度监控器')
    parser.add_argument('mode', choices=['single', 'continuous', 'stats'], help='运行模式')
    parser.add_argument('--interval', type=int, default=300, help='持续模式检查间隔（秒）')

    args = parser.parse_args()

    monitor = ProgressMonitor()

    if args.mode == 'single':
        results = monitor.run_single_check()
        print(f"\n📊 单次检查完成: {results}")

    elif args.mode == 'continuous':
        monitor.run_continuous_monitoring(args.interval)

    elif args.mode == 'stats':
        stats = monitor.get_monitoring_stats()
        print("📊 监控统计信息:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    main()
