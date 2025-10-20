#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab操作核心模块
统一管理所有GitLab相关操作
"""

import re
from typing import Dict, Optional, Any, List
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from gitlab_issue_manager import GitLabIssueManager, load_config

class GitLabOperations:
    """GitLab操作管理器"""

    def __init__(self):
        self.config = load_config()
        if not self.config:
            raise ValueError("无法加载GitLab配置")

        self.manager = GitLabIssueManager(
            self.config['gitlab_url'],
            self.config['private_token']
        )
        self.project_id = int(self.config['project_id'])

    def extract_issue_id_from_url(self, gitlab_url: str) -> Optional[int]:
        """
        从GitLab URL中提取议题的内部ID (iid)
        """
        match = re.search(r'/-/issues/(\d+)', gitlab_url)
        if match:
            return int(match.group(1))
        return None

    def get_issue_progress(self, gitlab_issue: Dict[str, Any]) -> str:
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

    def close_issue(self, issue_iid: int, issue_data: Dict[str, Any]) -> bool:
        """
        关闭GitLab议题并更新描述
        """
        try:
            # 构建关闭时的描述
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 获取原始描述
            gitlab_issue = self.manager.get_issue(self.project_id, issue_iid)
            if not gitlab_issue:
                return False

            original_description = gitlab_issue.get('description', '')

            # 构建关闭信息
            close_info = f"""

---

## 议题关闭信息
- **关闭时间**: {current_time}
- **关闭原因**: 数据库状态已更新为closed
- **项目名称**: {issue_data.get('project_name') or ''}
- **问题分类**: {issue_data.get('problem_category') or ''}
- **解决方案**: {issue_data.get('solution') or ''}
- **行动记录**: {issue_data.get('action_record') or ''}
- **备注**: {issue_data.get('remarks') or ''}

*此议题已通过自动化系统关闭*
            """

            # 合并描述
            new_description = (original_description or '') + close_info

            # 获取当前标签并移除进度标签
            current_labels = gitlab_issue.get('labels', [])
            updated_labels = [label for label in current_labels if not label.startswith('进度::')]

            # 更新议题（关闭并更新描述和标签）
            updated_issue = self.manager.update_issue(
                project_id=self.project_id,
                issue_iid=issue_iid,
                description=new_description,
                labels=updated_labels,
                state_event='close'
            )

            return updated_issue is not None

        except Exception as e:
            print(f"❌ 关闭GitLab议题异常: {e}")
            return False

    def get_issue(self, issue_iid: int) -> Optional[Dict[str, Any]]:
        """
        获取GitLab议题
        """
        return self.manager.get_issue(self.project_id, issue_iid)

    def create_issue(self, issue_data: Dict[str, Any], config: Dict[str, Any],
                    user_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        创建GitLab议题
        """
        try:
            # 导入创建议题函数
            from .enhanced_sync_database_to_gitlab import create_gitlab_issue

            # 创建议题
            gitlab_issue = create_gitlab_issue(issue_data, self.manager, self.project_id, config, user_mapping)

            if gitlab_issue:
                return {
                    'success': True,
                    'url': gitlab_issue.get('web_url', ''),
                    'progress': self.get_issue_progress(gitlab_issue),
                    'issue': gitlab_issue
                }
            else:
                return {
                    'success': False,
                    'error': '创建GitLab议题失败'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def extract_progress_from_labels(self, labels: List[str]) -> str:
        """
        从标签列表中提取进度信息
        """
        for label in labels:
            if label.startswith('进度::'):
                return label
        return '进度::To do'

