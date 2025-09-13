#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库到GitLab同步工具
将数据库中的议题同步到GitLab平台，并更新数据库中的GitLab链接
"""

import os
import sys
import json
import requests
import subprocess
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gitlab_issue_manager import GitLabIssueManager, load_config

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'issue',
    'password': 'hszc8888',
    'database': 'issue_database'
}

def get_database_issues():
    """
    从数据库获取所有议题
    """
    try:
        cmd = [
            'mysql', '-u', DB_CONFIG['user'], f'-p{DB_CONFIG["password"]}',
            '-h', DB_CONFIG['host'], '-P', str(DB_CONFIG['port']),
            '-e', f"USE {DB_CONFIG['database']}; SELECT id, project_name, problem_category, severity_level, problem_description, solution, action_priority, action_record, initiator, responsible_person, status, start_time, target_completion_time, actual_completion_time, remarks, gitlab_url FROM issues ORDER BY id;"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # 解析MySQL输出
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return []

        # 获取列名
        headers = lines[0].split('\t')
        issues = []

        for line in lines[1:]:
            if line.strip():
                values = line.split('\t')
                issue = dict(zip(headers, values))
                issues.append(issue)

        return issues
    except subprocess.CalledProcessError as e:
        print(f"❌ 数据库查询失败: {e}")
        print(f"错误输出: {e.stderr}")
        return []
    except Exception as e:
        print(f"❌ 获取数据库议题时发生错误: {e}")
        return []

def update_issue_gitlab_url(issue_id, gitlab_url):
    """
    更新数据库中的GitLab链接
    """
    try:
        cmd = [
            'mysql', '-u', DB_CONFIG['user'], f'-p{DB_CONFIG["password"]}',
            '-h', DB_CONFIG['host'], '-P', str(DB_CONFIG['port']),
            '-e', f"USE {DB_CONFIG['database']}; UPDATE issues SET gitlab_url = '{gitlab_url}' WHERE id = {issue_id};"
        ]

        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 更新GitLab链接失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 更新数据库时发生错误: {e}")
        return False

def load_gitlab_config():
    """
    加载GitLab配置
    """
    config_file = os.path.join(os.path.dirname(__file__), 'wps_gitlab_config.json')
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  无法加载配置文件: {e}")
        return None

def map_severity_to_labels(severity_level, config=None):
    """
    将严重程度映射为客户需求标签
    """
    if config and 'labels' in config and 'severity_mapping' in config['labels']:
        severity_str = str(severity_level) if severity_level else '0'
        return config['labels']['severity_mapping'].get(severity_str, ['客户需求', '一般'])
    else:
        # 默认映射
        severity = int(severity_level) if severity_level else 0
        if severity <= 2:
            return ['客户需求', '紧急']
        elif severity == 3:
            return ['客户需求', '中等']
        else:  # severity >= 4
            return ['客户需求', '一般']

def map_status_to_progress(status, config=None):
    """
    将状态映射为进度标签
    """
    if config and 'labels' in config and 'progress_mapping' in config['labels']:
        return config['labels']['progress_mapping'].get(status, 'To do')
    else:
        # 默认映射
        status_mapping = {
            'open': 'To do',
            'in_progress': 'Doing',
            'closed': 'Done',
            'resolved': 'Done'
        }
        return status_mapping.get(status, 'To do')

def create_gitlab_issue(manager, project_id, issue_data, config=None):
    """
    在GitLab中创建议题
    """
    # 构建标题
    title = f"{issue_data['project_name']}: {issue_data['problem_description']}"

    # 构建描述
    description = f"""
## 问题详情

**项目名称**: {issue_data['project_name']}
**问题分类**: {issue_data['problem_category']}
**严重程度**: {issue_data['severity_level']}
**责任人**: {issue_data['responsible_person']}
**发起人**: {issue_data['initiator']}

## 问题描述
{issue_data['problem_description']}

## 解决方案
{issue_data['solution'] or '待制定'}

## 行动记录
{issue_data['action_record'] or '待记录'}

## 时间信息
- **开始时间**: {issue_data['start_time'] or '待定'}
- **目标完成时间**: {issue_data['target_completion_time'] or '待定'}
- **实际完成时间**: {issue_data['actual_completion_time'] or '待定'}

## 备注
{issue_data['remarks'] or '无'}

---
*此议题由WPS表格数据自动同步创建*
    """.strip()

    # 构建标签
    labels = []

    # 添加严重程度标签
    severity_labels = map_severity_to_labels(issue_data['severity_level'], config)
    labels.extend(severity_labels)

    # 添加进度标签
    progress_label = map_status_to_progress(issue_data['status'], config)
    labels.append(progress_label)

    # 添加其他标签（只使用现有标签）
    if config and 'labels' in config and 'additional_labels' in config['labels']:
        labels.extend(config['labels']['additional_labels'])

    # 智能议题类型识别
    problem_desc = issue_data['problem_description'].lower()
    issue_type_label = None

    if config and 'labels' in config and 'issue_type_mapping' in config['labels']:
        mapping = config['labels']['issue_type_mapping']

        # 按优先级检查关键词
        for category, config_data in mapping.items():
            keywords = config_data['keywords']
            if any(keyword in problem_desc for keyword in keywords):
                issue_type_label = config_data['label']
                break

        # 如果没有匹配到，使用默认标签
        if not issue_type_label:
            issue_type_label = '议题类型::功能优化'  # 默认为功能优化
    else:
        # 默认逻辑
        if any(keyword in problem_desc for keyword in ['bug', '错误', '故障', '问题', '崩溃', '异常']):
            issue_type_label = '议题类型::Bug'
        elif any(keyword in problem_desc for keyword in ['优化', '改进', '提升', '性能', '速度', '响应']):
            issue_type_label = '议题类型::功能优化'
        elif any(keyword in problem_desc for keyword in ['新增', '添加', '开发', '实现', '功能', '模块']):
            issue_type_label = '议题类型::新增功能'
        elif any(keyword in problem_desc for keyword in ['算法', '模型', '检测', '识别', '分析', '计算']):
            issue_type_label = '议题类型::算法需求'
        else:
            issue_type_label = '议题类型::功能优化'  # 默认

    if issue_type_label:
        labels.append(issue_type_label)

    # 创建议题
    gitlab_issue = manager.create_issue(
        project_id=project_id,
        title=title,
        description=description,
        labels=labels
    )

    return gitlab_issue

def sync_issues_to_gitlab():
    """
    同步数据库议题到GitLab
    """
    print("=" * 60)
    print("数据库到GitLab同步工具")
    print("=" * 60)

    # 加载GitLab配置
    config = load_config()
    if not config:
        return False

    print(f"GitLab URL: {config['gitlab_url']}")
    print(f"项目路径: {config['project_path']}")
    print(f"项目ID: {config['project_id']}")
    print()

    # 创建GitLab客户端
    manager = GitLabIssueManager(config['gitlab_url'], config['private_token'])

    # 加载GitLab配置
    gitlab_config = load_gitlab_config()
    if gitlab_config:
        print("✅ 已加载GitLab配置")
    else:
        print("⚠️  使用默认配置")

    # 获取数据库议题
    print("📋 获取数据库议题...")
    issues = get_database_issues()
    if not issues:
        print("❌ 没有找到数据库议题")
        return False

    print(f"✅ 找到 {len(issues)} 个数据库议题")

    # 过滤出还没有GitLab链接的议题（或者强制同步所有议题）
    unsynced_issues = [issue for issue in issues if not issue.get('gitlab_url') or issue.get('gitlab_url') == 'NULL']
    print(f"📤 需要同步的议题: {len(unsynced_issues)} 个")

    if not unsynced_issues:
        print("✅ 所有议题都已同步到GitLab")
        return True

    # 同步议题
    success_count = 0
    for i, issue in enumerate(unsynced_issues, 1):
        print(f"\n🔄 同步议题 {i}/{len(unsynced_issues)}: {issue['project_name']}")

        try:
            # 在GitLab中创建议题
            gitlab_issue = create_gitlab_issue(manager, config['project_id'], issue, gitlab_config)

            if gitlab_issue:
                print(f"✅ 议题创建成功: {gitlab_issue['web_url']}")

                # 更新数据库中的GitLab链接
                if update_issue_gitlab_url(issue['id'], gitlab_issue['web_url']):
                    print(f"✅ 数据库链接更新成功")
                    success_count += 1
                else:
                    print(f"❌ 数据库链接更新失败")
            else:
                print(f"❌ 议题创建失败")

        except Exception as e:
            print(f"❌ 同步议题时发生错误: {e}")

    print(f"\n📊 同步完成: {success_count}/{len(unsynced_issues)} 个议题成功")
    return success_count > 0

def show_usage():
    """
    显示使用说明
    """
    print("=" * 60)
    print("数据库到GitLab同步工具 - 使用说明")
    print("=" * 60)
    print()
    print("🚀 功能:")
    print("   - 从数据库读取议题")
    print("   - 同步议题到GitLab平台")
    print("   - 更新数据库中的GitLab链接")
    print("   - 自动映射标签和状态")
    print()
    print("📁 配置文件: gitlab.env")
    print("🔧 环境变量:")
    print("   GITLAB_URL=https://dev.heils.cn")
    print("   GITLAB_PRIVATE_TOKEN=glpat-xxxxxxxxxxxx")
    print("   GITLAB_PROJECT_ID=1")
    print("   GITLAB_PROJECT_PATH=aoi/aoi-demo-r")
    print()
    print("💡 使用方法:")
    print("   python3 sync_database_to_gitlab.py")
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_usage()
    else:
        success = sync_issues_to_gitlab()
        if success:
            print("\n🎉 同步完成!")
        else:
            print("\n💥 同步失败!")
            sys.exit(1)
