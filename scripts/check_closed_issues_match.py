#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查closed状态且没有gitlab_url的议题，看是否能在GitLab中找到匹配的议题
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

def normalize_text(text: str) -> str:
    """标准化文本用于匹配"""
    if not text:
        return ""
    # 移除空格和特殊字符，转为小写
    return re.sub(r'[^\w\u4e00-\u9fff]', '', text.lower())

def match_issue(db_issue: Dict[str, Any], gitlab_issue: Dict[str, Any]) -> tuple[bool, int]:
    """判断数据库议题和GitLab议题是否匹配，返回(是否匹配, 匹配分数)"""
    db_project = normalize_text(db_issue.get('project_name', ''))
    db_desc = normalize_text(db_issue.get('problem_description', ''))
    gitlab_title = normalize_text(gitlab_issue.get('title', ''))

    score = 0

    # 检查项目名称是否在标题中
    if db_project:
        if db_project in gitlab_title:
            score += 20
        elif db_project[:5] in gitlab_title:  # 部分匹配
            score += 10

    # 检查问题描述是否在标题中
    if db_desc:
        # 取问题描述的前30个字符进行匹配
        db_desc_short = db_desc[:30] if len(db_desc) > 30 else db_desc
        if db_desc_short and db_desc_short in gitlab_title:
            score += 30
        elif db_desc[:15] in gitlab_title:  # 部分匹配
            score += 15

    # 如果项目名称和问题描述都匹配，分数会更高
    is_match = score >= 20  # 至少项目名称要匹配

    return is_match, score

def check_closed_issues_match():
    """检查closed状态且没有gitlab_url的议题是否能在GitLab中找到匹配"""
    try:
        print("=" * 80)
        print("检查closed状态且没有gitlab_url的议题匹配情况")
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

        # 1. 获取数据库中有gitlab_url的议题（用于排除已匹配的）
        print("📋 查询数据库中有gitlab_url的议题...")
        issues_with_url = db_manager.get_issues_with_gitlab_url()
        existing_iids = set()
        for issue in issues_with_url:
            url = issue.get('gitlab_url', '')
            if url:
                iid = extract_issue_iid_from_url(url)
                if iid:
                    existing_iids.add(iid)
        print(f"   已排除 {len(existing_iids)} 个已有gitlab_url的议题")
        print()

        # 2. 获取closed状态且没有gitlab_url的议题
        print("📋 查询closed状态且没有gitlab_url的议题...")
        query_closed = """
        SELECT id, project_name, problem_description, status, created_at, sync_status
        FROM issues
        WHERE status = 'closed'
          AND (gitlab_url IS NULL OR gitlab_url = '' OR gitlab_url = 'NULL')
        ORDER BY id DESC
        """
        closed_issues = db_manager.execute_query(query_closed)
        print(f"   找到 {len(closed_issues)} 个closed状态且没有gitlab_url的议题")
        print()

        # 3. 获取GitLab中的所有议题（包括closed状态）
        print("📋 从GitLab获取所有议题（包括closed状态）...")
        gitlab_issues = get_all_gitlab_issues(manager, project_id)
        # 只考虑closed状态的GitLab议题
        gitlab_closed_issues = [issue for issue in gitlab_issues if issue.get('state') == 'closed']
        print(f"   GitLab中共有 {len(gitlab_issues)} 个议题（全部状态）")
        print(f"   GitLab中共有 {len(gitlab_closed_issues)} 个closed状态的议题")
        print()

        # 排除已有gitlab_url的议题对应的GitLab议题
        available_gitlab_issues = [issue for issue in gitlab_closed_issues
                                  if issue.get('iid') not in existing_iids]
        print(f"   可用于匹配的GitLab closed议题: {len(available_gitlab_issues)} 个")
        print()

        # 4. 匹配
        print("=" * 80)
        print("开始匹配")
        print("=" * 80)

        matched_issues = []
        unmatched_issues = []

        for db_issue in closed_issues:
            db_id = db_issue['id']
            db_project = db_issue.get('project_name', '')
            db_desc = db_issue.get('problem_description', '')

            best_match = None
            best_score = 0

            # 查找最佳匹配
            for gitlab_issue in available_gitlab_issues:
                is_match, score = match_issue(db_issue, gitlab_issue)
                if is_match and score > best_score:
                    best_score = score
                    best_match = gitlab_issue

            if best_match and best_score >= 20:
                gitlab_url = best_match.get('web_url', '')
                gitlab_iid = best_match.get('iid')
                gitlab_title = best_match.get('title', '')
                gitlab_state = best_match.get('state', '')

                matched_issues.append({
                    'db_id': db_id,
                    'db_project': db_project,
                    'db_desc': db_desc[:50] + '...' if len(db_desc) > 50 else db_desc,
                    'gitlab_iid': gitlab_iid,
                    'gitlab_url': gitlab_url,
                    'gitlab_title': gitlab_title,
                    'gitlab_state': gitlab_state,
                    'match_score': best_score
                })
            else:
                unmatched_issues.append({
                    'db_id': db_id,
                    'db_project': db_project,
                    'db_desc': db_desc[:50] + '...' if len(db_desc) > 50 else db_desc
                })

        # 5. 输出结果
        print("=" * 80)
        print("匹配结果")
        print("=" * 80)
        print(f"✅ 找到匹配: {len(matched_issues)} 个")
        print(f"❌ 未找到匹配: {len(unmatched_issues)} 个")
        print()

        if matched_issues:
            print("=" * 80)
            print("可以匹配的议题详情")
            print("=" * 80)
            # 按匹配分数排序
            matched_issues.sort(key=lambda x: x['match_score'], reverse=True)

            for i, match in enumerate(matched_issues[:50], 1):  # 只显示前50个
                print(f"\n[{i}] 数据库议题 ID: {match['db_id']}")
                print(f"    项目: {match['db_project']}")
                print(f"    问题描述: {match['db_desc']}")
                print(f"    ↓ 匹配到 ↓")
                print(f"    GitLab议题 IID: {match['gitlab_iid']}")
                print(f"    GitLab标题: {match['gitlab_title']}")
                print(f"    GitLab URL: {match['gitlab_url']}")
                print(f"    GitLab状态: {match['gitlab_state']}")
                print(f"    匹配分数: {match['match_score']}")

            if len(matched_issues) > 50:
                print(f"\n... 还有 {len(matched_issues) - 50} 个匹配的议题")

        # 6. 统计总结
        print("\n" + "=" * 80)
        print("统计总结")
        print("=" * 80)
        print(f"数据库closed状态且没有gitlab_url的议题: {len(closed_issues)} 个")
        print(f"  - ✅ 可以在GitLab中找到匹配: {len(matched_issues)} 个")
        print(f"  - ❌ 在GitLab中找不到匹配: {len(unmatched_issues)} 个")
        print()
        print(f"GitLab中可用于匹配的closed议题: {len(available_gitlab_issues)} 个")
        print()
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # 7. 生成更新SQL建议
        if matched_issues:
            print("\n" + "=" * 80)
            print("更新SQL建议（前20个）")
            print("=" * 80)
            for match in matched_issues[:20]:
                gitlab_url_escaped = match['gitlab_url'].replace("'", "''")
                print(f"-- 议题ID {match['db_id']}: {match['db_project']}")
                print(f"UPDATE issues SET gitlab_url = '{gitlab_url_escaped}', sync_status = 'synced', last_sync_time = NOW() WHERE id = {match['db_id']};")
                print()

    except Exception as e:
        print(f"❌ 检查过程异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_closed_issues_match()

