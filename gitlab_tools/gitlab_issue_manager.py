#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab 议题管理工具
支持创建、修改、关闭议题，以及标签管理
"""

import os
import sys
import requests
import json
from datetime import datetime
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
        self.user_mapping = self.load_user_mapping()

    def load_user_mapping(self) -> Dict[str, str]:
        """
        加载用户映射配置
        """
        mapping_file = os.path.join(os.path.dirname(__file__), 'user_mapping.json')
        try:
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('user_mapping', {})
        except Exception as e:
            print(f"⚠️  加载用户映射配置失败: {e}")
        return {}

    def get_gitlab_user_id(self, responsible_person: str) -> Optional[int]:
        """
        根据责任人姓名获取GitLab用户ID
        """
        if not responsible_person:
            return None

        # 查找映射的GitLab用户名
        gitlab_username = self.user_mapping.get(responsible_person)
        if not gitlab_username:
            print(f"⚠️  未找到责任人 '{responsible_person}' 的GitLab用户映射")
            return None

        # 获取GitLab用户ID
        try:
            url = f"{self.gitlab_url}/api/v4/users"
            params = {'username': gitlab_username}
            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                users = response.json()
                if users:
                    return users[0]['id']
                else:
                    print(f"⚠️  未找到GitLab用户: {gitlab_username}")
            else:
                print(f"⚠️  获取GitLab用户信息失败: {response.status_code}")
        except Exception as e:
            print(f"⚠️  获取GitLab用户ID异常: {e}")

        return None

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
            data['labels'] = ','.join(labels) if isinstance(labels, list) else labels
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

        Args:
            project_id: 项目ID
            issue_iid: 议题内部ID (iid)
            title: 新标题
            description: 新描述
            assignee_ids: 新的分配用户ID列表
            milestone_id: 新的里程碑ID
            labels: 新的标签列表
            due_date: 新的截止日期
            weight: 新的权重
            state_event: 状态事件 ('close', 'reopen')
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
            data['labels'] = ','.join(labels) if isinstance(labels, list) else labels
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
    env_file = os.path.join(os.path.dirname(__file__), 'config', 'gitlab.env')

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

def modify_and_close_issue() -> bool:
    """
    修改议题内容、标签并关闭议题
    """
    print("=" * 60)
    print("GitLab 议题管理工具 - 修改并关闭议题")
    print("=" * 60)

    # 加载配置
    config = load_config()
    if not config:
        return False

    print(f"GitLab URL: {config['gitlab_url']}")
    print(f"项目路径: {config['project_path']}")
    print(f"项目ID: {config['project_id']}")
    print()

    # 创建客户端
    manager = GitLabIssueManager(config['gitlab_url'], config['private_token'])

    # 获取项目信息
    print("📋 获取项目信息...")
    project_info = manager.get_project_info(config['project_id'])
    if not project_info:
        print("❌ 无法获取项目信息")
        return False

    print(f"项目名称: {project_info['name']}")
    print(f"项目URL: {project_info['web_url']}")
    print()

    # 列出最近的议题
    print("📝 最近的议题列表:")
    issues = manager.list_issues(config['project_id'], state='opened', per_page=10)
    if not issues:
        print("❌ 没有找到开放的议题")
        return False

    for i, issue in enumerate(issues, 1):
        print(f"{i}. [{issue['id']}] {issue['title']}")
        print(f"   状态: {issue['state']}")
        print(f"   标签: {', '.join(issue.get('labels', []))}")
        print(f"   创建时间: {issue['created_at']}")
        print()

    # 选择要修改的议题
    try:
        choice = input("请选择要修改的议题编号 (输入议题内部ID): ").strip()
        issue_iid = int(choice)
    except ValueError:
        print("❌ 请输入有效的议题内部ID")
        return False

    # 获取议题详情
    print(f"\n🔍 获取议题 #{issue_iid} 详情...")
    issue = manager.get_issue(config['project_id'], issue_iid)
    if not issue:
        print(f"❌ 无法获取议题 #{issue_iid}")
        return False

    print(f"当前标题: {issue['title']}")
    print(f"当前状态: {issue['state']}")
    print(f"当前标签: {', '.join(issue.get('labels', []))}")
    print()

    # 修改议题
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_title = f"已修改的议题 - {issue['title']} - {current_time}"
    new_description = f"""
## 议题修改记录

### 原始议题
- **原始标题**: {issue['title']}
- **原始状态**: {issue['state']}
- **原始标签**: {', '.join(issue.get('labels', []))}

### 修改信息
- **修改时间**: {current_time}
- **修改方式**: Python 脚本自动化
- **修改内容**: 更新标题、描述、标签并关闭

### 修改后的内容
- **新标题**: {new_title}
- **新状态**: 已关闭
- **新标签**: test, modified, closed, automation

### 技术信息
- **修改工具**: GitLab Issue Manager
- **API版本**: GitLab API v4
- **操作类型**: 议题修改和关闭

---
*此议题已通过自动化脚本修改并关闭*
    """

    new_labels = ['test', 'modified', 'closed', 'automation', 'server-updated']

    print("🔧 修改议题...")
    updated_issue = manager.update_issue(
        project_id=config['project_id'],
        issue_iid=issue_iid,
        title=new_title,
        description=new_description,
        labels=new_labels
    )

    if not updated_issue:
        print("❌ 修改议题失败")
        return False

    print("✅ 议题修改成功!")
    print(f"新标题: {updated_issue['title']}")
    print(f"新标签: {', '.join(updated_issue.get('labels', []))}")
    print()

    # 关闭议题
    print("🔒 关闭议题...")
    closed_issue = manager.close_issue(config['project_id'], issue_iid)

    if not closed_issue:
        print("❌ 关闭议题失败")
        return False

    print("✅ 议题关闭成功!")
    print(f"议题状态: {closed_issue['state']}")
    print(f"议题URL: {closed_issue['web_url']}")
    print(f"关闭时间: {closed_issue['updated_at']}")

    return True

def show_usage() -> None:
    """
    显示使用说明
    """
    print("=" * 60)
    print("GitLab 议题管理工具 - 使用说明")
    print("=" * 60)
    print()
    print("🚀 功能:")
    print("   - 创建议题")
    print("   - 修改议题内容")
    print("   - 更新议题标签")
    print("   - 关闭/重新打开议题")
    print("   - 查看议题列表")
    print()
    print("📁 配置文件: gitlab.env")
    print("🔧 环境变量:")
    print("   GITLAB_URL=https://dev.heils.cn")
    print("   GITLAB_PRIVATE_TOKEN=glpat-xxxxxxxxxxxx")
    print("   GITLAB_PROJECT_ID=1")
    print("   GITLAB_PROJECT_PATH=aoi/aoi-demo-r")
    print()
    print("💡 使用方法:")
    print("   python3 gitlab_issue_manager.py")
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_usage()
    else:
        success = modify_and_close_issue()
        if success:
            print("\n🎉 操作完成!")
        else:
            print("\n💥 操作失败!")
            sys.exit(1)

