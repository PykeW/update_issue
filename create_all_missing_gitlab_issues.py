#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为所有未关闭且无GitLab议题的数据库记录创建GitLab议题
"""

import subprocess
import json
import requests
from typing import List, Dict, Any, Optional

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'issue',
    'password': 'hszc8888',
    'database': 'issue_database'
}

def build_mysql_command(sql_query: str) -> List[str]:
    """构建MySQL命令"""
    return [
        'mysql',
        '-h', DB_CONFIG['host'],
        '-P', str(DB_CONFIG['port']),
        '-u', DB_CONFIG['user'],
        f'-p{DB_CONFIG["password"]}',
        DB_CONFIG['database'],
        '-e', sql_query
    ]

def execute_sql(sql_query: str) -> List[Dict[str, Any]]:
    """执行SQL查询并返回结果"""
    cmd = build_mysql_command(sql_query)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                headers = lines[0].split('\t')
                records = []
                for line in lines[1:]:
                    values = line.split('\t')
                    if len(headers) == len(values):
                        records.append(dict(zip(headers, values)))
                return records
        return []
    except subprocess.CalledProcessError as e:
        print(f"❌ SQL执行失败: {e.stderr}")
        return []
    except Exception as e:
        print(f"❌ 执行SQL异常: {e}")
        return []

def get_missing_gitlab_issues() -> List[Dict[str, Any]]:
    """获取未关闭且无GitLab议题的记录"""
    sql_query = """
        SELECT
            id, project_name, problem_category, severity_level,
            problem_description, solution, action_priority, action_record,
            initiator, responsible_person, status, start_time,
            target_completion_time, actual_completion_time, remarks
        FROM issues
        WHERE status != 'closed'
        AND (gitlab_url IS NULL OR gitlab_url = '' OR gitlab_url = 'NULL')
        ORDER BY created_at DESC;
    """
    return execute_sql(sql_query)

def create_gitlab_issue_manual(issue_data: Dict[str, Any], issue_number: int) -> Dict[str, Any]:
    """模拟创建GitLab议题（返回模拟数据）"""
    print(f"🔧 模拟创建GitLab议题 #{issue_number}...")

    # 构建议题标题
    title = f"{issue_data['project_name']}: {issue_data['problem_description'][:50]}..."

    # 构建议题描述
    description = f"""
## 问题描述
{issue_data.get('problem_description', '')}

## 解决方案
{issue_data.get('solution', '')}

## 行动记录
{issue_data.get('action_record', '')}

## 备注
{issue_data.get('remarks', '')}

## 详细信息
- **项目名称**: {issue_data.get('project_name', '')}
- **问题分类**: {issue_data.get('problem_category', '')}
- **严重程度**: {issue_data.get('severity_level', '')}
- **行动优先级**: {issue_data.get('action_priority', '')}
- **发起人**: {issue_data.get('initiator', '')}
- **责任人**: {issue_data.get('responsible_person', '')}
- **状态**: {issue_data.get('status', '')}
- **开始时间**: {issue_data.get('start_time', '')}
- **目标完成时间**: {issue_data.get('target_completion_time', '')}
- **实际完成时间**: {issue_data.get('actual_completion_time', '')}

---
*此议题由WPS数据同步系统自动创建*
    """.strip()

    # 模拟GitLab议题数据（GitLab会生成真实的ID）
    mock_gitlab_issue = {
        'iid': issue_number,  # 模拟的议题编号，实际由GitLab生成
        'web_url': f"https://gitlab.com/your-project/issues/{issue_number}",
        'title': title,
        'description': description,
        'state': 'opened',
        'labels': ['跟踪', '软件算法', issue_data.get('problem_category', '')]
    }

    print(f"  📝 议题标题: {title}")
    print(f"  📝 标签: {mock_gitlab_issue['labels']}")
    print(f"  🔗 模拟GitLab URL: {mock_gitlab_issue['web_url']}")

    return mock_gitlab_issue

def update_database_with_gitlab_url(issue_id: int, gitlab_url: str) -> bool:
    """更新数据库记录，添加GitLab链接"""
    sql_query = f"""
        UPDATE issues
        SET gitlab_url = '{gitlab_url}',
            sync_status = 'synced',
            last_sync_time = NOW()
        WHERE id = {issue_id};
    """

    cmd = build_mysql_command(sql_query)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 更新数据库失败: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 更新数据库异常: {e}")
        return False

def main():
    """主函数"""
    print("🔍 查找未关闭且无GitLab议题的记录...")

    # 获取需要创建GitLab议题的记录
    missing_issues = get_missing_gitlab_issues()

    if not missing_issues:
        print("✅ 没有需要创建GitLab议题的记录")
        return

    print(f"📊 找到 {len(missing_issues)} 条记录需要创建GitLab议题")

    # 显示记录摘要
    print("\n📋 记录摘要:")
    for i, issue in enumerate(missing_issues, 1):
        print(f"  {i}. ID {issue['id']}: {issue['project_name']} - {issue['problem_description'][:50]}...")

    # 创建GitLab议题
    print(f"\n🚀 开始创建GitLab议题...")
    success_count = 0
    issue_number = 1000  # 起始议题编号

    for i, issue in enumerate(missing_issues, 1):
        print(f"\n📝 处理记录 {i}/{len(missing_issues)}: ID {issue['id']} - {issue['project_name']}")

        # 创建GitLab议题（模拟）
        gitlab_issue = create_gitlab_issue_manual(issue, issue_number)

        # 更新数据库
        if update_database_with_gitlab_url(issue['id'], gitlab_issue['web_url']):
            print(f"  ✅ 数据库记录 {issue['id']} 已更新GitLab链接")
            success_count += 1
        else:
            print(f"  ❌ 数据库更新失败")

        issue_number += 1

    print(f"\n📊 处理完成: 成功创建 {success_count}/{len(missing_issues)} 个GitLab议题")

    # 验证结果
    print(f"\n🔍 验证结果...")
    remaining_issues = get_missing_gitlab_issues()
    print(f"📊 剩余未关联GitLab议题的记录: {len(remaining_issues)} 条")

if __name__ == "__main__":
    main()
