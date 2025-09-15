#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版WPS数据接收API服务器
支持智能数据更新、GitLab同步和进度跟踪
"""

import logging
import subprocess
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from typing import Dict, List, Optional, Any, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/wps_api_enhanced.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据库配置
DB_CONFIG: Dict[str, Union[str, int]] = {
    'host': 'localhost',
    'port': 3306,
    'user': 'issue',
    'password': 'hszc8888',
    'database': 'issue_database'
}

class EnhancedWPSAPIHandler(BaseHTTPRequestHandler):
    """增强版WPS API请求处理器"""

    def escape_sql_string(self, value: Any) -> str:
        """安全地转义SQL字符串"""
        return str(value).replace("'", "\\'")

    def build_mysql_command(self, sql_query: str) -> List[str]:
        """构建MySQL命令"""
        return [
            'mysql', '-u', str(DB_CONFIG['user']), f'-p{str(DB_CONFIG["password"])}',
            '-h', str(DB_CONFIG['host']), '-P', str(DB_CONFIG['port']),
            '-e', sql_query
        ]

    def map_status(self, status: str) -> str:
        """映射状态值到数据库枚举值"""
        status_mapping = {
            'C': 'closed',
            'O': 'open',
            'P': 'in_progress',
            'R': 'resolved',
            'open': 'open',
            'in_progress': 'in_progress',
            'closed': 'closed',
            'resolved': 'resolved'
        }
        return status_mapping.get(status, 'open')

    def safe_convert_int(self, value: Any, default: int = 0) -> int:
        """安全转换为整数"""
        try:
            if value is None or str(value).strip() == '':
                return default
            # 先转换为字符串，然后处理
            str_value = str(value).strip()
            # 如果是空字符串或None，返回默认值
            if not str_value or str_value.lower() in ['none', 'null', 'nan']:
                return default
            # 转换为浮点数再转整数，处理 "2.0" 这种情况
            return int(float(str_value))
        except (ValueError, TypeError):
            return default

    def do_GET(self) -> None:
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # 使用字典映射提高路由效率
        get_routes = {
            '/': self.health_check,
            '/api/status': self.get_status,
            '/api/database/issues': self.get_issues,
            '/api/gitlab/sync-status': self.get_gitlab_sync_status
        }

        handler = get_routes.get(path)
        if handler:
            handler()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        """处理POST请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # 使用字典映射提高路由效率
        post_routes = {
            '/api/wps/upload': self.upload_wps_data,
            '/api/gitlab/sync': self.sync_to_gitlab,
            '/api/gitlab/update-progress': self.update_gitlab_progress
        }

        handler = post_routes.get(path)
        if handler:
            handler()
        else:
            self.send_error(404, "Not Found")

    def health_check(self) -> None:
        """健康检查"""
        response: Dict[str, Any] = {
            "status": "running",
            "service": "Enhanced WPS Data Receiver",
            "port": 80,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "features": [
                "智能数据更新",
                "GitLab同步",
                "进度跟踪"
            ]
        }
        self.send_json_response(response)

    def get_status(self) -> None:
        """获取服务状态"""
        try:
            # 检查数据库连接
            db_status = self.check_database_connection()

            # 获取数据库统计信息
            stats = self.get_database_stats()

            response: Dict[str, Any] = {
                "service": "Enhanced WPS Data Receiver",
                "status": "running",
                "database_connected": db_status,
                "database_stats": stats,
                "timestamp": datetime.now().isoformat()
            }
            self.send_json_response(response)
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
            self.send_error(500, str(e))

    def upload_wps_data(self) -> None:
        """处理WPS数据上传"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            if 'table_data' not in data:
                self.send_error(400, "缺少table_data字段")
                return

            table_data = data['table_data']
            logger.info(f"接收到WPS数据: {len(table_data)} 条记录")

            # 处理数据
            result = self.process_wps_data(table_data)

            response: Dict[str, Any] = {
                "success": True,
                "message": f"成功处理 {len(table_data)} 条记录",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            self.send_json_response(response)

        except Exception as e:
            logger.error(f"处理WPS数据失败: {e}")
            self.send_error(500, str(e))

    def process_wps_data(self, table_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """处理WPS数据，支持智能更新"""
        results: Dict[str, Any] = {
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "details": []
        }

        for row_data in table_data:
            try:
                # 检查是否已存在
                existing_issue = self.find_existing_issue(
                    row_data.get('project_name', ''),
                    row_data.get('problem_description', '')
                )

                if existing_issue:
                    # 更新现有记录
                    if self.should_update_issue(existing_issue, row_data):
                        update_result = self.update_issue(existing_issue['id'], row_data)
                        if update_result:
                            results["updated"] += 1
                            results["details"].append({
                                "project_name": row_data.get('project_name', ''),
                                "action": "updated",
                                "issue_id": existing_issue['id']
                            })
                            logger.info(f"议题 {existing_issue['id']} 更新成功")
                        else:
                            results["failed"] += 1
                            results["details"].append({
                                "project_name": row_data.get('project_name', ''),
                                "action": "update_failed",
                                "error": "更新失败"
                            })
                            logger.error(f"议题 {existing_issue['id']} 更新失败")
                    else:
                        # 数据无变化，跳过更新，但记录为成功
                        results["skipped"] += 1
                        results["details"].append({
                            "project_name": row_data.get('project_name', ''),
                            "action": "no_change",
                            "issue_id": existing_issue['id']
                        })
                        logger.info(f"议题 {existing_issue['id']} 无变化，跳过更新 (problem_description + project_name 完全匹配)")
                else:
                    # 插入新记录
                    insert_result = self.insert_issue(row_data)
                    if insert_result:
                        results["inserted"] += 1
                        results["details"].append({
                            "project_name": row_data.get('project_name', ''),
                            "action": "inserted",
                            "issue_id": insert_result
                        })
                    else:
                        results["failed"] += 1
                        results["details"].append({
                            "project_name": row_data.get('project_name', ''),
                            "action": "insert_failed",
                            "error": "插入失败"
                        })

            except Exception as e:
                error_msg = f"处理单条记录失败: {e}"
                logger.error(error_msg)
                logger.error(f"记录数据: {row_data}")
                results["failed"] += 1
                results["details"].append({
                    "project_name": row_data.get('project_name', ''),
                    "action": "failed",
                    "error": error_msg
                })

        return results


    def find_existing_issue(self, project_name: str, problem_description: str = '') -> Optional[Dict[str, Any]]:
        """查找现有议题 - 以problem_description为主键匹配"""
        try:
            # 以problem_description为主键，如果相同再比较project_name
            if problem_description:
                sql_query = f"""
                    USE {DB_CONFIG['database']};
                    SELECT * FROM issues
                    WHERE problem_description = '{self.escape_sql_string(problem_description)}'
                    AND project_name = '{self.escape_sql_string(project_name)}'
                    ORDER BY updated_at DESC
                    LIMIT 1;
                    """
            else:
                return None

            cmd = self.build_mysql_command(sql_query)
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # 有数据行
                    headers = lines[0].split('\t')
                    values = lines[1].split('\t')
                    return dict(zip(headers, values))

            return None
        except Exception as e:
            logger.error(f"查找现有议题失败: {e}")
            return None

    def should_update_issue(self, existing_issue: Dict[str, Any], new_data: Dict[str, Any]) -> bool:
        """判断是否需要更新议题 - 以problem_description为主键的智能比较"""
        # 首先确认problem_description和project_name相同（这是匹配条件）
        existing_desc = str(existing_issue.get('problem_description', '')).strip()
        new_desc = str(new_data.get('problem_description', '')).strip()
        existing_project = str(existing_issue.get('project_name', '')).strip()
        new_project = str(new_data.get('project_name', '')).strip()

        if existing_desc != new_desc or existing_project != new_project:
            logger.warning(f"匹配条件不一致: desc='{existing_desc}' vs '{new_desc}', project='{existing_project}' vs '{new_project}'")
            return False

        # 比较其他业务字段
        business_fields = [
            'problem_category', 'severity_level',
            'solution', 'action_priority', 'action_record', 'initiator',
            'responsible_person', 'status', 'remarks'
        ]

        # 比较时间字段（需要特殊处理）
        time_fields = ['start_time', 'target_completion_time', 'actual_completion_time']

        # 检查业务字段是否有变化
        for field in business_fields:
            existing_value = str(existing_issue.get(field, '')).strip()
            new_value = str(new_data.get(field, '')).strip()

            # 特殊处理status字段，确保映射一致
            if field == 'status':
                new_value = self.map_status(new_value)

            # 处理空值比较
            if existing_value in ['', 'None', 'null', 'NULL', '0']:
                existing_value = ''
            if new_value in ['', 'None', 'null', 'NULL', '0']:
                new_value = ''

            if existing_value != new_value:
                logger.info(f"字段 {field} 有变化: '{existing_value}' -> '{new_value}'")
                return True

        # 检查时间字段是否有变化
        for field in time_fields:
            existing_time = self.format_datetime(existing_issue.get(field, ''))
            new_time = self.format_datetime(new_data.get(field, ''))

            if existing_time != new_time:
                logger.info(f"时间字段 {field} 有变化: '{existing_time}' -> '{new_time}'")
                return True

        logger.info(f"议题 {existing_issue.get('id')} 无变化，跳过更新 (problem_description + project_name 匹配)")
        return False

    def insert_issue(self, row_data: Dict[str, Any]) -> Optional[int]:
        """插入新议题"""
        try:
            # 转换时间格式
            start_time = self.format_datetime(row_data.get('start_time', ''))
            target_time = self.format_datetime(row_data.get('target_completion_time', ''))
            actual_time = self.format_datetime(row_data.get('actual_completion_time', ''))

            # 构建SQL值
            project_name = self.escape_sql_string(row_data.get('project_name', ''))
            problem_category = self.escape_sql_string(row_data.get('problem_category', ''))
            problem_description = self.escape_sql_string(row_data.get('problem_description', ''))
            solution = self.escape_sql_string(row_data.get('solution', ''))
            action_record = self.escape_sql_string(row_data.get('action_record', ''))
            initiator = self.escape_sql_string(row_data.get('initiator', ''))
            responsible_person = self.escape_sql_string(row_data.get('responsible_person', ''))
            status = self.escape_sql_string(self.map_status(row_data.get('status', 'open')))
            remarks = self.escape_sql_string(row_data.get('remarks', ''))

            sql_query = f"""
                USE {DB_CONFIG['database']};
                INSERT INTO issues (
                    project_name, problem_category, severity_level,
                    problem_description, solution, action_priority, action_record,
                    initiator, responsible_person, status, start_time,
                    target_completion_time, actual_completion_time, remarks,
                    operation_type, sync_status
                ) VALUES (
                    '{project_name}',
                    '{problem_category}',
                    {self.safe_convert_int(row_data.get('severity_level', 0))},
                    '{problem_description}',
                    '{solution}',
                    {self.safe_convert_int(row_data.get('action_priority', 0))},
                    '{action_record}',
                    '{initiator}',
                    '{responsible_person}',
                    '{status}',
                    {f"'{start_time}'" if start_time else 'NULL'},
                    {f"'{target_time}'" if target_time else 'NULL'},
                    {f"'{actual_time}'" if actual_time else 'NULL'},
                    '{remarks}',
                    'insert',
                    'pending'
                );
                SELECT LAST_INSERT_ID();
                """
            cmd = self.build_mysql_command(sql_query)
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            # 检查执行结果
            if result.returncode != 0:
                logger.error(f"插入议题SQL执行失败: {result.stderr}")
                return None

            # 提取插入的ID
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.isdigit():
                        return int(line)

            return None
        except Exception as e:
            logger.error(f"插入议题失败: {e}")
            return None

    def update_issue(self, issue_id: int, row_data: Dict[str, Any]) -> bool:
        """更新现有议题"""
        try:
            # 转换时间格式
            start_time = self.format_datetime(row_data.get('start_time', ''))
            target_time = self.format_datetime(row_data.get('target_completion_time', ''))
            actual_time = self.format_datetime(row_data.get('actual_completion_time', ''))

            # 构建SQL值
            problem_category = self.escape_sql_string(row_data.get('problem_category', ''))
            problem_description = self.escape_sql_string(row_data.get('problem_description', ''))
            solution = self.escape_sql_string(row_data.get('solution', ''))
            action_record = self.escape_sql_string(row_data.get('action_record', ''))
            initiator = self.escape_sql_string(row_data.get('initiator', ''))
            responsible_person = self.escape_sql_string(row_data.get('responsible_person', ''))
            status = self.escape_sql_string(self.map_status(row_data.get('status', 'open')))
            remarks = self.escape_sql_string(row_data.get('remarks', ''))

            sql_query = f"""
                USE {DB_CONFIG['database']};
                UPDATE issues SET
                    problem_category = '{problem_category}',
                    severity_level = {self.safe_convert_int(row_data.get('severity_level', 0))},
                    problem_description = '{problem_description}',
                    solution = '{solution}',
                    action_priority = {self.safe_convert_int(row_data.get('action_priority', 0))},
                    action_record = '{action_record}',
                    initiator = '{initiator}',
                    responsible_person = '{responsible_person}',
                    status = '{status}',
                    start_time = {f"'{start_time}'" if start_time else 'NULL'},
                    target_completion_time = {f"'{target_time}'" if target_time else 'NULL'},
                    actual_completion_time = {f"'{actual_time}'" if actual_time else 'NULL'},
                    remarks = '{remarks}',
                    operation_type = 'update',
                    sync_status = 'pending',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = {issue_id};
                """
            cmd = self.build_mysql_command(sql_query)
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                logger.error(f"更新议题SQL执行失败: {result.stderr}")
                return False

            return True
        except Exception as e:
            logger.error(f"更新议题失败: {e}")
            return False

    def format_datetime(self, datetime_str: str) -> Optional[str]:
        """格式化时间字符串"""
        if not datetime_str or datetime_str.strip() == '':
            return None

        try:
            stripped_str = datetime_str.strip()

            # 处理非日期字符串
            non_date_strings = ['等待排期', '待定', 'TBD', 'N/A', '无', '空']
            if stripped_str in non_date_strings:
                return None

            # 使用字典映射提高格式匹配效率
            format_patterns = {
                '%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d': '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d': '%Y-%m-%d %H:%M:%S',
                '%m/%d/%Y': '%Y-%m-%d %H:%M:%S',
                '%d/%m/%Y': '%Y-%m-%d %H:%M:%S'
            }

            for input_fmt, output_fmt in format_patterns.items():
                try:
                    dt = datetime.strptime(stripped_str, input_fmt)
                    return dt.strftime(output_fmt)
                except ValueError:
                    continue

            return None
        except Exception:
            return None

    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        try:
            sql_query = f"USE {DB_CONFIG['database']}; SELECT 1;"
            cmd = self.build_mysql_command(sql_query)
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.returncode == 0
        except Exception:
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            sql_query = f"""
                USE {DB_CONFIG['database']};
                SELECT
                    COUNT(*) as total_issues,
                    COUNT(CASE WHEN sync_status = 'synced' THEN 1 END) as synced_issues,
                    COUNT(CASE WHEN sync_status = 'pending' THEN 1 END) as pending_issues,
                    COUNT(CASE WHEN sync_status = 'failed' THEN 1 END) as failed_issues,
                    COUNT(CASE WHEN operation_type = 'insert' THEN 1 END) as inserted_issues,
                    COUNT(CASE WHEN operation_type = 'update' THEN 1 END) as updated_issues
                FROM issues;
                """
            cmd = self.build_mysql_command(sql_query)
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    headers = lines[0].split('\t')
                    values = lines[1].split('\t')
                    return dict(zip(headers, values))

            return {}
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {}

    def get_issues(self) -> None:
        """获取议题列表"""
        try:
            sql_query = f"""
                USE {DB_CONFIG['database']};
                SELECT
                    id, project_name, problem_category,
                    severity_level, problem_description, status,
                    sync_status, gitlab_url, gitlab_progress,
                    created_at, updated_at
                FROM issues
                ORDER BY updated_at DESC
                LIMIT 50;
                """
            cmd = self.build_mysql_command(sql_query)
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            issues: List[Dict[str, Any]] = []
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    headers = lines[0].split('\t')
                    for line in lines[1:]:
                        values = line.split('\t')
                        issues.append(dict(zip(headers, values)))

            response: Dict[str, Any] = {
                "success": True,
                "issues": issues,
                "count": len(issues)
            }
            self.send_json_response(response)
        except Exception as e:
            logger.error(f"获取议题列表失败: {e}")
            self.send_error(500, str(e))

    def sync_to_gitlab(self) -> None:
        """同步到GitLab"""
        try:
            logger.info("开始同步数据库议题到GitLab...")
            sync_script = '/root/update_issue/gitlab_tools/enhanced_sync_database_to_gitlab.py'
            result = subprocess.run(['python3', sync_script],
                                  capture_output=True, text=True, cwd='/root/update_issue/gitlab_tools')

            if result.returncode == 0:
                response: Dict[str, Any] = {
                    "success": True,
                    "message": "GitLab同步成功",
                    "output": result.stdout
                }
            else:
                response = {
                    "success": False,
                    "message": "GitLab同步失败",
                    "error": result.stderr
                }

            self.send_json_response(response)
        except Exception as e:
            logger.error(f"GitLab同步失败: {e}")
            self.send_error(500, str(e))

    def get_gitlab_sync_status(self) -> None:
        """获取GitLab同步状态"""
        try:
            sql_query = f"""
                USE {DB_CONFIG['database']};
                SELECT
                    sync_status,
                    COUNT(*) as count,
                    COUNT(CASE WHEN gitlab_url IS NOT NULL THEN 1 END) as with_gitlab_url,
                    COUNT(CASE WHEN gitlab_progress IS NOT NULL THEN 1 END) as with_progress
                FROM issues
                GROUP BY sync_status;
                """
            cmd = self.build_mysql_command(sql_query)
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            sync_stats: List[Dict[str, Any]] = []
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    headers = lines[0].split('\t')
                    for line in lines[1:]:
                        values = line.split('\t')
                        sync_stats.append(dict(zip(headers, values)))

            response: Dict[str, Any] = {
                "success": True,
                "sync_stats": sync_stats,
                "timestamp": datetime.now().isoformat()
            }
            self.send_json_response(response)
        except Exception as e:
            logger.error(f"获取GitLab同步状态失败: {e}")
            self.send_error(500, str(e))

    def update_gitlab_progress(self) -> None:
        """更新GitLab进度"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            issue_id = data.get('issue_id')
            progress = data.get('progress')

            if not issue_id or not progress:
                self.send_error(400, "缺少issue_id或progress字段")
                return

            # 更新数据库中的GitLab进度
            sql_query = f"""
                USE {DB_CONFIG['database']};
                UPDATE issues
                SET gitlab_progress = '{progress}',
                    last_sync_time = CURRENT_TIMESTAMP
                WHERE id = {issue_id};
                """
            cmd = self.build_mysql_command(sql_query)
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if result.returncode == 0:
                response: Dict[str, Any] = {
                    "success": True,
                    "message": f"议题 #{issue_id} 进度已更新为 {progress}"
                }
            else:
                response = {
                    "success": False,
                    "message": "进度更新失败"
                }

            self.send_json_response(response)
        except Exception as e:
            logger.error(f"更新GitLab进度失败: {e}")
            self.send_error(500, str(e))

    def send_json_response(self, data: Dict[str, Any]) -> None:
        """发送JSON响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        response_json = json.dumps(data, ensure_ascii=False, indent=2)
        self.wfile.write(response_json.encode('utf-8'))

    def log_message(self, format: str, *args: Any) -> None:
        """自定义日志格式"""
        logger.info(f"{self.address_string()} - {format % args}")

def main() -> None:
    """主函数"""
    server_address = ('0.0.0.0', 80)
    httpd = HTTPServer(server_address, EnhancedWPSAPIHandler)

    logger.info("启动增强版WPS数据接收服务器...")
    logger.info(f"服务器地址: http://{server_address[0]}:{server_address[1]}")
    logger.info("功能特性: 智能数据更新、GitLab同步、进度跟踪")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("服务器停止")
        httpd.shutdown()

if __name__ == '__main__':
    main()
