#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab 议题管理工具
支持创建、修改、关闭议题，以及标签管理
"""

import os
import requests
from typing import Dict, List, Optional, Any, Union

class GitLabIssueManager:
    def __init__(self, gitlab_url: str, private_token: str) -> None:
        """
        初始化 GitLab API 客户端
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.headers = {
            'Private-Token': private_token,
            'Content-Type': 'application/json'
        }

    def create_issue(self, project_id: int, title: str, description: Optional[str] = None,
                    assignee_ids: Optional[List[int]] = None, milestone_id: Optional[int] = None,
                    labels: Optional[List[str]] = None, due_date: Optional[str] = None,
                    weight: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        创建 GitLab 议题
        """
        api_url = f"{self.gitlab_url}/api/v4/projects/{project_id}/issues"

        data: Dict[str, Any] = {'title': title}
        if description:
            data['description'] = description
        if assignee_ids:
            data['assignee_ids'] = assignee_ids
        if milestone_id:
            data['milestone_id'] = milestone_id
        if labels:
            data['labels'] = ','.join(labels)
        if due_date:
            data['due_date'] = due_date
        if weight:
            data['weight'] = weight

        try:
            response = requests.post(api_url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ 创建议题时发生错误: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"响应状态码: {e.response.status_code}")
                print(f"响应内容: {e.response.text}")
            return None

    def update_issue(self, project_id: int, issue_iid: int, title: Optional[str] = None,
                    description: Optional[str] = None, assignee_ids: Optional[List[int]] = None,
                    milestone_id: Optional[int] = None, labels: Optional[List[str]] = None,
                    due_date: Optional[str] = None, weight: Optional[int] = None,
                    state_event: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        更新 GitLab 议题
        """
        api_url = f"{self.gitlab_url}/api/v4/projects/{project_id}/issues/{issue_iid}"

        data: Dict[str, Any] = {}
        if title:
            data['title'] = title
        if description:
            data['description'] = description
        if assignee_ids:
            data['assignee_ids'] = assignee_ids
        if milestone_id:
            data['milestone_id'] = milestone_id
        if labels:
            data['labels'] = ','.join(labels)
        if due_date:
            data['due_date'] = due_date
        if weight:
            data['weight'] = weight
        if state_event:
            data['state_event'] = state_event

        try:
            response = requests.put(api_url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ 更新议题时发生错误: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"响应状态码: {e.response.status_code}")
                print(f"响应内容: {e.response.text}")
            return None

    def close_issue(self, project_id: int, issue_iid: int) -> Optional[Dict[str, Any]]:
        """
        关闭议题
        """
        return self.update_issue(project_id, issue_iid, state_event='close')

    def reopen_issue(self, project_id: int, issue_iid: int) -> Optional[Dict[str, Any]]:
        """
        重新打开议题
        """
        return self.update_issue(project_id, issue_iid, state_event='reopen')

    def get_issue(self, project_id: int, issue_iid: int) -> Optional[Dict[str, Any]]:
        """
        获取议题详情
        """
        api_url = f"{self.gitlab_url}/api/v4/projects/{project_id}/issues/{issue_iid}"

        try:
            response = requests.get(api_url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取议题详情时发生错误: {e}")
            return None

    def list_issues(self, project_id: int, state: str = 'opened', per_page: int = 20) -> Optional[List[Dict[str, Any]]]:
        """
        列出项目中的议题
        """
        api_url = f"{self.gitlab_url}/api/v4/projects/{project_id}/issues"
        params: Dict[str, Union[str, int]] = {
            'state': state,
            'per_page': per_page
        }

        try:
            response = requests.get(api_url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取议题列表时发生错误: {e}")
            return None

    def get_project_info(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        获取项目信息
        """
        api_url = f"{self.gitlab_url}/api/v4/projects/{project_id}"

        try:
            response = requests.get(api_url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取项目信息时发生错误: {e}")
            return None

def load_config() -> Optional[Dict[str, Any]]:
    """
    从环境变量加载配置
    """
    # 尝试从gitlab.env文件读取配置
    config: Dict[str, str] = {}
    env_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'gitlab.env')

    if os.path.exists(env_file):
        print("✅ 从 gitlab.env 文件加载配置")
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        except Exception as e:
            print(f"⚠️  读取配置文件失败: {e}")
    else:
        print("⚠️  未找到环境配置文件，使用系统环境变量")

    # 从环境变量获取配置
    gitlab_url = os.getenv('GITLAB_URL', config.get('GITLAB_URL', ''))
    private_token = os.getenv('GITLAB_PRIVATE_TOKEN', config.get('GITLAB_PRIVATE_TOKEN', ''))
    project_id = os.getenv('GITLAB_PROJECT_ID', config.get('GITLAB_PROJECT_ID', ''))
    project_path = os.getenv('GITLAB_PROJECT_PATH', config.get('GITLAB_PROJECT_PATH', ''))

    config.update({
        'gitlab_url': gitlab_url,
        'private_token': private_token,
        'project_id': project_id,
        'project_path': project_path
    })

    missing: List[str] = [k for k, v in config.items() if not v]
    if missing:
        print(f"❌ 缺少必需配置: {', '.join(missing)}")
        return None

    return config
