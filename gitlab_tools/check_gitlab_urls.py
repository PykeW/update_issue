#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查GitLab URL字段对应的议题是否存在，如果不存在则删除URL内容
"""

import os
import sys
import requests
import subprocess
from typing import Dict, List, Optional, Any, Union
import re

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gitlab_issue_manager import GitLabIssueManager, load_config

# 数据库配置
DB_CONFIG: Dict[str, Union[str, int]] = {
    'host': 'localhost',
    'port': 3306,
    'user': 'issue',
    'password': 'hszc8888',
    'database': 'issue_database'
}

def get_issues_with_gitlab_urls() -> List[Dict[str, Any]]:
    """
    获取所有有GitLab URL的议题
    """
    try:
        cmd: List[str] = [
            'mysql', '-u', str(DB_CONFIG['user']), f'-p{str(DB_CONFIG["password"])}',
            '-h', str(DB_CONFIG['host']), '-P', str(DB_CONFIG['port']),
            '-e', f"""
            USE {DB_CONFIG['database']};
            SELECT id, project_name, problem_description, gitlab_url, sync_status
            FROM issues
            WHERE gitlab_url IS NOT NULL AND gitlab_url != ''
            ORDER BY id;
            """
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # 解析MySQL输出
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return []

        # 获取列名
        headers = lines[0].split('\t')
        issues: List[Dict[str, Any]] = []

        # 解析数据行
        for line in lines[1:]:
            values = line.split('\t')
            if len(values) == len(headers):
                issue = dict(zip(headers, values))
                issues.append(issue)

        return issues
    except Exception as e:
        print(f"❌ 获取数据库议题失败: {e}")
        return []

def extract_issue_id_from_url(gitlab_url: str) -> Optional[int]:
    """
    从GitLab URL中提取议题ID
    """
    try:
        # 匹配URL格式: https://dev.heils.cn/aoi/aoi-demo-r/-/issues/123
        pattern = r'/issues/(\d+)$'
        match = re.search(pattern, gitlab_url)
        if match:
            return int(match.group(1))
        return None
    except Exception as e:
        print(f"❌ 解析URL失败: {gitlab_url}, 错误: {e}")
        return None

def check_gitlab_issue_exists(manager: GitLabIssueManager, project_id: int, issue_iid: int) -> bool:
    """
    检查GitLab议题是否存在
    """
    try:
        issue = manager.get_issue(project_id, issue_iid)
        return issue is not None
    except Exception as e:
        print(f"❌ 检查议题 #{issue_iid} 时发生错误: {e}")
        return False

def clear_gitlab_url(issue_id: int) -> bool:
    """
    清空议题的GitLab URL
    """
    try:
        cmd: List[str] = [
            'mysql', '-u', str(DB_CONFIG['user']), f'-p{str(DB_CONFIG["password"])}',
            '-h', str(DB_CONFIG['host']), '-P', str(DB_CONFIG['port']),
            '-e', f"""
            USE {DB_CONFIG['database']};
            UPDATE issues SET
                gitlab_url = NULL,
                sync_status = 'pending',
                last_sync_time = NULL,
                gitlab_progress = NULL
            WHERE id = {issue_id};
            """
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 清空议题 #{issue_id} GitLab URL失败: {e}")
        return False

def check_all_gitlab_urls() -> None:
    """
    检查所有GitLab URL的有效性
    """
    print("=" * 60)
    print("检查GitLab URL有效性")
    print("=" * 60)

    # 加载GitLab配置
    gitlab_config = load_config()
    if not gitlab_config:
        print("❌ 无法加载GitLab环境配置")
        return

    manager = GitLabIssueManager(gitlab_config['gitlab_url'], gitlab_config['private_token'])
    project_id = gitlab_config['project_id']

    # 获取所有有GitLab URL的议题
    print("📋 获取所有有GitLab URL的议题...")
    issues = get_issues_with_gitlab_urls()
    if not issues:
        print("❌ 没有找到有GitLab URL的议题")
        return

    print(f"✅ 找到 {len(issues)} 个有GitLab URL的议题")

    # 统计信息
    stats = {
        'total': len(issues),
        'valid': 0,
        'invalid': 0,
        'cleared': 0,
        'failed': 0
    }

    # 检查每个议题
    for issue in issues:
        issue_id = issue.get('id')
        gitlab_url = issue.get('gitlab_url', '')
        project_name = issue.get('project_name', '')

        print(f"\n🔍 检查议题 #{issue_id}: {project_name}")
        print(f"  URL: {gitlab_url}")

        try:
            # 提取议题ID
            issue_iid = extract_issue_id_from_url(gitlab_url)
            if not issue_iid:
                print(f"  ❌ 无法从URL提取议题ID")
                stats['invalid'] += 1
                continue

            # 检查议题是否存在
            exists = check_gitlab_issue_exists(manager, project_id, issue_iid)

            if exists:
                print(f"  ✅ 议题 #{issue_iid} 存在")
                stats['valid'] += 1
            else:
                print(f"  ❌ 议题 #{issue_iid} 不存在")
                stats['invalid'] += 1

                # 清空GitLab URL
                print(f"  🗑️  清空GitLab URL...")
                if clear_gitlab_url(issue_id):
                    print(f"  ✅ GitLab URL已清空")
                    stats['cleared'] += 1
                else:
                    print(f"  ❌ 清空GitLab URL失败")
                    stats['failed'] += 1

        except Exception as e:
            print(f"  ❌ 检查议题异常: {e}")
            stats['failed'] += 1

    # 显示检查结果
    print(f"\n📊 检查结果:")
    print(f"  📋 总议题数: {stats['total']}")
    print(f"  ✅ 有效URL: {stats['valid']}")
    print(f"  ❌ 无效URL: {stats['invalid']}")
    print(f"  🗑️  已清空: {stats['cleared']}")
    print(f"  💥 处理失败: {stats['failed']}")

if __name__ == "__main__":
    check_all_gitlab_urls()
