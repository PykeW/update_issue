#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动批量同步脚本
用于处理历史遗留的待同步任务
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.gitlab.core.database_manager import DatabaseManager
from src.gitlab.core.config_manager import ConfigManager

def get_issue_by_id(db_manager, issue_id):
    """从数据库获取议题详细信息"""
    try:
        query = f"SELECT * FROM issues WHERE id = {issue_id}"
        result = db_manager.execute_query(query)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ 获取议题详细信息失败: {str(e)}")
        return None

def sync_issue_to_gitlab(db_manager, config_manager, issue_id, action='create'):
    """立即同步议题到 GitLab"""
    try:
        print(f"🔗 开始同步议题到 GitLab: ID={issue_id}, 操作={action}")

        # 获取议题详细信息
        issue_data = get_issue_by_id(db_manager, issue_id)
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

        if action == 'create':
            # 创建新议题
            print(f"📝 创建 GitLab 议题: {issue_data.get('project_name')}")
            # 使用完整配置以包含 labels 映射（严重程度/进度/类型等）
            effective_config = full_config if full_config else gitlab_config
            result = gitlab_ops.create_issue(issue_data, effective_config, user_mapping)

            if result and result.get('success'):
                gitlab_url = result.get('url', '')
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
                error_msg = result.get('error', '创建失败') if result else '创建失败'
                print(f"❌ GitLab 议题创建失败: {error_msg}")
                return {'success': False, 'error': error_msg}

        elif action == 'close':
            # 关闭议题并移除标签
            gitlab_url = issue_data.get('gitlab_url', '')
            if gitlab_url and gitlab_url.upper() != 'NULL':
                print(f"🔒 关闭 GitLab 议题: {gitlab_url}")
                issue_iid = gitlab_ops.extract_issue_id_from_url(gitlab_url)
                if issue_iid:
                    result = gitlab_ops.close_issue(issue_iid, issue_data)
                    if result:
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

def process_pending_sync_queue(db_manager, config_manager, action_filter=None, limit=50):
    """处理待同步队列中的任务"""
    try:
        print(f"🔄 开始处理待同步队列...")

        # 构建查询条件
        where_conditions = ["status = 'pending'"]
        if action_filter:
            where_conditions.append(f"action = '{action_filter}'")

        where_clause = " AND ".join(where_conditions)

        # 查询待处理任务
        query = f"""
        SELECT id, issue_id, action, priority, metadata, created_at
        FROM sync_queue
        WHERE {where_clause}
        ORDER BY priority ASC, created_at ASC
        LIMIT {limit}
        """

        pending_tasks = db_manager.execute_query(query)

        if not pending_tasks:
            print(f"✅ 没有待处理的同步任务")
            return {
                'processed': 0,
                'success': 0,
                'failed': 0,
                'skipped': 0
            }

        print(f"📋 找到 {len(pending_tasks)} 个待处理任务")

        processed_count = 0
        success_count = 0
        failed_count = 0
        skipped_count = 0

        for i, task in enumerate(pending_tasks, 1):
            task_id = task['id']
            issue_id = task['issue_id']
            action = task['action']
            # metadata = task.get('metadata', '{}')  # 暂时未使用

            print(f"\n📋 处理任务 {i}/{len(pending_tasks)}: ID={task_id}, 议题={issue_id}, 操作={action}")

            try:
                # 1. 更新任务状态为 processing
                update_task_sql = f"""
                UPDATE sync_queue
                SET status = 'processing', processed_at = NOW()
                WHERE id = {task_id}
                """
                db_manager.execute_update(update_task_sql)

                # 2. 执行同步操作
                if action == 'close':
                    # 关闭议题
                    result = sync_issue_to_gitlab(db_manager, config_manager, issue_id, action='close')
                    if result.get('success'):
                        # 更新任务状态为 completed
                        complete_sql = f"""
                        UPDATE sync_queue
                        SET status = 'completed', processed_at = NOW()
                        WHERE id = {task_id}
                        """
                        db_manager.execute_update(complete_sql)
                        success_count += 1
                        print(f"✅ 任务 {task_id} 完成: 议题 {issue_id} 已关闭")
                    else:
                        # 更新任务状态为 failed
                        error_msg = result.get('error', '未知错误')
                        fail_sql = f"""
                        UPDATE sync_queue
                        SET status = 'failed', error_message = '{error_msg}', processed_at = NOW()
                        WHERE id = {task_id}
                        """
                        db_manager.execute_update(fail_sql)
                        failed_count += 1
                        print(f"❌ 任务 {task_id} 失败: {error_msg}")

                elif action == 'create':
                    # 创建议题
                    result = sync_issue_to_gitlab(db_manager, config_manager, issue_id, action='create')
                    if result.get('success'):
                        complete_sql = f"""
                        UPDATE sync_queue
                        SET status = 'completed', processed_at = NOW()
                        WHERE id = {task_id}
                        """
                        db_manager.execute_update(complete_sql)
                        success_count += 1
                        print(f"✅ 任务 {task_id} 完成: 议题 {issue_id} 已创建")
                    else:
                        error_msg = result.get('error', '未知错误')
                        fail_sql = f"""
                        UPDATE sync_queue
                        SET status = 'failed', error_message = '{error_msg}', processed_at = NOW()
                        WHERE id = {task_id}
                        """
                        db_manager.execute_update(fail_sql)
                        failed_count += 1
                        print(f"❌ 任务 {task_id} 失败: {error_msg}")

                elif action == 'create_and_close':
                    # 先创建再关闭
                    create_result = sync_issue_to_gitlab(db_manager, config_manager, issue_id, action='create')
                    if create_result.get('success'):
                        close_result = sync_issue_to_gitlab(db_manager, config_manager, issue_id, action='close')
                        if close_result.get('success'):
                            complete_sql = f"""
                            UPDATE sync_queue
                            SET status = 'completed', processed_at = NOW()
                            WHERE id = {task_id}
                            """
                            db_manager.execute_update(complete_sql)
                            success_count += 1
                            print(f"✅ 任务 {task_id} 完成: 议题 {issue_id} 已创建并关闭")
                        else:
                            error_msg = f"创建成功但关闭失败: {close_result.get('error', '未知错误')}"
                            fail_sql = f"""
                            UPDATE sync_queue
                            SET status = 'failed', error_message = '{error_msg}', processed_at = NOW()
                            WHERE id = {task_id}
                            """
                            db_manager.execute_update(fail_sql)
                            failed_count += 1
                            print(f"❌ 任务 {task_id} 失败: {error_msg}")
                    else:
                        error_msg = f"创建失败: {create_result.get('error', '未知错误')}"
                        fail_sql = f"""
                        UPDATE sync_queue
                        SET status = 'failed', error_message = '{error_msg}', processed_at = NOW()
                        WHERE id = {task_id}
                        """
                        db_manager.execute_update(fail_sql)
                        failed_count += 1
                        print(f"❌ 任务 {task_id} 失败: {error_msg}")

                else:
                    # 未知操作类型
                    fail_sql = f"""
                    UPDATE sync_queue
                    SET status = 'failed', error_message = '未知操作类型: {action}', processed_at = NOW()
                    WHERE id = {task_id}
                    """
                    db_manager.execute_update(fail_sql)
                    skipped_count += 1
                    print(f"⚠️ 任务 {task_id} 跳过: 未知操作类型 {action}")

                processed_count += 1

            except Exception as e:
                # 处理异常
                error_msg = str(e)
                fail_sql = f"""
                UPDATE sync_queue
                SET status = 'failed', error_message = '{error_msg}', processed_at = NOW()
                WHERE id = {task_id}
                """
                db_manager.execute_update(fail_sql)
                failed_count += 1
                processed_count += 1
                print(f"❌ 任务 {task_id} 异常: {error_msg}")

        result = {
            'processed': processed_count,
            'success': success_count,
            'failed': failed_count,
            'skipped': skipped_count
        }

        print(f"\n📊 队列处理完成: 处理 {processed_count} 个, 成功 {success_count} 个, 失败 {failed_count} 个, 跳过 {skipped_count} 个")

        return result

    except Exception as e:
        print(f"❌ 队列处理异常: {str(e)}")
        return {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'error': str(e)
        }

def show_queue_status(db_manager):
    """显示队列状态统计"""
    try:
        print("📊 同步队列状态统计:")
        print("=" * 50)

        # 按状态统计
        status_query = """
        SELECT status, COUNT(*) as count
        FROM sync_queue
        GROUP BY status
        ORDER BY status
        """
        status_stats = db_manager.execute_query(status_query)

        for stat in status_stats:
            status = stat['status']
            count = stat['count']
            print(f"  {status}: {count} 个")

        print()

        # 按操作类型统计
        action_query = """
        SELECT action, COUNT(*) as count
        FROM sync_queue
        WHERE status = 'pending'
        GROUP BY action
        ORDER BY action
        """
        action_stats = db_manager.execute_query(action_query)

        if action_stats:
            print("📋 待处理任务按操作类型:")
            for stat in action_stats:
                action = stat['action']
                count = stat['count']
                print(f"  {action}: {count} 个")
        else:
            print("✅ 没有待处理的任务")

        print()

        # 显示最近的几个待处理任务
        recent_query = """
        SELECT id, issue_id, action, priority, created_at
        FROM sync_queue
        WHERE status = 'pending'
        ORDER BY priority ASC, created_at ASC
        LIMIT 5
        """
        recent_tasks = db_manager.execute_query(recent_query)

        if recent_tasks:
            print("📋 最近的待处理任务:")
            for task in recent_tasks:
                print(f"  ID {task['id']}: 议题 {task['issue_id']}, 操作 {task['action']}, 优先级 {task['priority']}, 创建时间 {task['created_at']}")
        else:
            print("✅ 没有待处理的任务")

    except Exception as e:
        print(f"❌ 获取队列状态失败: {str(e)}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='手动批量同步脚本')
    parser.add_argument('--action', choices=['close', 'create', 'create_and_close'],
                       help='指定要处理的操作类型')
    parser.add_argument('--limit', type=int, default=50,
                       help='限制处理的任务数量 (默认: 50)')
    parser.add_argument('--status', action='store_true',
                       help='仅显示队列状态，不执行同步')
    parser.add_argument('--dry-run', action='store_true',
                       help='模拟运行，不实际执行同步')

    args = parser.parse_args()

    print("=" * 60)
    print("手动批量同步脚本")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.status:
        # 初始化数据库连接
        db_manager = DatabaseManager()
        show_queue_status(db_manager)
        return

    if args.dry_run:
        print("🔍 模拟运行模式 - 不会实际执行同步")
        # TODO: 实现 dry-run 逻辑
        return

    print(f"📋 配置:")
    print(f"  操作过滤: {args.action or '全部'}")
    print(f"  处理限制: {args.limit}")
    print()

    # 初始化数据库连接
    db_manager = DatabaseManager()
    config_manager = ConfigManager()

    try:
        # 显示当前状态
        show_queue_status(db_manager)

        # 确认执行
        if not args.action:
            confirm = input("\n⚠️ 将处理所有类型的待同步任务，确认继续？(y/N): ")
        else:
            confirm = input(f"\n⚠️ 将处理 {args.action} 类型的待同步任务，确认继续？(y/N): ")

        if confirm.lower() != 'y':
            print("❌ 操作已取消")
            return

        # 执行同步
        result = process_pending_sync_queue(db_manager, config_manager, args.action, args.limit)

        # 显示最终结果
        print("\n" + "=" * 60)
        print("同步完成")
        print("=" * 60)
        print(f"处理任务: {result['processed']} 个")
        print(f"成功: {result['success']} 个")
        print(f"失败: {result['failed']} 个")
        print(f"跳过: {result['skipped']} 个")

        if result['failed'] > 0:
            print(f"\n⚠️ 有 {result['failed']} 个任务失败，请检查日志")

        if result['processed'] == 0:
            print("\n✅ 没有需要处理的任务")

    except Exception as e:
        print(f"❌ 脚本执行异常: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
