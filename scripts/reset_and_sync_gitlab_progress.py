#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空gitlab_progress字段并重新从GitLab获取进度信息
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.gitlab.core.database_manager import DatabaseManager
from src.gitlab.core.gitlab_operations import GitLabOperations

def reset_and_sync_gitlab_progress(dry_run: bool = True):
    """清空gitlab_progress字段并重新从GitLab获取"""
    try:
        print("=" * 80)
        print("清空gitlab_progress字段并重新从GitLab获取进度信息")
        print("=" * 80)
        print(f"模式: {'模拟运行（不会实际更新数据库）' if dry_run else '实际更新'}")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 初始化
        db_manager = DatabaseManager()
        gitlab_ops = GitLabOperations()
        
        # 1. 获取所有有GitLab URL的议题
        print("📋 查询数据库中有GitLab URL的议题...")
        issues = db_manager.get_issues_with_gitlab_url()
        
        if not issues:
            print("✅ 没有找到有GitLab URL的议题")
            return
        
        print(f"   找到 {len(issues)} 个有GitLab URL的议题")
        print()
        
        # 2. 先清空gitlab_progress字段
        print("=" * 80)
        print("步骤1: 清空gitlab_progress字段")
        print("=" * 80)
        
        if not dry_run:
            clear_sql = """
            UPDATE issues
            SET gitlab_progress = ''
            WHERE gitlab_url IS NOT NULL AND gitlab_url != '' AND gitlab_url != 'NULL'
            """
            if db_manager.execute_update(clear_sql):
                print(f"✅ 已清空 {len(issues)} 个议题的gitlab_progress字段")
            else:
                print(f"❌ 清空gitlab_progress字段失败")
                return
        else:
            print(f"[模拟] 将清空 {len(issues)} 个议题的gitlab_progress字段")
        
        print()
        
        # 3. 重新从GitLab获取进度信息
        print("=" * 80)
        print("步骤2: 从GitLab重新获取进度信息")
        print("=" * 80)
        
        success_count = 0
        failed_count = 0
        updated_count = 0
        unchanged_count = 0
        skipped_count = 0
        
        for i, issue in enumerate(issues, 1):
            issue_id = issue['id']
            project_name = issue.get('project_name', '未知项目')
            gitlab_url = issue.get('gitlab_url', '')
            current_progress = issue.get('gitlab_progress', '')
            
            print(f"[{i}/{len(issues)}] 处理议题 #{issue_id}: {project_name}")
            
            # 检查gitlab_url是否有效
            if not gitlab_url or gitlab_url.strip() == '' or gitlab_url.upper() == 'NULL':
                print(f"  ⏭️  跳过: 无效的GitLab URL")
                skipped_count += 1
                continue
            
            try:
                # 从GitLab获取进度信息
                progress = gitlab_ops.sync_progress_from_gitlab(gitlab_url)
                
                if progress:
                    # 检查进度是否有变化
                    if progress != current_progress:
                        if not dry_run:
                            # 更新数据库
                            if db_manager.update_issue_progress(issue_id, progress):
                                print(f"  ✅ 进度已更新: '{current_progress}' -> '{progress}'")
                                updated_count += 1
                                success_count += 1
                            else:
                                print(f"  ❌ 数据库更新失败")
                                failed_count += 1
                        else:
                            print(f"  [模拟] 进度将更新: '{current_progress}' -> '{progress}'")
                            updated_count += 1
                            success_count += 1
                    else:
                        print(f"  ✓ 进度无变化: '{progress}'")
                        unchanged_count += 1
                        success_count += 1
                else:
                    # closed状态的议题不应该有进度标签，设置为空
                    if not dry_run:
                        if db_manager.update_issue_progress(issue_id, ''):
                            if current_progress:
                                print(f"  ✅ 已清空进度标签（closed状态）: '{current_progress}' -> ''")
                                updated_count += 1
                            else:
                                print(f"  ✓ 进度已为空（closed状态）")
                            success_count += 1
                        else:
                            print(f"  ❌ 数据库更新失败")
                            failed_count += 1
                    else:
                        if current_progress:
                            print(f"  [模拟] 将清空进度标签（closed状态）: '{current_progress}' -> ''")
                            updated_count += 1
                        else:
                            print(f"  ✓ 进度已为空（closed状态）")
                        success_count += 1
                
            except Exception as e:
                print(f"  ❌ 处理异常: {str(e)}")
                failed_count += 1
            
            print()
        
        # 4. 输出统计结果
        print("=" * 80)
        print("同步完成")
        print("=" * 80)
        print(f"总议题数: {len(issues)}")
        if dry_run:
            print(f"模拟更新: {updated_count} 个")
            print(f"无变化: {unchanged_count} 个")
            print(f"跳过: {skipped_count} 个")
            print()
            print("💡 这是模拟运行，没有实际更新数据库")
            print("   要实际更新，请运行: python3 scripts/reset_and_sync_gitlab_progress.py --execute")
        else:
            print(f"成功: {success_count} 个 (更新 {updated_count} 个, 无变化 {unchanged_count} 个)")
            print(f"失败: {failed_count} 个")
            print(f"跳过: {skipped_count} 个")
        print()
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 处理过程异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='清空gitlab_progress字段并重新从GitLab获取')
    parser.add_argument('--execute', action='store_true', help='实际执行更新（默认是模拟运行）')
    args = parser.parse_args()
    
    reset_and_sync_gitlab_progress(dry_run=not args.execute)

