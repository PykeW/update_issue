#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查GitLab议题和数据库同步情况
1. 检查有gitlab_url的议题是否在GitLab中真实存在
2. 检查没有gitlab_url的议题是否在GitLab中创建了但没同步回来
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.gitlab.core.database_manager import DatabaseManager
from src.gitlab.core.gitlab_issue_manager import GitLabIssueManager, load_config

def extract_issue_iid_from_url(gitlab_url: str) -> Optional[int]:
    """从GitLab URL中提取议题IID"""
    if not gitlab_url:
        return None
    match = re.search(r'/-/issues/(\d+)', gitlab_url)
    if match:
        return int(match.group(1))
    return None

def get_all_gitlab_issues(manager: GitLabIssueManager, project_id: int) -> List[Dict[str, Any]]:
    """获取GitLab项目中的所有议题"""
    import urllib.request
    import urllib.parse
    import json
    from urllib.error import HTTPError, URLError

    all_issues = []
    page = 1
    per_page = 100

    while True:
        try:
            api_url = f"{manager.gitlab_url}/api/v4/projects/{project_id}/issues"
            params = {
                'page': page,
                'per_page': per_page,
                'state': 'all'
            }
            url = api_url + '?' + urllib.parse.urlencode(params)

            req = urllib.request.Request(url, method='GET')
            for k, v in manager.headers.items():
                req.add_header(k, v)

            with urllib.request.urlopen(req, timeout=30) as resp:
                issues = json.loads(resp.read().decode('utf-8'))
                if not issues or len(issues) == 0:
                    break
                all_issues.extend(issues)
                if len(issues) < per_page:
                    break
                page += 1
        except HTTPError as e:
            print(f"❌ 获取GitLab议题失败 (page {page}): HTTP {e.code}")
            break
        except URLError as e:
            print(f"❌ 获取GitLab议题网络错误 (page {page}): {e}")
            break
        except Exception as e:
            print(f"❌ 获取GitLab议题异常 (page {page}): {e}")
            break

    return all_issues

def check_gitlab_url_sync():
    """检查GitLab议题和数据库同步情况"""
    try:
        print("=" * 80)
        print("GitLab议题和数据库同步情况检查")
        print("=" * 80)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 初始化
        db_manager = DatabaseManager()
        config = load_config()
        if not config:
            print("❌ 无法加载GitLab配置")
            return

        manager = GitLabIssueManager(
            gitlab_url=config['gitlab_url'],
            private_token=config['private_token']
        )
        project_id = int(config['project_id'])

        # 1. 获取数据库中有gitlab_url的议题
        print("📋 步骤1: 查询数据库中有gitlab_url的议题...")
        issues_with_url = db_manager.get_issues_with_gitlab_url()
        print(f"   找到 {len(issues_with_url)} 个有gitlab_url的议题")
        print()

        # 2. 获取数据库中没有gitlab_url的议题
        print("📋 步骤2: 查询数据库中没有gitlab_url的议题...")
        query_no_url = """
        SELECT id, project_name, problem_description, status, created_at, sync_status
        FROM issues
        WHERE (gitlab_url IS NULL OR gitlab_url = '' OR gitlab_url = 'NULL')
        ORDER BY id DESC
        """
        issues_without_url = db_manager.execute_query(query_no_url)
        print(f"   找到 {len(issues_without_url)} 个没有gitlab_url的议题")
        print()

        # 3. 获取GitLab中的所有议题
        print("📋 步骤3: 从GitLab获取所有议题...")
        gitlab_issues = get_all_gitlab_issues(manager, project_id)
        print(f"   GitLab中共有 {len(gitlab_issues)} 个议题")
        print()

        # 构建GitLab议题索引（以IID为key）
        gitlab_issues_by_iid: Dict[int, Dict[str, Any]] = {}
        for issue in gitlab_issues:
            iid = issue.get('iid')
            if iid:
                gitlab_issues_by_iid[iid] = issue

        # 4. 检查有gitlab_url的议题是否在GitLab中存在
        print("=" * 80)
        print("检查结果1: 验证数据库中有gitlab_url的议题是否在GitLab中存在")
        print("=" * 80)

        valid_count = 0
        invalid_count = 0
        invalid_issues = []

        for issue in issues_with_url:
            issue_id = issue['id']
            gitlab_url = issue.get('gitlab_url', '')
            project_name = issue.get('project_name', '未知')

            if not gitlab_url or gitlab_url.strip() == '' or gitlab_url.upper() == 'NULL':
                invalid_count += 1
                invalid_issues.append({
                    'id': issue_id,
                    'project_name': project_name,
                    'reason': 'gitlab_url为空或NULL'
                })
                continue

            issue_iid = extract_issue_iid_from_url(gitlab_url)
            if not issue_iid:
                invalid_count += 1
                invalid_issues.append({
                    'id': issue_id,
                    'project_name': project_name,
                    'gitlab_url': gitlab_url,
                    'reason': '无法从URL提取议题IID'
                })
                continue

            if issue_iid in gitlab_issues_by_iid:
                valid_count += 1
            else:
                invalid_count += 1
                invalid_issues.append({
                    'id': issue_id,
                    'project_name': project_name,
                    'gitlab_url': gitlab_url,
                    'issue_iid': issue_iid,
                    'reason': 'GitLab中不存在该议题'
                })

        print(f"✅ 有效议题: {valid_count} 个")
        print(f"❌ 无效议题: {invalid_count} 个")
        print()

        if invalid_issues:
            print("无效议题详情:")
            for item in invalid_issues[:20]:  # 只显示前20个
                print(f"  - 议题ID {item['id']}: {item['project_name']}")
                print(f"    URL: {item.get('gitlab_url', 'N/A')}")
                print(f"    原因: {item['reason']}")
            if len(invalid_issues) > 20:
                print(f"  ... 还有 {len(invalid_issues) - 20} 个无效议题")
            print()

        # 5. 检查没有gitlab_url的议题是否在GitLab中创建了
        print("=" * 80)
        print("检查结果2: 检查没有gitlab_url的议题是否在GitLab中创建了")
        print("=" * 80)

        # 构建数据库议题的标题特征（用于匹配）
        db_issues_by_title_pattern: Dict[str, Dict[str, Any]] = {}
        for issue in issues_without_url:
            project_name = issue.get('project_name', '')
            problem_desc = issue.get('problem_description', '')
            if project_name and problem_desc:
                # 可能的标题格式
                title_pattern1 = f"{project_name}: {problem_desc}"
                title_pattern2 = project_name
                db_issues_by_title_pattern[title_pattern1] = issue
                if title_pattern2 != title_pattern1:
                    db_issues_by_title_pattern[title_pattern2] = issue

        # 检查GitLab议题是否在数据库中没有gitlab_url
        potential_missing = []
        for gitlab_issue in gitlab_issues:
            gitlab_title = gitlab_issue.get('title', '')
            gitlab_iid = gitlab_issue.get('iid')
            gitlab_url = gitlab_issue.get('web_url', '')

            # 尝试匹配数据库中的议题
            for title_pattern, db_issue in db_issues_by_title_pattern.items():
                if title_pattern in gitlab_title or gitlab_title.startswith(title_pattern):
                    potential_missing.append({
                        'gitlab_iid': gitlab_iid,
                        'gitlab_url': gitlab_url,
                        'gitlab_title': gitlab_title,
                        'db_issue_id': db_issue['id'],
                        'db_project_name': db_issue.get('project_name', ''),
                        'match_type': 'title_match'
                    })
                    break

        print(f"🔍 发现 {len(potential_missing)} 个可能未同步gitlab_url的议题")
        print()

        if potential_missing:
            print("可能未同步的议题详情（前20个）:")
            for item in potential_missing[:20]:
                print(f"  - GitLab议题 IID {item['gitlab_iid']}: {item['gitlab_title']}")
                print(f"    GitLab URL: {item['gitlab_url']}")
                print(f"    数据库议题ID: {item['db_issue_id']}")
                print(f"    项目名称: {item['db_project_name']}")
            if len(potential_missing) > 20:
                print(f"  ... 还有 {len(potential_missing) - 20} 个可能未同步的议题")
            print()

        # 6. 统计总结
        print("=" * 80)
        print("检查总结")
        print("=" * 80)
        print(f"数据库中有gitlab_url的议题: {len(issues_with_url)} 个")
        print(f"  - ✅ 有效（在GitLab中存在）: {valid_count} 个")
        print(f"  - ❌ 无效（在GitLab中不存在或URL无效）: {invalid_count} 个")
        print()
        print(f"数据库中没有gitlab_url的议题: {len(issues_without_url)} 个")
        print(f"  - 🔍 可能已在GitLab中创建但未同步: {len(potential_missing)} 个")
        print()
        print(f"GitLab中的总议题数: {len(gitlab_issues)} 个")
        print()
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # 7. 生成修复建议
        if invalid_issues or potential_missing:
            print()
            print("💡 修复建议:")
            if invalid_issues:
                print(f"  1. 有 {len(invalid_issues)} 个议题的gitlab_url无效，建议:")
                print("     - 检查这些议题是否在GitLab中被删除")
                print("     - 或者更新数据库中的gitlab_url字段")
            if potential_missing:
                print(f"  2. 有 {len(potential_missing)} 个议题可能已创建但未同步gitlab_url，建议:")
                print("     - 手动检查这些议题，确认是否匹配")
                print("     - 如果匹配，更新数据库中的gitlab_url字段")

    except Exception as e:
        print(f"❌ 检查过程异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_gitlab_url_sync()

