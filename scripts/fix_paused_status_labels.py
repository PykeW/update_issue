#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复数据库中状态为paused但标签不同步的议题
自动将状态为paused的议题的GitLab标签更新为"进度::Pausing"
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.gitlab.core.database_manager import DatabaseManager
from src.gitlab.core.gitlab_operations import GitLabOperations

def fix_paused_status_labels():
    """修复状态为paused但标签不同步的议题"""
    try:
        print("🔍 开始修复状态为paused的议题标签...")

        db_manager = DatabaseManager()
        gitlab_ops = GitLabOperations()

        # 查询所有状态为paused且有GitLab URL的议题
        query = """
        SELECT id, project_name, status, gitlab_url, gitlab_progress
        FROM issues
        WHERE status = 'paused'
        AND gitlab_url IS NOT NULL
        AND gitlab_url != ''
        AND gitlab_url != 'NULL'
        ORDER BY id
        """

        issues = db_manager.execute_query(query)

        if not issues:
            print("✅ 没有需要修复的议题")
            return

        print(f"📋 找到 {len(issues)} 个状态为paused的议题需要检查")

        fixed_count = 0
        skipped_count = 0
        failed_count = 0

        for issue in issues:
            issue_id = issue['id']
            project_name = issue['project_name']
            gitlab_url = issue['gitlab_url']
            current_progress = issue.get('gitlab_progress', '')

            print(f"\n🔄 处理议题 {issue_id}: {project_name}")
            print(f"   GitLab URL: {gitlab_url}")
            print(f"   当前进度标签: {current_progress or '(空)'}")

            # 检查是否需要更新
            if current_progress == '进度::Pausing':
                print(f"   ✅ 标签已正确，跳过")
                skipped_count += 1
                continue

            # 提取议题IID
            issue_iid = gitlab_ops.extract_issue_id_from_url(gitlab_url)
            if not issue_iid:
                print(f"   ❌ 无法从URL提取议题IID")
                failed_count += 1
                continue

            # 更新GitLab标签
            print(f"   🔄 更新GitLab标签为'进度::Pausing'...")
            success = gitlab_ops.update_issue_labels(issue_iid, '进度::Pausing')

            if success:
                # 更新数据库中的进度标签
                update_sql = f"""
                UPDATE issues
                SET gitlab_progress = '进度::Pausing',
                    sync_status = 'synced',
                    last_sync_time = NOW()
                WHERE id = {issue_id}
                """
                db_manager.execute_update(update_sql)
                print(f"   ✅ 标签更新成功")
                fixed_count += 1
            else:
                print(f"   ❌ 标签更新失败")
                failed_count += 1

        print(f"\n📊 修复完成:")
        print(f"   ✅ 成功修复: {fixed_count} 个")
        print(f"   ⏭️  已正确跳过: {skipped_count} 个")
        print(f"   ❌ 失败: {failed_count} 个")

    except Exception as e:
        print(f"❌ 修复过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_paused_status_labels()

