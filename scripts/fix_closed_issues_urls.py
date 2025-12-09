#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动修复closed状态且没有gitlab_url的议题
根据匹配结果批量更新gitlab_url
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
    return re.sub(r'[^\w\u4e00-\u9fff]', '', text.lower())

def match_issue(db_issue: Dict[str, Any], gitlab_issue: Dict[str, Any]) -> tuple[bool, int]:
    """判断数据库议题和GitLab议题是否匹配，返回(是否匹配, 匹配分数)"""
    db_project = normalize_text(db_issue.get('project_name', ''))
    db_desc = normalize_text(db_issue.get('problem_description', ''))
    gitlab_title = normalize_text(gitlab_issue.get('title', ''))

    score = 0

    if db_project:
        if db_project in gitlab_title:
            score += 20
        elif db_project[:5] in gitlab_title:
            score += 10

    if db_desc:
        db_desc_short = db_desc[:30] if len(db_desc) > 30 else db_desc
        if db_desc_short and db_desc_short in gitlab_title:
            score += 30
        elif db_desc[:15] in gitlab_title:
            score += 15

    is_match = score >= 20
    return is_match, score

def fix_closed_issues_urls(dry_run: bool = True, min_score: int = 30):
    """修复closed状态且没有gitlab_url的议题"""
    try:
        print("=" * 80)
        print("修复closed状态且没有gitlab_url的议题")
        print("=" * 80)
        print(f"模式: {'模拟运行（不会实际更新数据库）' if dry_run else '实际更新'}")
        print(f"最低匹配分数: {min_score}")
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

        # 3. 获取GitLab中的所有closed议题
        print("📋 从GitLab获取所有closed状态的议题...")
        gitlab_issues = get_all_gitlab_issues(manager, project_id)
        gitlab_closed_issues = [issue for issue in gitlab_issues if issue.get('state') == 'closed']
        available_gitlab_issues = [issue for issue in gitlab_closed_issues
                                  if issue.get('iid') not in existing_iids]
        print(f"   可用于匹配的GitLab closed议题: {len(available_gitlab_issues)} 个")
        print()

        # 4. 匹配并更新
        print("=" * 80)
        print("开始匹配和更新")
        print("=" * 80)

        matched_count = 0
        updated_count = 0
        failed_count = 0
        skipped_count = 0

        for db_issue in closed_issues:
            db_id = db_issue['id']
            db_project = db_issue.get('project_name', '')
            db_desc = db_issue.get('problem_description', '')

            best_match = None
            best_score = 0

            for gitlab_issue in available_gitlab_issues:
                is_match, score = match_issue(db_issue, gitlab_issue)
                if is_match and score > best_score:
                    best_score = score
                    best_match = gitlab_issue

            if best_match and best_score >= min_score:
                gitlab_url = best_match.get('web_url', '')
                gitlab_iid = best_match.get('iid')
                gitlab_title = best_match.get('title', '')

                print(f"✅ 匹配成功: 数据库议题 #{db_id} -> GitLab议题 #{gitlab_iid} (分数: {best_score})")
                print(f"   项目: {db_project}")
                print(f"   GitLab标题: {gitlab_title[:60]}...")
                print(f"   GitLab URL: {gitlab_url}")

                if not dry_run:
                    gitlab_url_escaped = gitlab_url.replace("'", "''")
                    update_sql = f"""
                    UPDATE issues
                    SET gitlab_url = '{gitlab_url_escaped}',
                        sync_status = 'synced',
                        last_sync_time = NOW()
                    WHERE id = {db_id}
                    """
                    if db_manager.execute_update(update_sql):
                        updated_count += 1
                        existing_iids.add(gitlab_iid)
                        available_gitlab_issues = [issue for issue in available_gitlab_issues
                                                  if issue.get('iid') != gitlab_iid]
                        print(f"   ✅ 数据库已更新")
                    else:
                        failed_count += 1
                        print(f"   ❌ 数据库更新失败")
                else:
                    matched_count += 1
                    print(f"   [模拟] 将更新数据库")

                print()
            elif best_match and best_score < min_score:
                skipped_count += 1
                print(f"⏭️  跳过: 数据库议题 #{db_id} 匹配分数 {best_score} < {min_score} (最低要求)")
                print()

        # 5. 统计总结
        print("=" * 80)
        print("修复总结")
        print("=" * 80)
        if dry_run:
            print(f"模拟匹配: {matched_count} 个议题（匹配分数 >= {min_score}）")
            print(f"跳过: {skipped_count} 个议题（匹配分数 < {min_score}）")
            print()
            print("💡 这是模拟运行，没有实际更新数据库")
            print("   要实际更新，请运行: python3 scripts/fix_closed_issues_urls.py --execute")
        else:
            print(f"成功更新: {updated_count} 个议题")
            print(f"更新失败: {failed_count} 个议题")
            print(f"跳过: {skipped_count} 个议题（匹配分数 < {min_score}）")
        print()
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    except Exception as e:
        print(f"❌ 修复过程异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='修复closed状态且没有gitlab_url的议题')
    parser.add_argument('--execute', action='store_true', help='实际执行更新（默认是模拟运行）')
    parser.add_argument('--min-score', type=int, default=30, help='最低匹配分数（默认30）')
    args = parser.parse_args()

    fix_closed_issues_urls(dry_run=not args.execute, min_score=args.min_score)

