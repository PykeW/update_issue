#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
议题同步脚本
将数据库中的议题同步到GitLab
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_manager import DatabaseManager
from core.gitlab_operations import GitLabOperations
from core.config_manager import ConfigManager
from utils.helpers import print_stats, setup_logging, validate_issue_data

def sync_issues_to_gitlab(limit: int = 20) -> bool:
    """
    同步数据库议题到GitLab
    """
    print("=" * 60)
    print("数据库议题同步到GitLab")
    print("=" * 60)

    # 设置日志
    setup_logging()

    try:
        # 初始化管理器
        db_manager = DatabaseManager()
        gitlab_ops = GitLabOperations()
        config_manager = ConfigManager()

        # 加载配置
        config = config_manager.load_gitlab_config()
        user_mapping_config = config_manager.load_user_mapping()
        user_mapping = user_mapping_config.get('user_mapping', {}) if user_mapping_config else {}

        if not config:
            print("❌ 无法加载GitLab配置")
            return False

        # 获取需要同步的议题
        print("📋 获取需要同步的议题...")
        issues = db_manager.get_issues_without_gitlab_url(limit)
        if not issues:
            print("✅ 没有找到需要同步的议题")
            print("💡 提示：所有状态为open的议题都已经同步到GitLab了")
            return True

        print(f"✅ 找到 {len(issues)} 个需要同步的议题")

        # 统计信息
        stats = {
            'total': len(issues),
            'created': 0,
            'failed': 0
        }

        # 处理每个议题
        for issue in issues:
            issue_id = issue.get('id')
            project_name = issue.get('project_name', '')

            print(f"\n🔍 处理议题 #{issue_id}: {project_name}")

            try:
                # 验证议题数据
                if not validate_issue_data(issue):
                    print(f"  ❌ 议题数据验证失败")
                    stats['failed'] += 1
                    continue

                # 创建GitLab议题
                gitlab_issue = gitlab_ops.create_issue(issue, config, user_mapping)
                if gitlab_issue:
                    gitlab_url = gitlab_issue.get('web_url', '')
                    gitlab_progress = gitlab_ops.get_issue_progress(gitlab_issue)

                    print(f"  ✅ GitLab议题创建成功")
                    print(f"  URL: {gitlab_url}")
                    print(f"  进度: {gitlab_progress}")

                    # 更新数据库
                    if issue_id and db_manager.update_issue_gitlab_info(int(issue_id), gitlab_url, gitlab_progress):
                        print(f"  ✅ 数据库更新成功")
                        stats['created'] += 1
                    else:
                        print(f"  ❌ 数据库更新失败")
                        stats['failed'] += 1
                else:
                    print(f"  ❌ GitLab议题创建失败")
                    stats['failed'] += 1

            except Exception as e:
                print(f"  ❌ 处理议题异常: {e}")
                stats['failed'] += 1

        # 显示同步结果
        print_stats(stats, "议题同步结果")

        return stats['failed'] == 0

    except Exception as e:
        print(f"❌ 同步过程异常: {e}")
        return False

if __name__ == "__main__":
    success = sync_issues_to_gitlab()
    if not success:
        sys.exit(1)
