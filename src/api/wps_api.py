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

from src.gitlab.core.database_manager import DatabaseManager
from src.gitlab.core.config_manager import ConfigManager
from src.gitlab.services.manual_sync import (
    process_pending_sync_queue as service_process_pending_sync_queue,
)

from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Any, Dict

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

def get_issue_by_id(issue_id):
    """从数据库获取议题详细信息"""
    try:
        query = f"SELECT * FROM issues WHERE id = {issue_id}"
        result = db_manager.execute_query(query)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ 获取议题详细信息失败: {str(e)}")
        return None

def sync_issue_to_gitlab(issue_id, action='create'):
    """立即同步议题到 GitLab"""
    try:
        print(f"🔗 开始同步议题到 GitLab: ID={issue_id}, 操作={action}")

        # 获取议题详细信息
        issue_data = get_issue_by_id(issue_id)
        if not issue_data:
            return {'success': False, 'error': '议题不存在'}

        # 初始化 GitLab 操作
        from src.gitlab.core.gitlab_operations import GitLabOperations

        gitlab_ops = GitLabOperations()

        # 加载配置
        gitlab_config = config_manager.load_gitlab_config()
        full_config = config_manager.load_full_config()
        user_mapping_config = config_manager.load_user_mapping()
        user_mapping = user_mapping_config.get('user_mapping', {}) if user_mapping_config else {}

        if not gitlab_config:
            return {'success': False, 'error': 'GitLab配置加载失败'}
        # 明确收窄类型（认证在 GitLabOperations 内部完成；full_config 携带标签映射等业务配置）
        cfg = {
            'gitlab_url': gitlab_config['gitlab_url'],
            'private_token': gitlab_config['private_token'],
            'project_id': gitlab_config['project_id'],
            'project_path': gitlab_config.get('project_path', '')
        }

        if action == 'create':
            # 创建新议题
            print(f"📝 创建 GitLab 议题: {issue_data.get('project_name')}")
            # 传入 full_config 以便创建时使用 labels/mapping 等业务配置
            # 明确保证传入 Dict[str, Any]，避免 Optional 导致的类型不兼容
            effective_config: Dict[str, Any] = full_config or cfg
            create_result = gitlab_ops.create_issue(issue_data, effective_config, user_mapping)

            if create_result and create_result.get('success'):
                gitlab_url = create_result.get('url', '')
                # 更新数据库中的 gitlab_url
                update_sql = f"""
                UPDATE issues
                SET gitlab_url = '{gitlab_url}', sync_status = 'synced', last_sync_time = NOW()
                WHERE id = {issue_id}
                """
                db_manager.execute_update(update_sql)
                print(f"✅ GitLab 议题创建成功: {gitlab_url}")
                return {'success': True, 'gitlab_url': gitlab_url}
            else:
                error_msg = create_result.get('error', '创建失败') if create_result else '创建失败'
                print(f"❌ GitLab 议题创建失败: {error_msg}")
                return {'success': False, 'error': error_msg}

        elif action == 'close':
            # 关闭议题并移除标签
            gitlab_url = issue_data.get('gitlab_url', '')
            if gitlab_url and gitlab_url.upper() != 'NULL':
                print(f"🔒 关闭 GitLab 议题: {gitlab_url}")
                issue_iid = gitlab_ops.extract_issue_id_from_url(gitlab_url)
                if issue_iid:
                    close_ok = gitlab_ops.close_issue(issue_iid, issue_data)
                    if close_ok:
                        # 更新同步状态
                        update_sql = f"""
                        UPDATE issues
                        SET sync_status = 'synced', last_sync_time = NOW()
                        WHERE id = {issue_id}
                        """
                        db_manager.execute_update(update_sql)
                        print(f"✅ GitLab 议题关闭成功")
                        return {'success': True}
                    else:
                        return {'success': False, 'error': '关闭失败'}
                else:
                    return {'success': False, 'error': '无法提取议题ID'}
            else:
                return {'success': False, 'error': '没有有效的GitLab URL'}

        return {'success': False, 'error': '未知操作'}

    except Exception as e:
        error_msg = str(e)
        print(f"❌ GitLab 同步异常: {error_msg}")
        return {'success': False, 'error': error_msg}

def check_duplicate_record(project_name, problem_description):
    """检查是否存在重复记录"""
    try:
        if not problem_description or not project_name:
            return None

        # 查询是否存在相同的项目名和问题描述，包含 status 和 gitlab_url
        query = """
        SELECT id, project_name, problem_description, status, gitlab_url, created_at
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

def update_issue_status(issue_id, new_status, record, gitlab_url=None):
    """更新已存在记录的状态并同步到GitLab"""
    try:
        print(f"🔄 更新议题状态: ID={issue_id}, 新状态={new_status}")

        # 准备更新的字段
        actual_completion_time = clean_string_value(record.get('actual_completion_time', ''))

        # 处理时间字段
        def is_valid_datetime(value):
            if not value or value.strip() == '':
                return False
            try:
                from datetime import datetime
                datetime.strptime(value.strip(), '%Y-%m-%d %H:%M:%S')
                return True
            except:
                return False

        actual_time_sql = f"'{actual_completion_time}'" if is_valid_datetime(actual_completion_time) else 'NOW()'

        # 构建更新SQL
        update_sql = f"""
        UPDATE issues
        SET
            status = '{new_status}',
            actual_completion_time = {actual_time_sql},
            sync_status = 'pending',
            updated_at = NOW()
        WHERE id = {issue_id}
        """

        print(f"📝 执行状态更新SQL: {update_sql}")

        # 执行更新
        result = db_manager.execute_update(update_sql)

        if result:
            print(f"✅ 议题状态更新成功: ID={issue_id}, 状态={new_status}")

            # 如果状态为 closed，立即同步到 GitLab
            if new_status == 'closed':
                print(f"🔗 状态已关闭，立即同步到 GitLab")

                # 检查是否已有 GitLab URL（排除 NULL 和空字符串）
                if gitlab_url and gitlab_url.strip() and gitlab_url.strip().upper() != 'NULL':
                    print(f"✅ 检测到现有 GitLab URL: {gitlab_url}")
                    # 已有议题，立即关闭
                    gitlab_result = sync_issue_to_gitlab(issue_id, action='close')
                    if gitlab_result.get('success'):
                        print(f"✅ GitLab 议题已关闭")
                        return True, "状态更新成功并已关闭GitLab议题"
                    else:
                        error_msg = gitlab_result.get('error', '未知错误')
                        print(f"⚠️ GitLab 议题关闭失败: {error_msg}，添加到同步队列")
                        # 失败时添加到队列
                        queue_sql = f"""
                        INSERT INTO sync_queue (issue_id, action, priority, metadata, status)
                        VALUES (
                            {issue_id},
                            'close',
                            3,
                            '{{"remove_labels": ["进度::done"], "error": "{error_msg}"}}',
                            'pending'
                        )
                        """
                        try:
                            db_manager.execute_update(queue_sql)
                            print(f"✅ 已添加到同步队列，稍后重试")
                        except Exception as queue_error:
                            print(f"❌ 添加同步队列失败: {str(queue_error)}")
                else:
                    # 新规则：无 GitLab URL 且状态为 closed 不创建议题
                    print("⏭️ 跳过创建议题：无 GitLab URL 且状态为 closed（按新规则不创建）")

            return True, "状态更新成功"
        else:
            print(f"❌ 议题状态更新失败: ID={issue_id}")
            return False, "状态更新失败"

    except Exception as e:
        print(f"❌ 更新议题状态异常: {str(e)}")
        return False, f"状态更新失败: {str(e)}"

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
            print(f"📋 已存在记录ID: {duplicate_record['id']}, 当前状态: {duplicate_record.get('status', 'unknown')}")

            old_status = duplicate_record.get('status', '')
            issue_id = duplicate_record['id']
            gitlab_url = duplicate_record.get('gitlab_url', '')

            if old_status != status:
                # 状态有变化，执行更新
                print(f"🔄 状态变化检测: {old_status} → {status}")
                success, message = update_issue_status(issue_id, status, record, gitlab_url)
                if success:
                    return True, f"状态已更新: {old_status} → {status}"
                else:
                    return False, f"状态更新失败: {message}"
            else:
                # 状态无变化，跳过
                print(f"⏭️ 状态无变化，跳过记录: {issue_id}")
                return False, f"重复记录，状态未变化: {issue_id}"

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

                # 获取刚插入的记录 ID
                get_id_sql = f"""
                SELECT id, created_at FROM issues
                WHERE project_name = '{escape_sql_string(project_name)}'
                AND problem_description = '{escape_sql_string(problem_description)}'
                ORDER BY created_at DESC LIMIT 1
                """
                id_result = db_manager.execute_query(get_id_sql)

                if id_result and id_result[0].get('id'):
                    new_issue_id = id_result[0].get('id')
                    created_at = id_result[0].get('created_at')

                    # 新规则：不做时间过滤；仅非 closed 状态尝试创建
                    from datetime import datetime as dt
                    if isinstance(created_at, str):
                        try:
                            created_at = dt.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                        except Exception:
                            created_at = None

                    if status != 'closed':
                        print("🆕 新记录（非closed），立即尝试同步到GitLab")
                        gitlab_result = sync_issue_to_gitlab(new_issue_id, action='create')

                        if gitlab_result.get('success'):
                            print(f"✅ GitLab 议题已创建: {gitlab_result.get('gitlab_url')}")
                            return True, f"插入成功并已同步到GitLab: {gitlab_result.get('gitlab_url')}"
                        else:
                            error_msg = gitlab_result.get('error', '未知错误')
                            print(f"⚠️ GitLab 同步失败: {error_msg}，添加到同步队列")
                            queue_sql = f"""
                            INSERT INTO sync_queue (issue_id, action, priority, metadata, status)
                            VALUES (
                                {new_issue_id},
                                'create',
                                3,
                                '{{"error": "{error_msg}"}}',
                                'pending'
                            )
                            """
                            try:
                                db_manager.execute_update(queue_sql)
                                print(f"✅ 已添加到同步队列，稍后重试")
                            except Exception as queue_error:
                                print(f"❌ 添加同步队列失败: {str(queue_error)}")

                            return True, "插入成功但GitLab同步失败，已添加到队列"
                    else:
                        print("⏭️ 新记录为closed状态，按新规则不创建GitLab议题")
                else:
                    print(f"⚠️ 无法获取新插入记录的 ID")

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
        updated_count = 0  # 新增：更新计数（状态变化）
        skipped_count = 0  # 跳过计数（重复记录）
        failed_count = 0
        errors = []
        skipped_info = []  # 跳过记录信息
        updated_info = []  # 新增：更新记录信息

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
                    # 检查是否为状态更新
                    if '状态已更新' in message:
                        updated_count += 1
                        update_msg = f"记录 {i+1}: {message}"
                        print(f"🔄 {update_msg}")
                        updated_info.append(update_msg)
                    else:
                        success_count += 1
                        print(f"✅ 记录 {i+1} 处理成功")
                else:
                    # 检查是否为重复记录（状态未变化）
                    if '重复记录' in message or '状态未变化' in message:
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

        print(f"📊 处理完成: 成功 {success_count} 条, 更新 {updated_count} 条, 跳过 {skipped_count} 条, 失败 {failed_count} 条")

        # 处理待同步队列
        print(f"🔄 开始处理待同步队列...")
        queue_result = service_process_pending_sync_queue(db_manager, config_manager)
        print(f"📊 队列处理结果: 处理 {queue_result['processed']} 个, 成功 {queue_result['success']} 个, 失败 {queue_result['failed']} 个")

        # 返回结果
        result = {
            'success': success_count > 0 or updated_count > 0 or skipped_count > 0,  # 有新增、更新或跳过都算成功
            'message': f'处理完成: 成功 {success_count} 条, 更新 {updated_count} 条, 跳过 {skipped_count} 条, 失败 {failed_count} 条',
            'statistics': {
                'total': len(table_data),
                'success': success_count,
                'updated': updated_count,  # 新增：更新计数
                'skipped': skipped_count,
                'failed': failed_count
            },
            'errors': errors[:10] if errors else [],  # 只返回前10个真正的错误
            'skipped': skipped_info[:5] if skipped_info else [],  # 返回前5个跳过记录
            'updated': updated_info[:5] if updated_info else [],  # 新增：返回前5个更新记录
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
