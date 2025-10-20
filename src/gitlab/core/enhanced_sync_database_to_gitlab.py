#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版数据库到GitLab同步工具
支持进度跟踪和智能更新
"""

import os
import json
import requests
from typing import Dict, List, Optional, Any

def load_user_mapping() -> Dict[str, Any]:
    """
    加载用户映射配置
    """
    try:
        mapping_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'user_mapping.json')
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

def find_user_mapping(name: str, user_mapping: Dict[str, str]) -> Optional[str]:
    """智能查找用户映射"""
    # 直接匹配
    if name in user_mapping:
        return user_mapping[name]

    # 模糊匹配 - 检查是否包含关键词
    name_lower = name.lower()
    for mapped_name, gitlab_user in user_mapping.items():
        if name_lower in mapped_name.lower() or mapped_name.lower() in name_lower:
            print(f"🔍 模糊匹配: '{name}' → '{mapped_name}' → '{gitlab_user}'")
            return gitlab_user

    # 检查是否包含姓氏
    if len(name) >= 2:
        surname = name[-1]  # 取最后一个字符作为姓氏
        for mapped_name, gitlab_user in user_mapping.items():
            if mapped_name.endswith(surname):
                print(f"🔍 姓氏匹配: '{name}' → '{mapped_name}' → '{gitlab_user}'")
                return gitlab_user

    return None

def get_assignee_ids(manager, responsible_person: str, user_mapping: Dict[str, str]) -> Optional[List[int]]:
    """
    优化版获取指派人ID列表（支持多人指派）
    """
    try:
        assignee_ids = []

        # 检查是否包含分隔符（支持多种分隔符）
        separators = ['/', '、', ',', '，', ';', '；']
        person_list = [responsible_person]

        for sep in separators:
            if sep in responsible_person:
                person_list = [p.strip() for p in responsible_person.split(sep)]
                print(f"🔍 检测到多人责任人: '{responsible_person}' (分隔符: '{sep}')")
                print(f"   拆分为: {person_list}")
                break

        for person in person_list:
            if not person:  # 跳过空字符串
                continue

            # 查找用户映射
            gitlab_username = find_user_mapping(person, user_mapping)

            if gitlab_username:
                user_id = get_user_id_by_username(manager, gitlab_username)
                if user_id:
                    assignee_ids.append(user_id)
                    print(f"✅ 责任人 '{person}' → GitLab用户 '{gitlab_username}' (ID: {user_id})")
                else:
                    print(f"❌ 无法获取GitLab用户 '{gitlab_username}' 的ID")
            else:
                print(f"⚠️  未找到责任人 '{person}' 的映射")

        # 如果没有找到任何指派人，使用默认指派人
        if not assignee_ids:
            print(f"⚠️  无法获取任何指派人ID，使用默认指派人")
            default_username = user_mapping.get('default_assignee', 'kohill')
            user_id = get_user_id_by_username(manager, default_username)
            if user_id:
                assignee_ids.append(user_id)
                print(f"✅ 使用默认指派人: '{default_username}' (ID: {user_id})")
            else:
                print(f"❌ 无法获取默认指派人 '{default_username}' 的ID")

        return assignee_ids if assignee_ids else None

    except Exception as e:
        print(f"❌ 获取指派人ID异常: {e}")
        return None

def get_user_id_by_username(manager, username: str) -> Optional[int]:
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

def load_gitlab_config() -> Dict[str, Any]:
    """
    加载GitLab配置
    """
    config_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'wps_gitlab_config.json')
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

def create_gitlab_issue(issue_data: Dict[str, Any], manager, project_id: int, config: Dict[str, Any], user_mapping: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    在GitLab中创建议题
    """
    try:
        # 构建议题标题
        project_name = issue_data.get('project_name', '')
        problem_desc = issue_data.get('problem_description', '')

        title = (
            f"{project_name}: {problem_desc}" if project_name and problem_desc else
            project_name if project_name else
            f"议题 #{issue_data.get('id', '')}"
        )

        # 构建议题描述
        initiator = issue_data.get('initiator', '')
        description = f"## 提出人: {initiator}" if initiator else ""

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

        # 合并描述
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
