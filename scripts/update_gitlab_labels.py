#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新GitLab议题标签脚本
为已创建的议题添加正确的严重程度标签
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.gitlab.core.database_manager import DatabaseManager
from src.gitlab.core.gitlab_issue_manager import GitLabIssueManager, load_config

def update_issue_labels():
    """更新议题标签"""
    try:
        # 初始化数据库管理器
        db_manager = DatabaseManager()

        # 加载GitLab配置
        config = load_config()
        if not config:
            print("❌ 无法加载GitLab配置")
            return

        # 初始化GitLab管理器
        manager = GitLabIssueManager(
            gitlab_url=config['gitlab_url'],
            private_token=config['private_token']
        )

        project_id = int(config['project_id'])

        # 获取需要更新标签的议题
        query = '''
        SELECT id, project_name, severity_level, gitlab_url, problem_description, status
        FROM issues
        WHERE id >= 2240 AND gitlab_url IS NOT NULL AND gitlab_url != 'NULL'
        ORDER BY id DESC
        '''

        results = db_manager.execute_query(query)
        print(f"📋 找到 {len(results)} 个需要更新标签的议题")

        for row in results:
            issue_id = row['id']
            project_name = row['project_name']
            severity_level = row['severity_level']
            gitlab_url = row['gitlab_url']
            problem_description = row['problem_description']
            status = row['status']

            print(f"\n🔄 处理议题 {issue_id}: {project_name}")

            # 从GitLab URL提取议题IID
            if '/issues/' in gitlab_url:
                issue_iid = int(gitlab_url.split('/issues/')[-1])
            else:
                print(f"❌ 无法从URL提取议题IID: {gitlab_url}")
                continue

            # 构建新标签
            labels = []

            # 严重程度标签 - 使用硬编码映射
            severity_mapping = {
                "1": ["客户需求::紧急"],
                "2": ["客户需求::中等"],
                "3": ["客户需求::一般"],
                "4": ["客户需求::一般"]
            }

            severity_str = str(severity_level)
            if severity_str in severity_mapping:
                labels.extend(severity_mapping[severity_str])

            # 进度标签
            progress_mapping = {
                "open": "进度::To do",
                "in_progress": "进度::Doing",
                "closed": "进度::Done",
                "resolved": "进度::Done"
            }
            progress_label = progress_mapping.get(status, '进度::To do')
            labels.append(progress_label)

            # 议题类型标签 - 简化版本
            problem_desc = problem_description.lower()
            if any(keyword in problem_desc for keyword in ["bug", "错误", "故障", "问题", "崩溃", "异常"]):
                labels.append("议题类型::Bug")
            elif any(keyword in problem_desc for keyword in ["算法", "模型", "检测", "识别", "分析", "计算"]):
                labels.append("议题类型::算法需求")
            elif any(keyword in problem_desc for keyword in ["新增", "添加", "开发", "实现", "功能", "模块"]):
                labels.append("议题类型::新增功能")
            else:
                labels.append("议题类型::功能优化")

            # 固定标签
            labels.append("跟踪")

            print(f"   严重程度: {severity_level} → 标签: {severity_mapping.get(severity_str, [])}")
            print(f"   状态: {status} → 标签: {progress_label}")
            print(f"   所有标签: {labels}")

            # 更新GitLab议题标签
            result = manager.update_issue(
                project_id=project_id,
                issue_iid=issue_iid,
                labels=labels
            )

            if result:
                print(f"✅ 议题 {issue_id} 标签更新成功")
            else:
                print(f"❌ 议题 {issue_id} 标签更新失败")

        print(f"\n📊 标签更新完成")

    except Exception as e:
        print(f"❌ 更新标签时发生异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_issue_labels()
