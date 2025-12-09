#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pyright: reportMissingTypeStubs=none
"""
GitLab 议题管理工具
支持创建、修改、关闭议题，以及标签管理
"""

import os
from typing import cast
import json
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError
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
            req = urllib.request.Request(api_url, method='POST')
            for k, v in self.headers.items():
                req.add_header(k, v)
            body = json.dumps(data).encode('utf-8')
            with urllib.request.urlopen(req, body, timeout=30) as resp:
                resp_body = resp.read().decode('utf-8')
                result = cast(Dict[str, Any], json.loads(resp_body))
                return result
        except HTTPError as e:
            print(f"❌ 创建议题时发生错误: HTTP {e.code}")
            try:
                print(e.read().decode('utf-8'))
            except Exception:
                pass
            return None
        except URLError as e:
            print(f"❌ 创建议题网络错误: {e}")
            return None
        except Exception as e:
            print(f"❌ 创建议题异常: {e}")
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
            req = urllib.request.Request(api_url, method='PUT')
            for k, v in self.headers.items():
                req.add_header(k, v)
            body = json.dumps(data).encode('utf-8')
            with urllib.request.urlopen(req, body, timeout=30) as resp:
                resp_body = resp.read().decode('utf-8')
                result = cast(Dict[str, Any], json.loads(resp_body))
                return result
        except HTTPError as e:
            print(f"❌ 更新议题时发生错误: HTTP {e.code}")
            try:
                print(e.read().decode('utf-8'))
            except Exception:
                pass
            return None
        except URLError as e:
            print(f"❌ 更新议题网络错误: {e}")
            return None
        except Exception as e:
            print(f"❌ 更新议题异常: {e}")
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
            req = urllib.request.Request(api_url, method='GET')
            for k, v in self.headers.items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode('utf-8')
                result = cast(Dict[str, Any], json.loads(resp_body))
                return result
        except HTTPError as e:
            print(f"❌ 获取议题详情时发生错误: HTTP {e.code}")
            return None
        except URLError as e:
            print(f"❌ 获取议题详情网络错误: {e}")
            return None
        except Exception as e:
            print(f"❌ 获取议题详情异常: {e}")
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
            url = api_url + '?' + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, method='GET')
            for k, v in self.headers.items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode('utf-8')
                result = cast(List[Dict[str, Any]], json.loads(resp_body))
                return result
        except HTTPError as e:
            print(f"❌ 获取议题列表时发生错误: HTTP {e.code}")
            return None
        except URLError as e:
            print(f"❌ 获取议题列表网络错误: {e}")
            return None
        except Exception as e:
            print(f"❌ 获取议题列表异常: {e}")
            return None

    def get_project_info(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        获取项目信息
        """
        api_url = f"{self.gitlab_url}/api/v4/projects/{project_id}"

        try:
            req = urllib.request.Request(api_url, method='GET')
            for k, v in self.headers.items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode('utf-8')
                result = cast(Dict[str, Any], json.loads(resp_body))
                return result
        except HTTPError as e:
            print(f"❌ 获取项目信息时发生错误: HTTP {e.code}")
            return None
        except URLError as e:
            print(f"❌ 获取项目信息网络错误: {e}")
            return None
        except Exception as e:
            print(f"❌ 获取项目信息异常: {e}")
            return None

def load_config() -> Optional[Dict[str, Any]]:
    """
    加载 GitLab 配置，从 wps_gitlab_config.json 加载。
    系统环境变量优先级最高（如果设置了）。
    返回统一键名: gitlab_url/private_token/project_id/project_path
    """
    # 优先：系统环境变量
    gitlab_url = os.getenv('GITLAB_URL', '')
    private_token = os.getenv('GITLAB_PRIVATE_TOKEN', '')
    project_id = os.getenv('GITLAB_PROJECT_ID', '')
    project_path = os.getenv('GITLAB_PROJECT_PATH', '')

    # 如果环境变量已设置完整，直接返回
    if gitlab_url and private_token and project_id and project_path:
        print("✅ 从系统环境变量加载配置")
        return {
            'gitlab_url': gitlab_url,
            'private_token': private_token,
            'project_id': project_id,
            'project_path': project_path
        }

    # 从 wps_gitlab_config.json 加载配置
    try:
        from .config_manager import ConfigManager
        cfg_mgr = ConfigManager()
        full = cfg_mgr.load_full_config()
        if not full:
            print("❌ 无法加载 JSON 配置 wps_gitlab_config.json")
            return None
        gitlab = full.get('gitlab', {})
        config = {
            'gitlab_url': gitlab.get('url', ''),
            'private_token': gitlab.get('token', ''),
            'project_id': str(gitlab.get('project_id', '')),
            'project_path': gitlab.get('project_path', '')
        }
        # 环境变量覆盖JSON配置
        if gitlab_url:
            config['gitlab_url'] = gitlab_url
        if private_token:
            config['private_token'] = private_token
        if project_id:
            config['project_id'] = project_id
        if project_path:
            config['project_path'] = project_path

        missing: List[str] = [k for k, v in config.items() if not v]
        if missing:
            print(f"❌ 缺少必需配置: {', '.join(missing)}")
            return None
        print("✅ 从 wps_gitlab_config.json 加载配置")
        return config
    except Exception as e:
        print(f"❌ 加载 JSON 配置失败: {e}")
        return None
