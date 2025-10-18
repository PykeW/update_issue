#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WPS数据上传API服务
接收WPS表格数据并保存到数据库
"""

import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from gitlab_tools.core.database_manager import DatabaseManager
from gitlab_tools.core.config_manager import ConfigManager

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 初始化组件
db_manager = DatabaseManager()
config_manager = ConfigManager()

def clean_string_value(value):
    """清理字符串值"""
    if value is None:
        return ''
    return str(value).strip()

def check_duplicate_record(project_name, problem_description):
    """检查是否存在重复记录"""
    try:
        if not problem_description or not project_name:
            return None

        # 查询是否存在相同的项目名和问题描述
        query = """
        SELECT id, project_name, problem_description, created_at
        FROM issues
        WHERE project_name = %s AND problem_description = %s
        ORDER BY created_at ASC
        LIMIT 1
        """

        # 转义单引号
        escaped_project_name = project_name.replace("'", "''")
        escaped_problem_description = problem_description.replace("'", "''")

        formatted_query = query.replace('%s', f"'{escaped_project_name}'", 1).replace('%s', f"'{escaped_problem_description}'", 1)
        result = db_manager.execute_query(formatted_query)

        if result:
            return result[0]  # 返回找到的重复记录
        return None

    except Exception as e:
        print(f"❌ 检查重复记录时发生错误: {str(e)}")
        return None

def insert_issue_record(record):
    """插入议题记录到数据库"""
    try:
        print(f"🔍 开始插入记录: {record.get('project_name', '未知项目')}")

        # 准备数据
        project_name = clean_string_value(record.get('project_name', ''))
        problem_category = clean_string_value(record.get('problem_category', ''))
        severity_level = clean_string_value(record.get('severity_level', '0'))
        problem_description = clean_string_value(record.get('problem_description', ''))
        solution = clean_string_value(record.get('solution', ''))
        action_priority = clean_string_value(record.get('action_priority', '0'))
        action_record = clean_string_value(record.get('action_record', ''))
        initiator = clean_string_value(record.get('initiator', ''))
        responsible_person = clean_string_value(record.get('responsible_person', ''))
        # 状态映射：WPS状态 -> 数据库状态
        wps_status = clean_string_value(record.get('status', 'open'))
        status_mapping = {
            'O': 'open',           # Open
            'C': 'closed',        # Closed
            'P': 'in_progress',   # In Progress
            'R': 'resolved'       # Resolved
        }
        status = status_mapping.get(wps_status.upper(), 'open')
        start_time = clean_string_value(record.get('start_time', ''))
        target_completion_time = clean_string_value(record.get('target_completion_time', ''))
        actual_completion_time = clean_string_value(record.get('actual_completion_time', ''))
        remarks = clean_string_value(record.get('remarks', ''))

        print(f"📋 数据准备完成: 项目={project_name}, 分类={problem_category}, 严重程度={severity_level}")

        # 检查重复记录
        duplicate_record = check_duplicate_record(project_name, problem_description)
        if duplicate_record:
            print(f"⚠️ 发现重复记录: 项目={project_name}, 问题描述={problem_description[:50]}...")
            print(f"📋 已存在记录ID: {duplicate_record['id']}, 创建时间: {duplicate_record['created_at']}")
            return False, f"重复记录，已存在记录ID: {duplicate_record['id']}"

        # 处理数值字段
        try:
            severity_level_int = int(float(severity_level)) if severity_level else 0
        except:
            severity_level_int = 0

        try:
            action_priority_int = int(float(action_priority)) if action_priority else 0
        except:
            action_priority_int = 0

        print(f"🔢 数值转换: 严重程度={severity_level_int}, 优先级={action_priority_int}")

        # 处理时间字段 - 只处理有效的时间格式
        def is_valid_datetime(value):
            if not value or value.strip() == '':
                return False
            # 检查是否是有效的时间格式 (YYYY-MM-DD HH:MM:SS)
            try:
                from datetime import datetime
                datetime.strptime(value.strip(), '%Y-%m-%d %H:%M:%S')
                return True
            except:
                return False

        start_time_sql = f"'{start_time}'" if is_valid_datetime(start_time) else 'NULL'
        target_completion_time_sql = f"'{target_completion_time}'" if is_valid_datetime(target_completion_time) else 'NULL'
        actual_completion_time_sql = f"'{actual_completion_time}'" if is_valid_datetime(actual_completion_time) else 'NULL'

        # 转义单引号
        def escape_sql_string(value):
            return value.replace("'", "''")

        # 构建插入SQL
        insert_sql = f"""
        INSERT INTO issues (
            project_name, problem_category, severity_level, problem_description,
            solution, action_priority, action_record, initiator, responsible_person,
            status, start_time, target_completion_time, actual_completion_time,
            remarks
        ) VALUES (
            '{escape_sql_string(project_name)}',
            '{escape_sql_string(problem_category)}',
            {severity_level_int},
            '{escape_sql_string(problem_description)}',
            '{escape_sql_string(solution)}',
            {action_priority_int},
            '{escape_sql_string(action_record)}',
            '{escape_sql_string(initiator)}',
            '{escape_sql_string(responsible_person)}',
            '{status}',
            {start_time_sql},
            {target_completion_time_sql},
            {actual_completion_time_sql},
            '{escape_sql_string(remarks)}'
        )
        """

        print(f"📝 SQL准备完成，长度: {len(insert_sql)} 字符")

        # 执行插入
        print(f"🚀 开始执行数据库插入...")
        try:
            result = db_manager.execute_update(insert_sql)
            print(f"📊 数据库插入结果: {result}")

            if result:
                print(f"✅ 插入成功: {project_name}")
                return True, "插入成功"
            else:
                print(f"❌ 插入失败: {project_name}")
                return False, "插入失败"
        except Exception as db_error:
            print(f"❌ 数据库插入异常: {str(db_error)}")
            return False, f"插入失败: {str(db_error)}"

    except Exception as e:
        print(f"❌ 插入异常: {str(e)}")
        return False, f"插入失败: {str(e)}"

@app.route('/', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'success': True,
        'message': 'WPS上传API服务正常运行',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/wps/upload', methods=['POST'])
def upload_wps_data():
    """接收WPS表格数据"""
    try:
        # 获取请求数据
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据为空'
            }), 400

        # 提取表格数据
        table_data = data.get('table_data', [])
        client_info = data.get('client_info', {})

        if not table_data:
            return jsonify({
                'success': False,
                'error': '表格数据为空'
            }), 400

        print(f"📤 接收到WPS数据: {len(table_data)} 条记录")
        print(f"📋 客户端信息: {client_info}")

        # 处理每条记录
        success_count = 0
        skipped_count = 0  # 新增：跳过计数（重复记录）
        failed_count = 0
        errors = []
        skipped_info = []  # 新增：跳过记录信息

        print(f"🔄 开始处理 {len(table_data)} 条记录...")

        for i, record in enumerate(table_data):
            try:
                print(f"📝 处理记录 {i+1}/{len(table_data)}: {record.get('project_name', '未知项目')}")

                # 验证必填字段
                if not record.get('project_name'):
                    error_msg = f"记录 {i+1}: 项目名称不能为空"
                    print(f"❌ {error_msg}")
                    errors.append(error_msg)
                    failed_count += 1
                    continue

                # 插入数据库
                print(f"🚀 开始插入记录 {i+1}...")
                success, message = insert_issue_record(record)
                print(f"📊 记录 {i+1} 插入结果: success={success}, message={message}")

                if success:
                    success_count += 1
                    print(f"✅ 记录 {i+1} 处理成功")
                else:
                    # 检查是否为重复记录
                    if '重复记录' in message or '已存在记录' in message:
                        skipped_count += 1
                        skip_msg = f"记录 {i+1}: {message}"
                        print(f"⏭️  {skip_msg}")
                        skipped_info.append(skip_msg)
                    else:
                        error_msg = f"记录 {i+1}: {message}"
                        print(f"❌ {error_msg}")
                        errors.append(error_msg)
                        failed_count += 1

            except Exception as e:
                error_msg = f"记录 {i+1}: 处理异常 - {str(e)}"
                print(f"❌ {error_msg}")
                errors.append(error_msg)
                failed_count += 1

        print(f"📊 处理完成: 成功 {success_count} 条, 跳过 {skipped_count} 条, 失败 {failed_count} 条")

        # 返回结果
        result = {
            'success': success_count > 0 or skipped_count > 0,  # 修改：有新增或跳过都算成功
            'message': f'处理完成: 成功 {success_count} 条, 跳过 {skipped_count} 条, 失败 {failed_count} 条',
            'statistics': {
                'total': len(table_data),
                'success': success_count,
                'skipped': skipped_count,  # 新增：跳过计数
                'failed': failed_count
            },
            'errors': errors[:10] if errors else [],  # 只返回前10个真正的错误
            'skipped': skipped_info[:5] if skipped_info else [],  # 新增：返回前5个跳过记录
            'timestamp': datetime.now().isoformat()
        }

        print(f"✅ 处理结果: {result['message']}")

        return jsonify(result)

    except Exception as e:
        error_msg = f"服务器处理异常: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/database/status', methods=['GET'])
def get_database_status():
    """获取数据库状态"""
    try:
        # 查询数据库统计
        stats_query = """
        SELECT
            COUNT(*) as total_issues,
            SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_issues,
            SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_issues,
            SUM(CASE WHEN gitlab_url IS NOT NULL AND gitlab_url != '' THEN 1 ELSE 0 END) as synced_issues
        FROM issues
        """

        result = db_manager.execute_query(stats_query)

        if result:
            stats = result[0]
            return jsonify({
                'success': True,
                'data': {
                    'total_issues': stats.get('total_issues', 0),
                    'open_issues': stats.get('open_issues', 0),
                    'closed_issues': stats.get('closed_issues', 0),
                    'synced_issues': stats.get('synced_issues', 0)
                },
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': '无法获取数据库统计'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取状态失败: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("🚀 启动WPS数据上传API服务...")
    print("📡 服务地址: http://114.55.118.105:80")
    print("📋 API端点:")
    print("  - GET  /                   健康检查")
    print("  - POST /api/wps/upload     WPS数据上传")
    print("  - GET  /api/database/status 数据库状态")
    print("=" * 50)

    app.run(host='0.0.0.0', port=80, debug=False)
