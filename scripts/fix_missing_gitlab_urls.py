#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复缺失的gitlab_url
根据检查结果，更新数据库中缺失的gitlab_url字段
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

def match_issue(db_issue: Dict[str, Any], gitlab_issue: Dict[str, Any]) -> bool:
    """判断数据库议题和GitLab议题是否匹配"""
    db_project = normalize_text(db_issue.get('project_name', ''))
    db_desc = normalize_text(db_issue.get('problem_description', ''))
    gitlab_title = normalize_text(gitlab_issue.get('title', ''))

    # 检查项目名称是否在标题中
    if db_project and db_project not in gitlab_title:
        return False

    # 检查问题描述是否在标题中（至少部分匹配）
    if db_desc:
        # 取问题描述的前20个字符进行匹配
        db_desc_short = db_desc[:20] if len(db_desc) > 20 else db_desc
        if db_desc_short and db_desc_short not in gitlab_title:
            return False

    return True

def fix_missing_gitlab_urls(dry_run: bool = True):
    """修复缺失的gitlab_url"""
    try:
        print("=" * 80)
        print("修复缺失的gitlab_url")
        print("=" * 80)
        print(f"模式: {'模拟运行（不会实际更新数据库）' if dry_run else '实际更新'}")
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

        # 1. 获取数据库中没有gitlab_url的议题
        print("📋 查询数据库中没有gitlab_url的议题...")
        query_no_url = """
        SELECT id, project_name, problem_description, status, created_at, sync_status
        FROM issues
        WHERE (gitlab_url IS NULL OR gitlab_url = '' OR gitlab_url = 'NULL')
        AND status != 'closed'
        ORDER BY id DESC
        """
        issues_without_url = db_manager.execute_query(query_no_url)
        print(f"   找到 {len(issues_without_url)} 个没有gitlab_url的议题（排除closed状态）")
        print()

        # 2. 获取GitLab中的所有议题
        print("📋 从GitLab获取所有议题...")
        gitlab_issues = get_all_gitlab_issues(manager, project_id)
        print(f"   GitLab中共有 {len(gitlab_issues)} 个议题")
        print()

        # 3. 获取数据库中有gitlab_url的议题（用于排除已匹配的）
        print("📋 查询数据库中有gitlab_url的议题...")
        issues_with_url = db_manager.get_issues_with_gitlab_url()
        existing_urls = set()
        for issue in issues_with_url:
            url = issue.get('gitlab_url', '')
            if url:
                iid = extract_issue_iid_from_url(url)
                if iid:
                    existing_urls.add(iid)
        print(f"   已排除 {len(existing_urls)} 个已有gitlab_url的议题")
        print()

        # 4. 匹配并更新
        print("=" * 80)
        print("开始匹配和更新")
        print("=" * 80)

        matched_count = 0
        updated_count = 0
        failed_count = 0

        for db_issue in issues_without_url:
            db_id = db_issue['id']
            db_project = db_issue.get('project_name', '')

            best_match = None
            best_score = 0

            # 查找最佳匹配
            for gitlab_issue in gitlab_issues:
                gitlab_iid = gitlab_issue.get('iid')
                if not gitlab_iid or gitlab_iid in existing_urls:
                    continue

                if match_issue(db_issue, gitlab_issue):
                    # 计算匹配分数
                    score = 0
                    db_project_norm = normalize_text(db_project)
                    gitlab_title_norm = normalize_text(gitlab_issue.get('title', ''))

                    if db_project_norm in gitlab_title_norm:
                        score += 10

                    db_desc_norm = normalize_text(db_issue.get('problem_description', ''))
                    if db_desc_norm and db_desc_norm[:30] in gitlab_title_norm:
                        score += 20

                    if score > best_score:
                        best_score = score
                        best_match = gitlab_issue

            if best_match and best_score >= 10:
                gitlab_url = best_match.get('web_url', '')
                gitlab_iid = best_match.get('iid')
                gitlab_title = best_match.get('title', '')

                print(f"✅ 匹配成功: 数据库议题 #{db_id} -> GitLab议题 #{gitlab_iid}")
                print(f"   项目: {db_project}")
                print(f"   GitLab标题: {gitlab_title}")
                print(f"   GitLab URL: {gitlab_url}")
                print(f"   匹配分数: {best_score}")

                if not dry_run:
                    # 更新数据库
                    update_sql = f"""
                    UPDATE issues
                    SET gitlab_url = '{gitlab_url.replace("'", "''")}',
                        sync_status = 'synced',
                        last_sync_time = NOW()
                    WHERE id = {db_id}
                    """
                    if db_manager.execute_update(update_sql):
                        updated_count += 1
                        existing_urls.add(gitlab_iid)  # 标记为已使用
                        print(f"   ✅ 数据库已更新")
                    else:
                        failed_count += 1
                        print(f"   ❌ 数据库更新失败")
                else:
                    matched_count += 1
                    print(f"   [模拟] 将更新数据库")

                print()

        # 5. 统计总结
        print("=" * 80)
        print("修复总结")
        print("=" * 80)
        if dry_run:
            print(f"模拟匹配: {matched_count} 个议题")
            print()
            print("💡 这是模拟运行，没有实际更新数据库")
            print("   要实际更新，请运行: python3 scripts/fix_missing_gitlab_urls.py --execute")
        else:
            print(f"成功更新: {updated_count} 个议题")
            print(f"更新失败: {failed_count} 个议题")
        print()
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    except Exception as e:
        print(f"❌ 修复过程异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='修复缺失的gitlab_url')
    parser.add_argument('--execute', action='store_true', help='实际执行更新（默认是模拟运行）')
    args = parser.parse_args()

    fix_missing_gitlab_urls(dry_run=not args.execute)

