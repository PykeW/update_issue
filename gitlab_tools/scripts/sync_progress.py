#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab进度同步脚本
从GitLab议题中提取进度信息并更新到数据库
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_manager import DatabaseManager
from core.gitlab_operations import GitLabOperations
from utils.helpers import print_stats, setup_logging

def sync_gitlab_progress() -> None:
    """
    同步GitLab进度到数据库
    """
    print("=" * 60)
    print("GitLab进度同步工具")
    print("=" * 60)

    # 设置日志
    setup_logging()

    try:
        # 初始化管理器
        db_manager = DatabaseManager()
        gitlab_ops = GitLabOperations()

        # 获取所有有GitLab URL的议题
        print("📋 获取所有有GitLab URL的议题...")
        issues = db_manager.get_issues_with_gitlab_url()
        if not issues:
            print("❌ 没有找到有GitLab URL的议题")
            return

        print(f"✅ 找到 {len(issues)} 个有GitLab URL的议题")

        # 统计信息
        stats = {
            'total': len(issues),
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'not_found': 0,
            'closed': 0
        }

        # 处理每个议题
        for issue in issues:
            issue_id = issue.get('id')
            gitlab_url = issue.get('gitlab_url', '')
            project_name = issue.get('project_name', '')
            current_progress = issue.get('gitlab_progress', '')
            db_status = issue.get('status', '')

            print(f"\n🔍 处理议题 #{issue_id}: {project_name}")
            print(f"  URL: {gitlab_url}")
            print(f"  数据库状态: {db_status}")
            print(f"  当前进度: {current_progress}")

            try:
                # 提取议题ID
                issue_iid = gitlab_ops.extract_issue_iid_from_url(gitlab_url)
                if not issue_iid:
                    print(f"  ❌ 无法从URL提取议题ID")
                    stats['failed'] += 1
                    continue

                # 检查数据库状态
                if db_status == 'closed':
                    print(f"  🔒 数据库状态为closed，关闭GitLab议题")

                    # 关闭GitLab议题
                    if gitlab_ops.close_issue(issue_iid, issue):
                        print(f"  ✅ GitLab议题关闭成功")
                        # 清空数据库中的进度信息
                        if issue_id and db_manager.update_issue_progress(int(issue_id), ''):
                            print(f"  ✅ 数据库进度已清空")
                            stats['closed'] += 1
                        else:
                            print(f"  ❌ 数据库进度清空失败")
                            stats['failed'] += 1
                    else:
                        print(f"  ❌ GitLab议题关闭失败")
                        stats['failed'] += 1
                    continue

                # 获取GitLab议题
                gitlab_issue = gitlab_ops.get_issue(issue_iid)
                if not gitlab_issue:
                    print(f"  ❌ GitLab议题 #{issue_iid} 不存在")
                    stats['not_found'] += 1
                    continue

                # 提取进度信息
                new_progress = gitlab_ops.get_issue_progress(gitlab_issue)
                print(f"  📊 GitLab进度: {new_progress}")

                # 检查是否需要更新
                if new_progress == current_progress:
                    print(f"  ⏭️  进度无变化，跳过")
                    stats['skipped'] += 1
                else:
                    print(f"  🔄 更新进度: {current_progress} → {new_progress}")

                    # 更新数据库
                    if issue_id and db_manager.update_issue_progress(int(issue_id), new_progress):
                        print(f"  ✅ 进度更新成功")
                        stats['updated'] += 1
                    else:
                        print(f"  ❌ 数据库更新失败")
                        stats['failed'] += 1

            except Exception as e:
                print(f"  ❌ 处理议题异常: {e}")
                stats['failed'] += 1

        # 显示同步结果
        print_stats(stats, "进度同步结果")

    except Exception as e:
        print(f"❌ 同步过程异常: {e}")

if __name__ == "__main__":
    sync_gitlab_progress()
