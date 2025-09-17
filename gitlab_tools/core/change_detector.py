#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能变更检测器
检测数据库变更并自动触发同步
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from database_manager import DatabaseManager
from gitlab_operations import GitLabOperations

@dataclass
class ChangeEvent:
    """变更事件"""
    issue_id: int
    change_type: str  # INSERT, UPDATE, DELETE
    field_name: str
    old_value: Any
    new_value: Any
    timestamp: datetime
    hash_value: str

class ChangeDetector:
    """智能变更检测器"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.gitlab_ops = GitLabOperations()
        self.last_check_time = None
        self.change_cache = {}

    def calculate_hash(self, issue_data: Dict[str, Any]) -> str:
        """计算议题数据哈希值"""
        # 选择关键字段进行哈希计算
        key_fields = [
            'project_name',
            'problem_description',
            'status',
            'responsible_person',
            'severity_level',
            'problem_category'
        ]

        hash_data = {}
        for field in key_fields:
            hash_data[field] = str(issue_data.get(field, ''))

        # 创建哈希
        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.md5(hash_string.encode()).hexdigest()

    def detect_changes(self, since: Optional[datetime] = None) -> List[ChangeEvent]:
        """检测数据库变更"""
        if since is None:
            since = datetime.now() - timedelta(minutes=5)

        changes = []

        # 查询最近修改的议题
        query = """
            SELECT id, project_name, problem_description, status, responsible_person,
                   severity_level, problem_category, gitlab_url, updated_at
            FROM issues
            WHERE updated_at > %s
            ORDER BY updated_at ASC
        """

        recent_issues = self.db_manager.execute_query(query.replace('%s', f"'{since}'"))

        for issue in recent_issues:
            issue_id = issue['id']
            current_hash = self.calculate_hash(issue)

            # 检查是否有变更
            if issue_id in self.change_cache:
                old_hash = self.change_cache[issue_id]
                if old_hash != current_hash:
                    # 检测到变更
                    change_event = ChangeEvent(
                        issue_id=issue_id,
                        change_type='UPDATE',
                        field_name='data_hash',
                        old_value=old_hash,
                        new_value=current_hash,
                        timestamp=issue['updated_at'],
                        hash_value=current_hash
                    )
                    changes.append(change_event)
            else:
                # 新议题
                change_event = ChangeEvent(
                    issue_id=issue_id,
                    change_type='INSERT',
                    field_name='data_hash',
                    old_value=None,
                    new_value=current_hash,
                    timestamp=issue['updated_at'],
                    hash_value=current_hash
                )
                changes.append(change_event)

            # 更新缓存
            self.change_cache[issue_id] = current_hash

        return changes

    def should_sync_issue(self, issue_data: Dict[str, Any]) -> tuple[bool, str]:
        """判断议题是否需要同步"""
        status = issue_data.get('status', '')
        gitlab_url = issue_data.get('gitlab_url', '')

        # 检查状态变更
        if status == 'closed' and gitlab_url:
            return True, 'close'
        elif status == 'open' and not gitlab_url:
            return True, 'create'
        elif status == 'open' and gitlab_url:
            return True, 'update'
        elif gitlab_url:
            return True, 'sync_progress'

        return False, ''

    def add_to_sync_queue(self, issue_id: int, action: str, priority: int = 5, metadata: Optional[Dict] = None):
        """添加任务到同步队列"""
        try:
            # 使用存储过程添加任务
            query = "CALL AddToSyncQueue(%s, %s, %s, %s)"
            metadata_json = json.dumps(metadata if metadata is not None else {})

            result = self.db_manager.execute_query(query.format(issue_id, action, priority, metadata_json))

            if result:
                queue_id = result[0].get('queue_id', 0)
                result_type = result[0].get('result', 'unknown')

                print(f"✅ 任务已添加到队列: ID={queue_id}, 结果={result_type}")
                return queue_id
            else:
                print(f"❌ 添加任务到队列失败")
                return None

        except Exception as e:
            print(f"❌ 添加任务到队列时发生错误: {str(e)}")
            return None

    def process_changes(self, changes: List[ChangeEvent]):
        """处理检测到的变更"""
        for change in changes:
            try:
                # 获取议题详情
                issue_data = self.db_manager.get_issue_by_id(change.issue_id)
                if not issue_data:
                    continue

                # 判断是否需要同步
                should_sync, action = self.should_sync_issue(issue_data)

                if should_sync:
                    # 确定优先级
                    priority = self._determine_priority(issue_data, action)

                    # 准备元数据
                    metadata = {
                        'change_type': change.change_type,
                        'field_name': change.field_name,
                        'timestamp': change.timestamp.isoformat(),
                        'hash_value': change.hash_value
                    }

                    # 添加到同步队列
                    queue_id = self.add_to_sync_queue(
                        change.issue_id,
                        action,
                        priority,
                        metadata
                    )

                    if queue_id:
                        print(f"🔄 议题 #{change.issue_id} 已加入同步队列: {action}")

            except Exception as e:
                print(f"❌ 处理变更时发生错误: {str(e)}")

    def _determine_priority(self, issue_data: Dict[str, Any], action: str) -> int:
        """确定同步优先级"""
        # 基础优先级
        priority_map = {
            'create': 3,      # 创建议题优先级较高
            'close': 2,      # 关闭议题优先级最高
            'update': 4,     # 更新议题
            'sync_progress': 5  # 同步进度优先级较低
        }

        base_priority = priority_map.get(action, 5)

        # 根据严重程度调整优先级
        severity = issue_data.get('severity_level', 0)
        if isinstance(severity, (int, float)) and severity > 0:
            if severity >= 3:
                base_priority = max(1, base_priority - 1)  # 提高优先级
            elif severity <= 1:
                base_priority = min(10, base_priority + 1)  # 降低优先级

        return base_priority

    def run_continuous_monitoring(self, interval: int = 30):
        """持续监控模式"""
        print(f"🔄 开始持续监控模式，检查间隔: {interval}秒")

        while True:
            try:
                # 检测变更
                changes = self.detect_changes()

                if changes:
                    print(f"📋 检测到 {len(changes)} 个变更")
                    self.process_changes(changes)
                else:
                    print("✅ 无变更检测到")

                # 等待下次检查
                time.sleep(interval)

            except KeyboardInterrupt:
                print("\n🛑 监控已停止")
                break
            except Exception as e:
                print(f"❌ 监控过程中发生错误: {str(e)}")
                time.sleep(interval)

    def run_single_check(self):
        """单次检查模式"""
        print("🔍 执行单次变更检测...")

        changes = self.detect_changes()

        if changes:
            print(f"📋 检测到 {len(changes)} 个变更:")
            for change in changes:
                print(f"  - 议题 #{change.issue_id}: {change.change_type}")

            self.process_changes(changes)
        else:
            print("✅ 无变更检测到")

        return len(changes)

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='智能变更检测器')
    parser.add_argument('mode', choices=['single', 'continuous'], help='运行模式')
    parser.add_argument('--interval', type=int, default=30, help='持续模式检查间隔（秒）')

    args = parser.parse_args()

    detector = ChangeDetector()

    if args.mode == 'single':
        detector.run_single_check()
    elif args.mode == 'continuous':
        detector.run_continuous_monitoring(args.interval)

if __name__ == "__main__":
    main()
