#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础版WPS数据接收API服务器
使用标准库，不依赖外部包
运行在5000端口，接收WPS表格数据并同步到MySQL数据库
"""

import logging
import subprocess
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/wps_api.log'),
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

class WPSAPIHandler(BaseHTTPRequestHandler):
    """WPS API请求处理器"""

    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/':
            self.health_check()
        elif path == '/api/status':
            self.get_status()
        elif path == '/api/test':
            self.test_endpoints()
        elif path == '/api/database/tables':
            self.get_database_tables()
        elif path == '/api/database/issues':
            self.get_issues()
        elif path == '/api/debug/logs':
            self.get_debug_logs()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """处理POST请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/api/wps/upload':
            self.upload_wps_data()
        elif path == '/api/database/query':
            self.database_query()
        elif path == '/api/gitlab/sync':
            self.sync_to_gitlab()
        elif path == '/api/gitlab/status':
            self.get_gitlab_status()
        else:
            self.send_error(404, "Not Found")

    def health_check(self):
        """健康检查接口"""
        response = {
            'status': 'running',
            'service': 'WPS Data Receiver',
            'port': 80,
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        }
        self.send_json_response(response)

    def upload_wps_data(self):
        """接收WPS表格数据"""
        try:
            # 读取请求数据
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            # 详细日志记录接收到的数据
            logger.info("=" * 60)
            logger.info("接收到WPS上传请求")
            logger.info(f"请求头: {dict(self.headers)}")
            logger.info(f"数据大小: {content_length} bytes")
            logger.info(f"原始数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            logger.info("=" * 60)

            if not data or 'table_data' not in data:
                logger.error("数据格式错误，缺少table_data字段")
                self.send_error_response({'error': '数据格式错误，缺少table_data字段'}, 400)
                return

            table_data = data['table_data']
            if not isinstance(table_data, list):
                logger.error(f"table_data不是数组格式: {type(table_data)}")
                self.send_error_response({'error': 'table_data必须是数组格式'}, 400)
                return

            logger.info(f"接收到WPS数据: {len(table_data)} 条记录")

            # 验证软件分类
            software_records = []
            for index, row_data in enumerate(table_data, 1):
                logger.info(f"处理第 {index} 条记录: {json.dumps(row_data, ensure_ascii=False)}")
                problem_category = str(row_data.get('problem_category', '')).lower()
                if '软件' in problem_category:
                    software_records.append(row_data)
                    logger.info(f"✅ 第 {index} 条记录通过软件分类验证")
                else:
                    logger.warning(f"❌ 第 {index} 条记录不包含软件分类: {row_data.get('problem_category', '')}")

            if not software_records:
                logger.error("没有通过软件分类验证的记录")
                response = {
                    'error': '所有记录的问题分类都必须包含"软件"',
                    'received_records': len(table_data),
                    'valid_records': 0
                }
                self.send_error_response(response, 400)
                return

            logger.info(f"通过软件分类验证的记录: {len(software_records)} 条")

            # 插入数据库
            logger.info("开始插入数据库...")
            success_count = self.insert_to_database(software_records)
            logger.info(f"数据库插入完成，成功: {success_count} 条")

            response = {
                'success': True,
                'message': f'成功处理 {len(software_records)} 条软件相关记录',
                'total_received': len(table_data),
                'valid_records': len(software_records),
                'database_success': success_count,
                'timestamp': datetime.now().isoformat()
            }
            self.send_json_response(response)

        except Exception as e:
            logger.error(f"处理WPS数据时出错: {e}")
            self.send_error_response({'error': str(e)}, 500)

    def insert_to_database(self, records):
        """插入数据到数据库"""
        success_count = 0

        logger.info(f"准备插入 {len(records)} 条记录到数据库")

        for index, record in enumerate(records, 1):
            try:
                logger.info(f"处理第 {index} 条记录: {json.dumps(record, ensure_ascii=False)}")

                # 提取所有WPS表格字段
                serial_number = str(record.get('serial_number', '')).replace("'", "\\'")
                project_name = str(record.get('project_name', '未命名项目')).replace("'", "\\'")
                problem_category = str(record.get('problem_category', '')).replace("'", "\\'")
                severity_level = record.get('severity_level', 0)
                problem_description = str(record.get('problem_description', '')).replace("'", "\\'")
                solution = str(record.get('solution', '')).replace("'", "\\'")
                action_priority = record.get('action_priority', 0)
                action_record = str(record.get('action_record', '')).replace("'", "\\'")
                initiator = str(record.get('initiator', '')).replace("'", "\\'")
                responsible_person = str(record.get('responsible_person', '')).replace("'", "\\'")

                # 状态映射：将WPS的状态值映射到数据库ENUM值
                status_mapping = {
                    'C': 'closed',      # 已完成
                    'O': 'open',        # 开放
                    'D': 'in_progress', # 进行中
                    'P': 'open',        # P状态映射为open
                    'open': 'open',
                    'in_progress': 'in_progress',
                    'closed': 'closed',
                    'resolved': 'resolved'
                }
                raw_status = str(record.get('status', 'open'))
                status = status_mapping.get(raw_status, 'open').replace("'", "\\'")

                # 时间字段处理
                start_time = str(record.get('start_time', '')).replace("'", "\\'")
                target_completion_time = str(record.get('target_completion_time', '')).replace("'", "\\'")
                actual_completion_time = str(record.get('actual_completion_time', '')).replace("'", "\\'")
                remarks = str(record.get('remarks', '')).replace("'", "\\'")

                # 处理时间字段的SQL格式
                start_time_sql = f"'{start_time}'" if start_time else 'NULL'
                target_completion_time_sql = f"'{target_completion_time}'" if target_completion_time else 'NULL'
                actual_completion_time_sql = f"'{actual_completion_time}'" if actual_completion_time else 'NULL'

                # 使用mysql命令行工具插入完整数据
                sql = f"""
                INSERT INTO issues (
                    serial_number, project_name, problem_category, severity_level,
                    problem_description, solution, action_priority, action_record,
                    initiator, responsible_person, status, start_time,
                    target_completion_time, actual_completion_time, remarks, created_at
                ) VALUES (
                    '{serial_number}', '{project_name}', '{problem_category}', {severity_level},
                    '{problem_description}', '{solution}', {action_priority}, '{action_record}',
                    '{initiator}', '{responsible_person}', '{status}', {start_time_sql},
                    {target_completion_time_sql}, {actual_completion_time_sql}, '{remarks}', NOW()
                )
                """

                logger.info(f"执行SQL: {sql}")

                cmd = [
                    'mysql', '-u', DB_CONFIG['user'],
                    f'-p{DB_CONFIG["password"]}',
                    '-h', DB_CONFIG['host'],
                    DB_CONFIG['database'], '-e', sql
                ]

                logger.info(f"执行命令: {' '.join(cmd[:3])} -p*** {' '.join(cmd[4:])}")

                result = subprocess.run(cmd, capture_output=True, text=True)

                logger.info(f"命令返回码: {result.returncode}")
                logger.info(f"标准输出: {result.stdout}")
                logger.info(f"错误输出: {result.stderr}")

                if result.returncode == 0:
                    success_count += 1
                    logger.info(f"✅ 第 {index} 条记录插入成功")
                else:
                    logger.error(f"❌ 第 {index} 条记录插入失败: {result.stderr}")

            except Exception as e:
                logger.error(f"❌ 第 {index} 条记录插入异常: {e}")

        logger.info(f"数据库插入完成，成功: {success_count}/{len(records)} 条")
        return success_count

    def get_status(self):
        """获取服务状态"""
        try:
            # 检查数据库连接
            cmd = [
                'mysql', '-u', DB_CONFIG['user'],
                f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'],
                DB_CONFIG['database'], '-e', 'SELECT 1'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            db_status = result.returncode == 0

            response = {
                'service': 'WPS Data Receiver',
                'status': 'running',
                'database_connected': db_status,
                'timestamp': datetime.now().isoformat()
            }
            self.send_json_response(response)

        except Exception as e:
            logger.error(f"获取状态时出错: {e}")
            self.send_error_response({'error': str(e)}, 500)

    def test_endpoints(self):
        """测试所有端点"""
        try:
            # 测试数据库连接
            cmd = [
                'mysql', '-u', DB_CONFIG['user'],
                f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'],
                DB_CONFIG['database'], '-e', 'SELECT 1'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            db_status = result.returncode == 0

            response = {
                'database_test': 'success' if db_status else 'failed',
                'timestamp': datetime.now().isoformat()
            }
            self.send_json_response(response)

        except Exception as e:
            logger.error(f"测试端点时出错: {e}")
            self.send_error_response({'error': str(e)}, 500)

    def get_database_tables(self):
        """获取数据库表列表"""
        try:
            cmd = [
                'mysql', '-u', DB_CONFIG['user'],
                f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'],
                DB_CONFIG['database'], '-e', 'SHOW TABLES'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # 解析输出获取表名
                lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
                tables = [line.split('\t')[0] for line in lines if line.strip()]

                response = {
                    'success': True,
                    'tables': tables,
                    'count': len(tables)
                }
                self.send_json_response(response)
            else:
                self.send_error_response({'error': '数据库查询失败'}, 500)

        except Exception as e:
            logger.error(f"获取表列表错误: {e}")
            self.send_error_response({'error': str(e)}, 500)

    def get_issues(self):
        """获取issues表数据"""
        try:
            # 获取查询参数
            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)

            limit = int(query_params.get('limit', [50])[0])
            offset = int(query_params.get('offset', [0])[0])
            status = query_params.get('status', [None])[0]

            # 构建SQL查询
            sql = "SELECT * FROM issues"
            if status:
                sql += f" WHERE status = '{status}'"
            sql += f" ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"

            cmd = [
                'mysql', '-u', DB_CONFIG['user'],
                f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'],
                DB_CONFIG['database'], '-e', sql
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # 解析输出
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    headers = lines[0].split('\t')
                    data = []
                    for line in lines[1:]:
                        values = line.split('\t')
                        data.append(dict(zip(headers, values)))

                    response = {
                        'success': True,
                        'data': data,
                        'count': len(data),
                        'limit': limit,
                        'offset': offset
                    }
                    self.send_json_response(response)
                else:
                    self.send_json_response({'success': True, 'data': [], 'count': 0})
            else:
                self.send_error_response({'error': '数据库查询失败'}, 500)

        except Exception as e:
            logger.error(f"查询issues表错误: {e}")
            self.send_error_response({'error': str(e)}, 500)

    def database_query(self):
        """执行数据库查询（只允许SELECT）"""
        try:
            # 读取请求数据
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            if not data or 'sql' not in data:
                self.send_error_response({'error': '缺少SQL查询语句'}, 400)
                return

            sql = data['sql'].strip()

            # 安全检查：只允许SELECT查询
            if not sql.upper().startswith('SELECT'):
                self.send_error_response({'error': '只允许SELECT查询'}, 400)
                return

            cmd = [
                'mysql', '-u', DB_CONFIG['user'],
                f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'],
                DB_CONFIG['database'], '-e', sql
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # 解析输出
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    headers = lines[0].split('\t')
                    data = []
                    for line in lines[1:]:
                        values = line.split('\t')
                        data.append(dict(zip(headers, values)))

                    response = {
                        'success': True,
                        'data': data,
                        'count': len(data)
                    }
                    self.send_json_response(response)
                else:
                    self.send_json_response({'success': True, 'data': [], 'count': 0})
            else:
                self.send_error_response({'error': '数据库查询失败'}, 500)

        except Exception as e:
            logger.error(f"数据库查询错误: {e}")
            self.send_error_response({'error': str(e)}, 500)

    def get_debug_logs(self):
        """获取调试日志"""
        try:
            # 读取最近的日志文件
            log_file = '/var/log/wps_api.log'
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # 获取最后100行日志
                    recent_logs = lines[-100:] if len(lines) > 100 else lines
                    log_content = ''.join(recent_logs)
            except FileNotFoundError:
                log_content = "日志文件不存在"

            # 获取数据库中的issues记录
            cmd = [
                'mysql', '-u', DB_CONFIG['user'],
                f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'],
                DB_CONFIG['database'], '-e', 'SELECT * FROM issues ORDER BY created_at DESC LIMIT 10'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            db_records = []
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    headers = lines[0].split('\t')
                    for line in lines[1:]:
                        values = line.split('\t')
                        db_records.append(dict(zip(headers, values)))

            response = {
                'success': True,
                'log_file': log_file,
                'recent_logs': log_content,
                'database_records': db_records,
                'timestamp': datetime.now().isoformat()
            }
            self.send_json_response(response)

        except Exception as e:
            logger.error(f"获取调试日志错误: {e}")
            self.send_error_response({'error': str(e)}, 500)

    def send_json_response(self, data, status_code=200):
        """发送JSON响应"""
        response_data = json.dumps(data, ensure_ascii=False, indent=2)

        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_data.encode('utf-8'))))
        self.end_headers()

        self.wfile.write(response_data.encode('utf-8'))

    def send_error_response(self, data, status_code):
        """发送错误响应"""
        self.send_json_response(data, status_code)

    def log_message(self, format, *args):
        """重写日志方法"""
        logger.info(f"{self.address_string()} - {format % args}")

    def sync_to_gitlab(self):
        """同步数据库议题到GitLab"""
        try:
            logger.info("开始同步数据库议题到GitLab...")

            # 运行GitLab同步脚本
            sync_script = '/root/update_issue/gitlab_tools/sync_database_to_gitlab.py'
            result = subprocess.run(['python3', sync_script],
                                  capture_output=True, text=True, cwd='/root/update_issue/gitlab_tools')

            if result.returncode == 0:
                logger.info("GitLab同步成功")
                response = {
                    'success': True,
                    'message': '数据库议题已成功同步到GitLab',
                    'output': result.stdout,
                    'timestamp': datetime.now().isoformat()
                }
                self.send_json_response(response, 200)
            else:
                logger.error(f"GitLab同步失败: {result.stderr}")
                response = {
                    'success': False,
                    'message': 'GitLab同步失败',
                    'error': result.stderr,
                    'timestamp': datetime.now().isoformat()
                }
                self.send_json_response(response, 500)

        except Exception as e:
            logger.error(f"GitLab同步异常: {e}")
            response = {
                'success': False,
                'message': 'GitLab同步异常',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.send_json_response(response, 500)

    def get_gitlab_status(self):
        """获取GitLab同步状态"""
        try:
            # 查询数据库中的GitLab同步状态
            cmd = [
                'mysql', '-u', DB_CONFIG['user'], f'-p{DB_CONFIG["password"]}',
                '-h', DB_CONFIG['host'], '-P', str(DB_CONFIG['port']),
                '-e', f"USE {DB_CONFIG['database']}; SELECT COUNT(*) as total, COUNT(gitlab_url) as synced, sync_status FROM issues GROUP BY sync_status;"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # 解析结果
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                headers = lines[0].split('\t')
                stats = []
                for line in lines[1:]:
                    if line.strip():
                        values = line.split('\t')
                        stats.append(dict(zip(headers, values)))

                response = {
                    'success': True,
                    'gitlab_sync_status': stats,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                response = {
                    'success': True,
                    'message': '无法获取GitLab同步状态',
                    'timestamp': datetime.now().isoformat()
                }

            self.send_json_response(response, 200)

        except Exception as e:
            logger.error(f"获取GitLab状态异常: {e}")
            response = {
                'success': False,
                'message': '获取GitLab状态异常',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.send_json_response(response, 500)

def run_server():
    """运行服务器"""
    server_address = ('0.0.0.0', 80)
    httpd = HTTPServer(server_address, WPSAPIHandler)

    logger.info("启动WPS数据接收服务器...")
    logger.info(f"服务器地址: http://0.0.0.0:80")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("服务器停止")
        httpd.shutdown()

if __name__ == '__main__':
    run_server()
