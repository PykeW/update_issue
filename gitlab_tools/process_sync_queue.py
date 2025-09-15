#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步队列处理脚本
处理数据库中的同步队列，自动创建和关闭GitLab议题
"""

import os
import sys
import subprocess
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gitlab_issue_manager import GitLabIssueManager, load_config
from enhanced_sync_database_to_gitlab import create_gitlab_issue, update_gitlab_issue, load_gitlab_config, load_user_mapping

# 数据库配置
DB_CONFIG: Dict[str, Union[str, int]] = {
    'host': 'localhost',
    'port': 3306,
    'user': 'issue',
    'password': 'hszc8888',
    'database': 'issue_database'
}

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/update_issue/gitlab_tools/queue.log'),
        logging.StreamHandler()
    ]
)

def get_pending_queue_items() -> List[Dict[str, Any]]:
    """
    获取待处理的同步队列项
    """
    try:
        cmd: List[str] = [
            'mysql', '-u', str(DB_CONFIG['user']), f'-p{str(DB_CONFIG["password"])}',
            '-h', str(DB_CONFIG['host']), '-P', str(DB_CONFIG['port']),
            '-e', f"""
            USE {DB_CONFIG['database']};
            SELECT id, issue_id, action, created_at
            FROM sync_queue
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT 10;
            """
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # 解析MySQL输出
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return []

        # 获取列名
        headers = lines[0].split('\t')
        items: List[Dict[str, Any]] = []

        # 解析数据行
        for line in lines[1:]:
            values = line.split('\t')
            if len(values) == len(headers):
                item = dict(zip(headers, values))
                items.append(item)

        return items
    except Exception as e:
        logging.error(f"获取同步队列失败: {e}")
        return []

def update_queue_status(queue_id: int, status: str, error_message: str = None) -> bool:
    """
    更新队列项状态
    """
    try:
        error_sql = f", error_message = '{error_message}'" if error_message else ""

        cmd: List[str] = [
            'mysql', '-u', str(DB_CONFIG['user']), f'-p{str(DB_CONFIG["password"])}',
            '-h', str(DB_CONFIG['host']), '-P', str(DB_CONFIG['port']),
            '-e', f"""
            USE {DB_CONFIG['database']};
            UPDATE sync_queue SET
                status = '{status}',
                processed_at = NOW(){error_sql}
            WHERE id = {queue_id};
            """
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.returncode == 0
    except Exception as e:
        logging.error(f"更新队列状态失败: {e}")
        return False

def get_issue_data(issue_id: int) -> Optional[Dict[str, Any]]:
    """
    获取议题数据
    """
    try:
        cmd: List[str] = [
            'mysql', '-u', str(DB_CONFIG['user']), f'-p{str(DB_CONFIG["password"])}',
            '-h', str(DB_CONFIG['host']), '-P', str(DB_CONFIG['port']),
            '-e', f"""
            USE {DB_CONFIG['database']};
            SELECT id, project_name, problem_category, severity_level, problem_description,
                   solution, action_priority, action_record, initiator, responsible_person,
                   status, start_time, target_completion_time, actual_completion_time,
                   remarks, gitlab_url, sync_status, last_sync_time, gitlab_progress
            FROM issues
            WHERE id = {issue_id};
            """
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # 解析MySQL输出
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return None

        # 获取列名
        headers = lines[0].split('\t')
        values = lines[1].split('\t')

        if len(values) == len(headers):
            return dict(zip(headers, values))
        return None
    except Exception as e:
        logging.error(f"获取议题数据失败: {e}")
        return None

def process_queue_item(item: Dict[str, Any]) -> bool:
    """
    处理单个队列项
    """
    queue_id = item.get('id')
    issue_id = item.get('issue_id')
    action = item.get('action')

    logging.info(f"处理队列项 {queue_id}: 议题 {issue_id}, 动作 {action}")

    try:
        # 更新状态为处理中
        update_queue_status(queue_id, 'processing')

        # 获取议题数据
        issue_data = get_issue_data(issue_id)
        if not issue_data:
            logging.error(f"无法获取议题 {issue_id} 的数据")
            update_queue_status(queue_id, 'failed', '无法获取议题数据')
            return False

        # 加载配置
        gitlab_config = load_config()
        if not gitlab_config:
            logging.error("无法加载GitLab配置")
            update_queue_status(queue_id, 'failed', '无法加载GitLab配置')
            return False

        manager = GitLabIssueManager(gitlab_config['gitlab_url'], gitlab_config['private_token'])
        project_id = gitlab_config['project_id']
        config = load_gitlab_config()
        user_mapping_config = load_user_mapping()
        user_mapping = user_mapping_config.get('user_mapping', {})

        if action == 'create':
            # 创建GitLab议题
            gitlab_issue = create_gitlab_issue(issue_data, manager, project_id, config, user_mapping)
            if gitlab_issue:
                logging.info(f"✅ 议题 {issue_id} 创建成功")
                update_queue_status(queue_id, 'completed')
                return True
            else:
                logging.error(f"❌ 议题 {issue_id} 创建失败")
                update_queue_status(queue_id, 'failed', 'GitLab议题创建失败')
                return False

        elif action == 'close':
            # 关闭GitLab议题
            gitlab_url = issue_data.get('gitlab_url', '')
            if not gitlab_url:
                logging.warning(f"议题 {issue_id} 没有GitLab URL，跳过关闭")
                update_queue_status(queue_id, 'completed')
                return True

            # 提取议题ID
            import re
            pattern = r'/issues/(\d+)$'
            match = re.search(pattern, gitlab_url)
            if not match:
                logging.error(f"无法从URL提取议题ID: {gitlab_url}")
                update_queue_status(queue_id, 'failed', '无法从URL提取议题ID')
                return False

            issue_iid = int(match.group(1))

            # 关闭议题
            from sync_gitlab_progress import close_gitlab_issue
            if close_gitlab_issue(manager, project_id, issue_iid, issue_data):
                logging.info(f"✅ 议题 {issue_id} 关闭成功")
                update_queue_status(queue_id, 'completed')
                return True
            else:
                logging.error(f"❌ 议题 {issue_id} 关闭失败")
                update_queue_status(queue_id, 'failed', 'GitLab议题关闭失败')
                return False
        else:
            logging.error(f"未知动作: {action}")
            update_queue_status(queue_id, 'failed', f'未知动作: {action}')
            return False

    except Exception as e:
        logging.error(f"处理队列项异常: {e}")
        update_queue_status(queue_id, 'failed', str(e))
        return False

def process_sync_queue():
    """
    处理同步队列
    """
    logging.info("开始处理同步队列")

    # 获取待处理项
    items = get_pending_queue_items()
    if not items:
        logging.info("没有待处理的队列项")
        return

    logging.info(f"找到 {len(items)} 个待处理项")

    # 处理每个项
    success_count = 0
    for item in items:
        if process_queue_item(item):
            success_count += 1

    logging.info(f"队列处理完成: {success_count}/{len(items)} 成功")

if __name__ == "__main__":
    process_sync_queue()
