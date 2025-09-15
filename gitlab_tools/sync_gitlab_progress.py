#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab进度同步工具
从GitLab议题中提取进度信息并更新到数据库
"""

import os
import sys
import requests
import subprocess
import json
from typing import Dict, List, Optional, Any, Union
import re
from datetime import datetime

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
            SELECT id, project_name, problem_description, gitlab_url, gitlab_progress, sync_status
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

def get_gitlab_issue_progress(gitlab_issue: Dict[str, Any]) -> str:
    """
    从GitLab议题中提取进度信息
    """
    try:
        labels = gitlab_issue.get('labels', [])

        # 查找进度标签
        for label in labels:
            if label.startswith('进度::'):
                return label

        # 根据状态推断进度
        state = gitlab_issue.get('state', 'opened')
        state_mapping = {
            'closed': '进度::Done',
            'opened': '进度::To do'
        }
        return state_mapping.get(state, '进度::Doing')

    except Exception:
        return '进度::To do'

def close_gitlab_issue(manager: GitLabIssueManager, project_id: int, issue_iid: int,
                      issue_data: Dict[str, Any]) -> bool:
    """
    关闭GitLab议题并更新描述
    """
    try:
        # 构建关闭时的描述
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 获取原始描述
        gitlab_issue = manager.get_issue(project_id, issue_iid)
        if not gitlab_issue:
            return False

        original_description = gitlab_issue.get('description', '')

        # 构建关闭信息
        close_info = f"""

---

## 议题关闭信息
- **关闭时间**: {current_time}
- **关闭原因**: 数据库状态已更新为closed
- **项目名称**: {issue_data.get('project_name', '')}
- **问题分类**: {issue_data.get('problem_category', '')}
- **解决方案**: {issue_data.get('solution', '')}
- **行动记录**: {issue_data.get('action_record', '')}
- **备注**: {issue_data.get('remarks', '')}

*此议题已通过自动化系统关闭*
        """

        # 合并描述
        new_description = original_description + close_info

        # 获取当前标签并移除进度标签
        current_labels = gitlab_issue.get('labels', [])
        updated_labels = [label for label in current_labels if not label.startswith('进度::')]

        # 更新议题（关闭并更新描述和标签）
        updated_issue = manager.update_issue(
            project_id=project_id,
            issue_iid=issue_iid,
            description=new_description,
            labels=updated_labels,
            state_event='close'
        )

        return updated_issue is not None

    except Exception as e:
        print(f"❌ 关闭GitLab议题异常: {e}")
        return False

def update_database_progress(issue_id: int, gitlab_progress: str) -> bool:
    """
    更新数据库中的进度信息
    """
    try:
        cmd: List[str] = [
            'mysql', '-u', str(DB_CONFIG['user']), f'-p{str(DB_CONFIG["password"])}',
            '-h', str(DB_CONFIG['host']), '-P', str(DB_CONFIG['port']),
            '-e', f"""
            USE {DB_CONFIG['database']};
            UPDATE issues SET
                gitlab_progress = '{gitlab_progress}',
                last_sync_time = CURRENT_TIMESTAMP
            WHERE id = {issue_id};
            """
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 更新数据库进度失败: {e}")
        return False

def get_issues_with_gitlab_urls_and_status() -> List[Dict[str, Any]]:
    """
    获取所有有GitLab URL的议题，包括状态信息
    """
    try:
        cmd: List[str] = [
            'mysql', '-u', str(DB_CONFIG['user']), f'-p{str(DB_CONFIG["password"])}',
            '-h', str(DB_CONFIG['host']), '-P', str(DB_CONFIG['port']),
            '-e', f"""
            USE {DB_CONFIG['database']};
            SELECT id, project_name, problem_description, problem_category, solution,
                   action_record, remarks, gitlab_url, gitlab_progress, sync_status, status
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

def sync_gitlab_progress() -> None:
    """
    同步GitLab进度到数据库
    """
    print("=" * 60)
    print("GitLab进度同步工具")
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
    issues = get_issues_with_gitlab_urls_and_status()
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
            issue_iid = extract_issue_id_from_url(gitlab_url)
            if not issue_iid:
                print(f"  ❌ 无法从URL提取议题ID")
                stats['failed'] += 1
                continue

            # 检查数据库状态
            if db_status == 'closed':
                print(f"  🔒 数据库状态为closed，关闭GitLab议题")

                # 关闭GitLab议题
                if close_gitlab_issue(manager, project_id, issue_iid, issue):
                    print(f"  ✅ GitLab议题关闭成功")
                    # 清空数据库中的进度信息
                    if update_database_progress(issue_id, ''):
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
            gitlab_issue = manager.get_issue(project_id, issue_iid)
            if not gitlab_issue:
                print(f"  ❌ GitLab议题 #{issue_iid} 不存在")
                stats['not_found'] += 1
                continue

            # 提取进度信息
            new_progress = get_gitlab_issue_progress(gitlab_issue)
            print(f"  📊 GitLab进度: {new_progress}")

            # 检查是否需要更新
            if new_progress == current_progress:
                print(f"  ⏭️  进度无变化，跳过")
                stats['skipped'] += 1
            else:
                print(f"  🔄 更新进度: {current_progress} → {new_progress}")

                # 更新数据库
                if update_database_progress(issue_id, new_progress):
                    print(f"  ✅ 进度更新成功")
                    stats['updated'] += 1
                else:
                    print(f"  ❌ 数据库更新失败")
                    stats['failed'] += 1

        except Exception as e:
            print(f"  ❌ 处理议题异常: {e}")
            stats['failed'] += 1

    # 显示同步结果
    print(f"\n📊 进度同步结果:")
    print(f"  📋 总议题数: {stats['total']}")
    print(f"  🔄 已更新: {stats['updated']}")
    print(f"  ⏭️  跳过: {stats['skipped']}")
    print(f"  🔒 已关闭: {stats['closed']}")
    print(f"  ❌ 失败: {stats['failed']}")
    print(f"  🔍 未找到: {stats['not_found']}")

if __name__ == "__main__":
    sync_gitlab_progress()
