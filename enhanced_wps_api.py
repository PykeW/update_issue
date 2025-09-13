#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版WPS数据接收API服务器
支持智能数据更新、GitLab同步和进度跟踪
"""

import logging
import subprocess
import json
import hashlib
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

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
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'issue',
    'password': 'hszc8888',
    'database': 'issue_database'
}

class EnhancedWPSAPIHandler(BaseHTTPRequestHandler):
    """增强版WPS API请求处理器"""

    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/':
            self.health_check()
        elif path == '/api/status':
            self.get_status()
        elif path == '/api/database/issues':
            self.get_issues()
        elif path == '/api/gitlab/sync-status':
            self.get_gitlab_sync_status()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """处理POST请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/api/wps/upload':
            self.upload_wps_data()
        elif path == '/api/gitlab/sync':
            self.sync_to_gitlab()
        elif path == '/api/gitlab/update-progress':
            self.update_gitlab_progress()
        else:
            self.send_error(404, "Not Found")

    def health_check(self):
        """健康检查"""
        response = {
            "status": "running",
            "service": "Enhanced WPS Data Receiver",
            "port": 5000,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "features": [
                "智能数据更新",
                "GitLab同步",
                "进度跟踪"
            ]
        }
        self.send_json_response(response)

    def get_status(self):
        """获取服务状态"""
        try:
            # 检查数据库连接
            db_status = self.check_database_connection()

            # 获取数据库统计信息
            stats = self.get_database_stats()

            response = {
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

    def upload_wps_data(self):
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

            response = {
                "success": True,
                "message": f"成功处理 {len(table_data)} 条记录",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            self.send_json_response(response)

        except Exception as e:
            logger.error(f"处理WPS数据失败: {e}")
            self.send_error(500, str(e))

    def process_wps_data(self, table_data):
        """处理WPS数据，支持智能更新"""
        results = {
            "inserted": 0,
            "updated": 0,
            "failed": 0,
            "details": []
        }

        for row_data in table_data:
            try:
                # 生成数据哈希值
                data_hash = self.generate_data_hash(row_data)

                # 检查是否已存在
                existing_issue = self.find_existing_issue(
                    row_data.get('serial_number', ''),
                    row_data.get('project_name', '')
                )

                if existing_issue:
                    # 更新现有记录
                    if self.should_update_issue(existing_issue, row_data, data_hash):
                        update_result = self.update_issue(existing_issue['id'], row_data, data_hash)
                        if update_result:
                            results["updated"] += 1
                            results["details"].append({
                                "serial_number": row_data.get('serial_number', ''),
                                "project_name": row_data.get('project_name', ''),
                                "action": "updated",
                                "issue_id": existing_issue['id']
                            })
                        else:
                            results["failed"] += 1
                    else:
                        results["details"].append({
                            "serial_number": row_data.get('serial_number', ''),
                            "project_name": row_data.get('project_name', ''),
                            "action": "no_change",
                            "issue_id": existing_issue['id']
                        })
                else:
                    # 插入新记录
                    insert_result = self.insert_issue(row_data, data_hash)
                    if insert_result:
                        results["inserted"] += 1
                        results["details"].append({
                            "serial_number": row_data.get('serial_number', ''),
                            "project_name": row_data.get('project_name', ''),
                            "action": "inserted",
                            "issue_id": insert_result
                        })
                    else:
                        results["failed"] += 1

            except Exception as e:
                logger.error(f"处理单条记录失败: {e}")
                results["failed"] += 1
                results["details"].append({
                    "serial_number": row_data.get('serial_number', ''),
                    "project_name": row_data.get('project_name', ''),
                    "action": "failed",
                    "error": str(e)
                })

        return results

    def generate_data_hash(self, row_data):
        """生成数据哈希值"""
        # 排除时间戳字段，只对业务数据进行哈希
        hash_fields = [
            'serial_number', 'project_name', 'problem_category',
            'severity_level', 'problem_description', 'solution',
            'action_priority', 'action_record', 'initiator',
            'responsible_person', 'status', 'remarks'
        ]

        hash_string = ""
        for field in hash_fields:
            value = str(row_data.get(field, ''))
            hash_string += f"{field}:{value}|"

        return hashlib.md5(hash_string.encode('utf-8')).hexdigest()

    def find_existing_issue(self, serial_number, project_name):
        """查找现有议题"""
        try:
            cmd = [
                'mysql', '-u', DB_CONFIG['user'], f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'], '-P', str(DB_CONFIG['port']),
                '-e', f"""
                USE {DB_CONFIG['database']};
                SELECT * FROM issues
                WHERE serial_number = '{serial_number}'
                AND project_name = '{project_name}'
                LIMIT 1;
                """
            ]
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

    def should_update_issue(self, existing_issue, new_data, new_hash):
        """判断是否需要更新议题"""
        # 比较数据哈希值
        if existing_issue.get('data_hash') == new_hash:
            return False

        # 比较关键字段
        key_fields = ['problem_description', 'solution', 'status', 'responsible_person']
        for field in key_fields:
            if str(existing_issue.get(field, '')) != str(new_data.get(field, '')):
                return True

        return False

    def insert_issue(self, row_data, data_hash):
        """插入新议题"""
        try:
            # 转换时间格式
            start_time = self.format_datetime(row_data.get('start_time', ''))
            target_time = self.format_datetime(row_data.get('target_completion_time', ''))
            actual_time = self.format_datetime(row_data.get('actual_completion_time', ''))

            cmd = [
                'mysql', '-u', DB_CONFIG['user'], f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'], '-P', str(DB_CONFIG['port']),
                '-e', f"""
                USE {DB_CONFIG['database']};
                INSERT INTO issues (
                    serial_number, project_name, problem_category, severity_level,
                    problem_description, solution, action_priority, action_record,
                    initiator, responsible_person, status, start_time,
                    target_completion_time, actual_completion_time, remarks,
                    operation_type, data_hash, sync_status
                ) VALUES (
                    '{row_data.get('serial_number', '')}',
                    '{row_data.get('project_name', '')}',
                    '{row_data.get('problem_category', '')}',
                    {int(row_data.get('severity_level', 0))},
                    '{row_data.get('problem_description', '').replace("'", "\\'")}',
                    '{row_data.get('solution', '').replace("'", "\\'")}',
                    {int(row_data.get('action_priority', 0))},
                    '{row_data.get('action_record', '').replace("'", "\\'")}',
                    '{row_data.get('initiator', '')}',
                    '{row_data.get('responsible_person', '')}',
                    '{row_data.get('status', 'open')}',
                    {f"'{start_time}'" if start_time else 'NULL'},
                    {f"'{target_time}'" if target_time else 'NULL'},
                    {f"'{actual_time}'" if actual_time else 'NULL'},
                    '{row_data.get('remarks', '').replace("'", "\\'")}',
                    'insert',
                    '{data_hash}',
                    'pending'
                );
                SELECT LAST_INSERT_ID();
                """
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

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

    def update_issue(self, issue_id, row_data, data_hash):
        """更新现有议题"""
        try:
            # 转换时间格式
            start_time = self.format_datetime(row_data.get('start_time', ''))
            target_time = self.format_datetime(row_data.get('target_completion_time', ''))
            actual_time = self.format_datetime(row_data.get('actual_completion_time', ''))

            cmd = [
                'mysql', '-u', DB_CONFIG['user'], f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'], '-P', str(DB_CONFIG['port']),
                '-e', f"""
                USE {DB_CONFIG['database']};
                UPDATE issues SET
                    problem_category = '{row_data.get('problem_category', '')}',
                    severity_level = {int(row_data.get('severity_level', 0))},
                    problem_description = '{row_data.get('problem_description', '').replace("'", "\\'")}',
                    solution = '{row_data.get('solution', '').replace("'", "\\'")}',
                    action_priority = {int(row_data.get('action_priority', 0))},
                    action_record = '{row_data.get('action_record', '').replace("'", "\\'")}',
                    initiator = '{row_data.get('initiator', '')}',
                    responsible_person = '{row_data.get('responsible_person', '')}',
                    status = '{row_data.get('status', 'open')}',
                    start_time = {f"'{start_time}'" if start_time else 'NULL'},
                    target_completion_time = {f"'{target_time}'" if target_time else 'NULL'},
                    actual_completion_time = {f"'{actual_time}'" if actual_time else 'NULL'},
                    remarks = '{row_data.get('remarks', '').replace("'", "\\'")}',
                    operation_type = 'update',
                    data_hash = '{data_hash}',
                    sync_status = 'pending',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = {issue_id};
                """
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"更新议题失败: {e}")
            return False

    def format_datetime(self, datetime_str):
        """格式化时间字符串"""
        if not datetime_str or datetime_str.strip() == '':
            return None

        try:
            # 尝试多种时间格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%m/%d/%Y',
                '%d/%m/%Y'
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(datetime_str.strip(), fmt)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue

            return None
        except Exception:
            return None

    def check_database_connection(self):
        """检查数据库连接"""
        try:
            cmd = [
                'mysql', '-u', DB_CONFIG['user'], f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'], '-P', str(DB_CONFIG['port']),
                '-e', f"USE {DB_CONFIG['database']}; SELECT 1;"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.returncode == 0
        except Exception:
            return False

    def get_database_stats(self):
        """获取数据库统计信息"""
        try:
            cmd = [
                'mysql', '-u', DB_CONFIG['user'], f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'], '-P', str(DB_CONFIG['port']),
                '-e', f"""
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
            ]
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

    def get_issues(self):
        """获取议题列表"""
        try:
            cmd = [
                'mysql', '-u', DB_CONFIG['user'], f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'], '-P', str(DB_CONFIG['port']),
                '-e', f"""
                USE {DB_CONFIG['database']};
                SELECT
                    id, serial_number, project_name, problem_category,
                    severity_level, problem_description, status,
                    sync_status, gitlab_url, gitlab_progress,
                    created_at, updated_at
                FROM issues
                ORDER BY updated_at DESC
                LIMIT 50;
                """
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            issues = []
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    headers = lines[0].split('\t')
                    for line in lines[1:]:
                        values = line.split('\t')
                        issues.append(dict(zip(headers, values)))

            response = {
                "success": True,
                "issues": issues,
                "count": len(issues)
            }
            self.send_json_response(response)
        except Exception as e:
            logger.error(f"获取议题列表失败: {e}")
            self.send_error(500, str(e))

    def sync_to_gitlab(self):
        """同步到GitLab"""
        try:
            logger.info("开始同步数据库议题到GitLab...")
            sync_script = '/root/update_issue/gitlab_tools/enhanced_sync_database_to_gitlab.py'
            result = subprocess.run(['python3', sync_script],
                                  capture_output=True, text=True, cwd='/root/update_issue/gitlab_tools')

            if result.returncode == 0:
                response = {
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

    def get_gitlab_sync_status(self):
        """获取GitLab同步状态"""
        try:
            cmd = [
                'mysql', '-u', DB_CONFIG['user'], f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'], '-P', str(DB_CONFIG['port']),
                '-e', f"""
                USE {DB_CONFIG['database']};
                SELECT
                    sync_status,
                    COUNT(*) as count,
                    COUNT(CASE WHEN gitlab_url IS NOT NULL THEN 1 END) as with_gitlab_url,
                    COUNT(CASE WHEN gitlab_progress IS NOT NULL THEN 1 END) as with_progress
                FROM issues
                GROUP BY sync_status;
                """
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            sync_stats = []
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    headers = lines[0].split('\t')
                    for line in lines[1:]:
                        values = line.split('\t')
                        sync_stats.append(dict(zip(headers, values)))

            response = {
                "success": True,
                "sync_stats": sync_stats,
                "timestamp": datetime.now().isoformat()
            }
            self.send_json_response(response)
        except Exception as e:
            logger.error(f"获取GitLab同步状态失败: {e}")
            self.send_error(500, str(e))

    def update_gitlab_progress(self):
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
            cmd = [
                'mysql', '-u', DB_CONFIG['user'], f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'], '-P', str(DB_CONFIG['port']),
                '-e', f"""
                USE {DB_CONFIG['database']};
                UPDATE issues
                SET gitlab_progress = '{progress}',
                    last_sync_time = CURRENT_TIMESTAMP
                WHERE id = {issue_id};
                """
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if result.returncode == 0:
                response = {
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

    def send_json_response(self, data):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        response_json = json.dumps(data, ensure_ascii=False, indent=2)
        self.wfile.write(response_json.encode('utf-8'))

    def log_message(self, format, *args):
        """自定义日志格式"""
        logger.info(f"{self.address_string()} - {format % args}")

def main():
    """主函数"""
    server_address = ('0.0.0.0', 5000)
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
