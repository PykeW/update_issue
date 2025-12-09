#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量同步GitLab进度信息到数据库
从GitLab获取所有已有gitlab_url的议题的当前进度标签，并更新到数据库
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.gitlab.core.database_manager import DatabaseManager
from src.gitlab.core.gitlab_operations import GitLabOperations

def sync_all_gitlab_progress():
    """批量同步所有议题的GitLab进度信息"""
    try:
        print("=" * 60)
        print("批量同步GitLab进度信息到数据库")
        print("=" * 60)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 初始化
        db_manager = DatabaseManager()
        gitlab_ops = GitLabOperations()

        # 获取所有有GitLab URL的议题
        print("🔍 查询数据库中有GitLab URL的议题...")
        issues = db_manager.get_issues_with_gitlab_url()

        if not issues:
            print("✅ 没有找到有GitLab URL的议题")
            return

        print(f"📋 找到 {len(issues)} 个有GitLab URL的议题")
        print()

        # 统计信息
        success_count = 0
        failed_count = 0
        skipped_count = 0
        updated_count = 0
        unchanged_count = 0

        # 处理每个议题
        for i, issue in enumerate(issues, 1):
            issue_id = issue['id']
            project_name = issue.get('project_name', '未知项目')
            gitlab_url = issue.get('gitlab_url', '')
            current_progress = issue.get('gitlab_progress', '')

            print(f"[{i}/{len(issues)}] 处理议题 #{issue_id}: {project_name}")

            # 检查gitlab_url是否有效
            if not gitlab_url or gitlab_url.strip() == '' or gitlab_url.upper() == 'NULL':
                print(f"  ⏭️  跳过: 无效的GitLab URL")
                skipped_count += 1
                continue

            try:
                # 从GitLab获取进度信息
                progress = gitlab_ops.sync_progress_from_gitlab(gitlab_url)

                if progress:
                    # 检查进度是否有变化
                    if progress != current_progress:
                        # 更新数据库
                        if db_manager.update_issue_progress(issue_id, progress):
                            print(f"  ✅ 进度已更新: '{current_progress}' -> '{progress}'")
                            updated_count += 1
                            success_count += 1
                        else:
                            print(f"  ❌ 数据库更新失败")
                            failed_count += 1
                    else:
                        print(f"  ✓ 进度无变化: '{progress}'")
                        unchanged_count += 1
                        success_count += 1
                else:
                    print(f"  ⚠️  未能从GitLab获取进度信息")
                    failed_count += 1

            except Exception as e:
                print(f"  ❌ 处理异常: {str(e)}")
                failed_count += 1

            print()

        # 输出统计结果
        print("=" * 60)
        print("同步完成")
        print("=" * 60)
        print(f"总议题数: {len(issues)}")
        print(f"成功: {success_count} 个 (更新 {updated_count} 个, 无变化 {unchanged_count} 个)")
        print(f"失败: {failed_count} 个")
        print(f"跳过: {skipped_count} 个")
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        return {
            'total': len(issues),
            'success': success_count,
            'updated': updated_count,
            'unchanged': unchanged_count,
            'failed': failed_count,
            'skipped': skipped_count
        }

    except Exception as e:
        print(f"❌ 批量同步异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = sync_all_gitlab_progress()
    if result:
        sys.exit(0)
    else:
        sys.exit(1)

