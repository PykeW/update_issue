#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库操作核心模块
统一管理所有数据库相关操作
"""

import subprocess
from typing import Dict, List, Optional, Any, Union

# 数据库配置
DB_CONFIG: Dict[str, Union[str, int]] = {
    'host': 'localhost',
    'port': 3306,
    'user': 'issue',
    'password': 'hszc8888',
    'database': 'issue_database'
}

class DatabaseManager:
    """数据库管理器"""

    def __init__(self):
        self.config = DB_CONFIG

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        执行SQL查询并返回结果
        """
        try:
            cmd: List[str] = [
                'mysql', '-u', str(self.config['user']), f'-p{str(self.config["password"])}',
                '-h', str(self.config['host']), '-P', str(self.config['port']),
                '-e', f"USE {self.config['database']}; {query}"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # 解析MySQL输出
            lines = result.stdout.strip().split('\n')
            if len(lines) < 2:
                return []

            # 获取列名
            headers = lines[0].split('\t')
            data: List[Dict[str, Any]] = []

            # 解析数据行
            for line in lines[1:]:
                values = line.split('\t')
                if len(values) == len(headers):
                    row = dict(zip(headers, values))
                    data.append(row)

            return data
        except Exception as e:
            print(f"❌ 数据库查询失败: {e}")
            return []

    def execute_update(self, query: str) -> bool:
        """
        执行SQL更新操作
        """
        try:
            cmd: List[str] = [
                'mysql', '-u', str(self.config['user']), f'-p{str(self.config["password"])}',
                '-h', str(self.config['host']), '-P', str(self.config['port']),
                '-e', f"USE {self.config['database']}; {query}"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            # 检查返回码，0表示成功
            # 忽略警告信息，只检查是否有真正的错误
            if result.returncode == 0:
                return True
            else:
                print(f"❌ 数据库更新失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 数据库更新异常: {e}")
            return False

    def get_issues_without_gitlab_url(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取没有GitLab URL的议题
        """
        query = f"""
        SELECT id, project_name, problem_category, severity_level, problem_description,
               solution, action_priority, action_record, initiator, responsible_person,
               status, start_time, target_completion_time, actual_completion_time,
               remarks, gitlab_url, sync_status, last_sync_time, gitlab_progress
        FROM issues
        WHERE (gitlab_url IS NULL OR gitlab_url = '')
        AND status = 'open'
        AND (sync_status IS NULL OR sync_status = 'pending' OR sync_status = 'failed')
        ORDER BY id
        LIMIT {limit};
        """
        return self.execute_query(query)

    def get_issues_with_gitlab_url(self) -> List[Dict[str, Any]]:
        """
        获取所有有GitLab URL的议题
        """
        query = """
        SELECT id, project_name, problem_description, problem_category, solution,
               action_record, remarks, gitlab_url, gitlab_progress, sync_status, status
        FROM issues
        WHERE gitlab_url IS NOT NULL AND gitlab_url != ''
        ORDER BY id;
        """
        return self.execute_query(query)

    def update_issue_gitlab_info(self, issue_id: int, gitlab_url: str,
                                gitlab_progress: str = '', sync_status: str = 'synced') -> bool:
        """
        更新议题的GitLab信息
        """
        query = f"""
        UPDATE issues SET
            gitlab_url = '{gitlab_url}',
            gitlab_progress = '{gitlab_progress}',
            sync_status = '{sync_status}',
            last_sync_time = CURRENT_TIMESTAMP
        WHERE id = {issue_id};
        """
        return self.execute_update(query)

    def update_issue_progress(self, issue_id: int, gitlab_progress: str) -> bool:
        """
        更新议题进度
        """
        query = f"""
        UPDATE issues SET
            gitlab_progress = '{gitlab_progress}'
        WHERE id = {issue_id};
        """
        return self.execute_update(query)

    def get_pending_queue_items(self) -> List[Dict[str, Any]]:
        """
        获取待处理的同步队列项
        """
        query = """
        SELECT id, issue_id, action, created_at
        FROM sync_queue
        WHERE status = 'pending'
        ORDER BY created_at
        LIMIT 10;
        """
        return self.execute_query(query)

    def update_queue_status(self, queue_id: int, status: str, error_message: Optional[str] = None) -> bool:
        """
        更新队列项状态
        """
        error_sql = f", error_message = '{error_message}'" if error_message else ""
        query = f"""
        UPDATE sync_queue SET
            status = '{status}',
            processed_at = NOW(){error_sql}
        WHERE id = {queue_id};
        """
        return self.execute_update(query)

    def add_to_sync_queue(self, issue_id: int, action: str) -> bool:
        """
        添加项目到同步队列
        """
        query = f"""
        INSERT INTO sync_queue (issue_id, action, created_at)
        VALUES ({issue_id}, '{action}', NOW());
        """
        return self.execute_update(query)

    def get_issue_by_id(self, issue_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取议题
        """
        query = f"""
        SELECT id, project_name, problem_category, severity_level, problem_description,
               solution, action_priority, action_record, initiator, responsible_person,
               status, start_time, target_completion_time, actual_completion_time,
               remarks, gitlab_url, sync_status, last_sync_time, gitlab_progress
        FROM issues
        WHERE id = {issue_id};
        """
        results = self.execute_query(query)
        return results[0] if results else None

    def update_issue(self, issue_id: int, **kwargs) -> bool:
        """
        更新议题信息
        """
        try:
            # 构建更新字段
            update_fields = []
            for key, value in kwargs.items():
                if value is not None:
                    if isinstance(value, str):
                        update_fields.append(f"{key} = '{value}'")
                    else:
                        update_fields.append(f"{key} = {value}")

            if not update_fields:
                return True

            # 添加时间戳
            update_fields.append("last_sync_time = NOW()")

            query = f"""
            UPDATE issues SET
                {', '.join(update_fields)}
            WHERE id = {issue_id};
            """

            return self.execute_update(query)
        except Exception as e:
            print(f"❌ 更新议题失败: {e}")
            return False
