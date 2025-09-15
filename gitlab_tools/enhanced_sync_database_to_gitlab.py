#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版数据库到GitLab同步工具
支持进度跟踪和智能更新
"""

import os
import sys
import json
import requests
import subprocess
from typing import Dict, List, Optional, Any, Union

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gitlab_issue_manager import GitLabIssueManager, load_config

def load_user_mapping() -> Dict[str, Any]:
    """
    加载用户映射配置
    """
    try:
        mapping_file = os.path.join(os.path.dirname(__file__), 'user_mapping.json')
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print("⚠️  用户映射文件不存在，使用默认配置")
            return {
                'user_mapping': {},
                'default_assignee': 'kohill'
            }
    except Exception as e:
        print(f"⚠️  加载用户映射失败: {e}")
        return {
            'user_mapping': {},
            'default_assignee': 'kohill'
        }

def get_assignee_ids(manager: GitLabIssueManager, responsible_person: str, user_mapping: Dict[str, str]) -> Optional[List[int]]:
    """
    根据责任人姓名获取GitLab用户ID列表（支持多人指派）
    自动识别包含 "/" 的责任人并拆分为多人指派
    """
    try:
        # 检查是否包含 "/" 分隔符，自动识别多人指派
        if '/' in responsible_person:
            print(f"🔍 检测到多人责任人: '{responsible_person}'")
            # 按 "/" 分割责任人
            person_list = [p.strip() for p in responsible_person.split('/')]
            print(f"   拆分为: {person_list}")

            assignee_ids: List[int] = []
            for person in person_list:
                if person:  # 确保不是空字符串
                    # 查找单个责任人的映射
                    gitlab_username = user_mapping.get(person)
                    if gitlab_username:
                        # 确保是字符串格式（单个用户）
                        if isinstance(gitlab_username, list):
                            gitlab_username = gitlab_username[0]

                        user_id = get_user_id_by_username(manager, gitlab_username)
                        if user_id:
                            assignee_ids.append(user_id)
                            print(f"✅ 责任人 '{person}' → GitLab用户 '{gitlab_username}' (ID: {user_id})")
                        else:
                            print(f"❌ 无法获取GitLab用户 '{gitlab_username}' 的ID")
                    else:
                        print(f"⚠️  未找到责任人 '{person}' 的映射")

            if assignee_ids:
                return assignee_ids
            else:
                print(f"⚠️  无法获取任何多人指派人ID，使用默认指派人")
                gitlab_username = user_mapping.get('default_assignee', 'kohill')
                user_id = get_user_id_by_username(manager, gitlab_username)
                return [user_id] if user_id else None

        else:
            # 单个责任人处理
            gitlab_usernames = user_mapping.get(responsible_person)

            if not gitlab_usernames:
                print(f"⚠️  未找到责任人 '{responsible_person}' 的映射，使用默认指派人")
                gitlab_usernames = [user_mapping.get('default_assignee', 'kohill')]

            # 确保是列表格式
            if isinstance(gitlab_usernames, str):
                gitlab_usernames = [gitlab_usernames]

            assignee_ids = []

            for username in gitlab_usernames:
                user_id = get_user_id_by_username(manager, username)
                if user_id:
                    assignee_ids.append(user_id)
                    print(f"✅ 责任人 '{responsible_person}' → GitLab用户 '{username}' (ID: {user_id})")
                else:
                    print(f"❌ 无法获取GitLab用户 '{username}' 的ID")

            if assignee_ids:
                return assignee_ids
            else:
                print(f"❌ 无法获取任何指派人ID")
                return None

    except Exception as e:
        print(f"❌ 获取指派人ID异常: {e}")
        return None

def get_user_id_by_username(manager: GitLabIssueManager, username: str) -> Optional[int]:
    """
    根据用户名获取GitLab用户ID
    """
    try:
        url = f"{manager.gitlab_url}/api/v4/users"
        params = {'username': username}
        response = requests.get(url, headers=manager.headers, params=params)

        if response.status_code == 200:
            users = response.json()
            if users:
                return users[0]['id']
            else:
                print(f"❌ 未找到GitLab用户: {username}")
                return None
        else:
            print(f"❌ 获取GitLab用户 '{username}' 失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 获取用户 '{username}' ID异常: {e}")
        return None

# 数据库配置
DB_CONFIG: Dict[str, Union[str, int]] = {
    'host': 'localhost',
    'port': 3306,
    'user': 'issue',
    'password': 'hszc8888',
    'database': 'issue_database'
}

def get_database_issues() -> List[Dict[str, Any]]:
    """
    从数据库获取所有议题，包括GitLab同步状态
    """
    try:
        cmd: List[str] = [
            'mysql', '-u', str(DB_CONFIG['user']), f'-p{str(DB_CONFIG["password"])}',
            '-h', str(DB_CONFIG['host']), '-P', str(DB_CONFIG['port']),
            '-e', f"""
            USE {DB_CONFIG['database']};
            SELECT
                id, project_name, problem_category,
                severity_level, problem_description, solution,
                action_priority, action_record, initiator,
                responsible_person, status, start_time,
                target_completion_time, actual_completion_time,
                remarks, gitlab_url, sync_status, last_sync_time, gitlab_progress
            FROM issues
            WHERE (gitlab_url IS NULL OR gitlab_url = '') AND status = 'open' AND (sync_status IS NULL OR sync_status = 'pending' OR sync_status = 'failed')
            ORDER BY id
            LIMIT 20;
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

def load_gitlab_config() -> Dict[str, Any]:
    """
    加载GitLab配置
    """
    config_file = 'wps_gitlab_config.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  读取GitLab配置文件失败: {e}")
    return {}

def map_severity_to_labels(severity_level: int, config: Dict[str, Any]) -> List[str]:
    """
    将严重程度映射到GitLab标签
    """
    if not config or 'labels' not in config or 'severity_mapping' not in config['labels']:
        return []

    severity_str = str(severity_level)
    mapping = config['labels']['severity_mapping']

    if severity_str in mapping:
        return mapping[severity_str]
    return []

def map_status_to_progress(status: str, config: Dict[str, Any]) -> str:
    """
    将状态映射到GitLab进度标签
    """
    if not config or 'labels' not in config or 'progress_mapping' not in config['labels']:
        return '进度::To do'

    mapping = config['labels']['progress_mapping']

    if status in mapping:
        return mapping[status]
    return '进度::To do'

def get_issue_type_label(problem_description: str, config: Dict[str, Any]) -> str:
    """
    根据问题描述智能识别议题类型
    """
    if not config or 'labels' not in config or 'issue_type_mapping' not in config['labels']:
        return '议题类型::功能优化'

    problem_desc = problem_description.lower()
    mapping = config['labels']['issue_type_mapping']

    # 按优先级检查关键词
    for config_data in mapping.values():
        keywords = config_data['keywords']
        if any(keyword in problem_desc for keyword in keywords):
            return config_data['label']

    return '议题类型::功能优化'

def create_gitlab_issue(issue_data: Dict[str, Any], manager: GitLabIssueManager, project_id: int, config: Dict[str, Any], user_mapping: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    在GitLab中创建议题
    """
    try:
        # 构建议题标题 - 使用条件表达式提高效率
        project_name = issue_data.get('project_name', '')
        problem_desc = issue_data.get('problem_description', '')

        # 使用条件表达式替代 if-elif-else 链
        title = (
            f"{project_name}: {problem_desc}" if project_name and problem_desc else
            project_name if project_name else
            f"议题 #{issue_data.get('id', '')}"
        )

        # 构建议题描述
        initiator = issue_data.get('initiator', '')
        description = f"提出人: {initiator}" if initiator else ""

        # 构建详细信息
        details = f"""
## 问题描述
{issue_data.get('problem_description', '')}

## 解决方案
{issue_data.get('solution', '')}

## 行动记录
{issue_data.get('action_record', '')}

## 备注
{issue_data.get('remarks', '')}

---
*此议题由WPS数据同步系统自动创建*
        """.strip()

        # 合并描述 - 使用条件表达式提高效率
        full_description = (
            f"{description}\n\n{details}" if description and details else
            description if description else
            details
        )

        # 构建标签
        labels: List[str] = []

        # 严重程度标签
        severity_labels = map_severity_to_labels(issue_data.get('severity_level', 0), config)
        labels.extend(severity_labels)

        # 进度标签
        progress_label = map_status_to_progress(issue_data.get('status', 'open'), config)
        labels.append(progress_label)

        # 固定标签
        if config and 'labels' in config and 'additional_labels' in config['labels']:
            labels.extend(config['labels']['additional_labels'])

        # 智能议题类型标签
        issue_type_label = get_issue_type_label(issue_data.get('problem_description', ''), config)
        labels.append(issue_type_label)

        # 获取指派人ID
        assignee_ids = None
        responsible_person = issue_data.get('responsible_person', '')
        if responsible_person:
            assignee_ids = get_assignee_ids(manager, responsible_person, user_mapping)

        # 创建GitLab议题
        gitlab_issue = manager.create_issue(
            project_id=project_id,
            title=title,
            description=full_description,
            labels=labels,
            assignee_ids=assignee_ids
        )

        if gitlab_issue:
            return gitlab_issue
        else:
            print(f"❌ 创建GitLab议题失败: {title}")
            return None

    except Exception as e:
        print(f"❌ 创建GitLab议题异常: {e}")
        return None

def update_gitlab_issue(issue_data: Dict[str, Any], gitlab_issue: Dict[str, Any], manager: GitLabIssueManager, project_id: int, config: Dict[str, Any], user_mapping: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    更新GitLab议题
    """
    try:
        # 构建新的议题标题 - 使用条件表达式提高效率
        project_name = issue_data.get('project_name', '')
        problem_desc = issue_data.get('problem_description', '')

        # 使用条件表达式替代 if-elif-else 链
        title = (
            f"{project_name}: {problem_desc}" if project_name and problem_desc else
            project_name if project_name else
            f"议题 #{issue_data.get('id', '')}"
        )

        # 构建新的议题描述
        initiator = issue_data.get('initiator', '')
        description = f"提出人: {initiator}" if initiator else ""

        # 构建详细信息
        details = f"""
## 问题描述
{issue_data.get('problem_description', '')}

## 解决方案
{issue_data.get('solution', '')}

## 详细信息
- **项目名称**: {issue_data.get('project_name', '')}
- **问题分类**: {issue_data.get('problem_category', '')}
- **严重程度**: {issue_data.get('severity_level', '')}
- **行动优先级**: {issue_data.get('action_priority', '')}
- **发起人**: {issue_data.get('initiator', '')}
- **责任人**: {issue_data.get('responsible_person', '')}
- **状态**: {issue_data.get('status', '')}
- **开始时间**: {issue_data.get('start_time', '')}
- **目标完成时间**: {issue_data.get('target_completion_time', '')}
- **实际完成时间**: {issue_data.get('actual_completion_time', '')}
- **行动记录**: {issue_data.get('action_record', '')}
- **备注**: {issue_data.get('remarks', '')}

---
*此议题由WPS数据同步系统自动更新*
        """.strip()

        # 合并描述 - 使用条件表达式提高效率
        full_description = (
            f"{description}\n\n{details}" if description and details else
            description if description else
            details
        )

        # 构建标签
        labels: List[str] = []

        # 严重程度标签
        severity_labels = map_severity_to_labels(issue_data.get('severity_level', 0), config)
        labels.extend(severity_labels)

        # 进度标签
        progress_label = map_status_to_progress(issue_data.get('status', 'open'), config)
        labels.append(progress_label)

        # 固定标签
        if config and 'labels' in config and 'additional_labels' in config['labels']:
            labels.extend(config['labels']['additional_labels'])

        # 智能议题类型标签
        issue_type_label = get_issue_type_label(issue_data.get('problem_description', ''), config)
        labels.append(issue_type_label)

        # 获取指派人ID
        assignee_ids = None
        responsible_person = issue_data.get('responsible_person', '')
        if responsible_person:
            assignee_ids = get_assignee_ids(manager, responsible_person, user_mapping)

        # 更新GitLab议题
        updated_issue = manager.update_issue(
            project_id=project_id,
            issue_iid=gitlab_issue['iid'],
            title=title,
            description=full_description,
            labels=labels,
            assignee_ids=assignee_ids
        )

        if updated_issue:
            return updated_issue
        else:
            print(f"❌ 更新GitLab议题失败: {title}")
            return None

    except Exception as e:
        print(f"❌ 更新GitLab议题异常: {e}")
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

        # 根据状态推断进度 - 使用字典映射提高效率
        state = gitlab_issue.get('state', 'opened')
        state_mapping = {
            'closed': '进度::Done',
            'opened': '进度::To do'
        }
        return state_mapping.get(state, '进度::Doing')

    except Exception:
        return '进度::To do'

def update_database_issue(issue_id: int, gitlab_issue: Dict[str, Any], operation_type: str = 'sync') -> bool:
    """
    更新数据库中的议题信息
    """
    try:
        gitlab_url = gitlab_issue.get('web_url', '')
        gitlab_id = gitlab_issue.get('iid', '')
        gitlab_labels = json.dumps(gitlab_issue.get('labels', []), ensure_ascii=False)
        gitlab_progress = get_gitlab_issue_progress(gitlab_issue)

        cmd: List[str] = [
            'mysql', '-u', str(DB_CONFIG['user']), f'-p{str(DB_CONFIG["password"])}',
            '-h', str(DB_CONFIG['host']), '-P', str(DB_CONFIG['port']),
            '-e', f"""
            USE {DB_CONFIG['database']};
            UPDATE issues SET
                gitlab_url = '{gitlab_url}',
                gitlab_progress = '{gitlab_progress}',
                sync_status = 'synced',
                last_sync_time = CURRENT_TIMESTAMP
            WHERE id = {issue_id};
            """
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.returncode == 0

    except Exception as e:
        print(f"❌ 更新数据库议题失败: {e}")
        return False

def sync_issues_to_gitlab() -> bool:
    """
    同步数据库议题到GitLab
    """
    print("=" * 60)
    print("增强版数据库到GitLab同步工具")
    print("=" * 60)

    # 加载GitLab配置
    config = load_gitlab_config()
    if not config:
        print("❌ 无法加载GitLab配置")
        return False

    # 创建GitLab客户端
    gitlab_config = load_config()
    if not gitlab_config:
        print("❌ 无法加载GitLab环境配置")
        return False

    manager = GitLabIssueManager(gitlab_config['gitlab_url'], gitlab_config['private_token'])
    project_id = gitlab_config['project_id']

    # 加载用户映射
    print("👥 加载用户映射配置...")
    user_mapping_config = load_user_mapping()
    user_mapping = user_mapping_config.get('user_mapping', {})
    print(f"✅ 加载了 {len(user_mapping)} 个用户映射")

    # 获取数据库议题
    print("📋 获取数据库议题...")
    issues = get_database_issues()
    if not issues:
        print("✅ 没有找到状态为open且需要同步的议题")
        print("💡 提示：所有状态为open的议题都已经同步到GitLab了")
        return True

    print(f"✅ 找到 {len(issues)} 个状态为open且需要同步的议题")

    # 统计信息
    stats = {
        'total': len(issues),
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'failed': 0
    }

    # 处理每个议题
    for issue in issues:
        issue_id = issue.get('id')
        if not issue_id:
            print(f"⚠️  跳过无效议题: 缺少ID")
            continue

        project_name = issue.get('project_name', '')
        gitlab_url = issue.get('gitlab_url', '')
        sync_status = issue.get('sync_status', 'pending')
        operation_type = issue.get('operation_type', 'insert')

        print(f"\n🔄 处理议题 #{issue_id}: {project_name}")

        try:
            if gitlab_url and sync_status == 'synced':
                # 议题已同步，检查是否需要更新
                if operation_type == 'update':
                    print(f"  📝 议题已存在，需要更新")

                    # 获取现有GitLab议题
                    gitlab_issue = manager.get_issue(project_id, issue.get('gitlab_id', ''))
                    if gitlab_issue:
                        # 更新GitLab议题
                        updated_issue = update_gitlab_issue(issue, gitlab_issue, manager, project_id, config, user_mapping)
                        if updated_issue:
                            # 更新数据库
                            if update_database_issue(issue_id, updated_issue, 'update'):
                                print(f"  ✅ 议题更新成功")
                                stats['updated'] += 1
                            else:
                                print(f"  ❌ 数据库更新失败")
                                stats['failed'] += 1
                        else:
                            print(f"  ❌ GitLab议题更新失败")
                            stats['failed'] += 1
                    else:
                        print(f"  ⚠️  无法获取现有GitLab议题")
                        stats['failed'] += 1
                else:
                    print(f"  ⏭️  议题已同步，跳过")
                    stats['skipped'] += 1
            else:
                # 创建新的GitLab议题
                print(f"  🆕 创建新议题")

                gitlab_issue = create_gitlab_issue(issue, manager, project_id, config, user_mapping)
                if gitlab_issue:
                    # 更新数据库
                    if update_database_issue(issue_id, gitlab_issue, 'create'):
                        print(f"  ✅ 议题创建成功: {gitlab_issue.get('web_url', '')}")
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
    print(f"\n📊 同步结果:")
    print(f"  📋 总议题数: {stats['total']}")
    print(f"  🆕 新创建: {stats['created']}")
    print(f"  📝 已更新: {stats['updated']}")
    print(f"  ⏭️  跳过: {stats['skipped']}")
    print(f"  ❌ 失败: {stats['failed']}")

    return stats['failed'] == 0

def main() -> None:
    """
    主函数
    """
    success = sync_issues_to_gitlab()

    if success:
        print(f"\n🎉 同步完成!")
    else:
        print(f"\n💥 同步过程中出现错误!")
        sys.exit(1)

if __name__ == "__main__":
    main()
