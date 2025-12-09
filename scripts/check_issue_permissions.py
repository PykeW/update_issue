#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查token是否能够进行议题的提交（创建和更新）
"""

import json
import urllib.request
import urllib.error
from pathlib import Path

project_root = Path(__file__).parent.parent
config_path = project_root / 'config' / 'wps_gitlab_config.json'

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)
    gitlab_url = config['gitlab']['url']
    token = config['gitlab']['token']
    project_id = config['gitlab'].get('project_id', '1')

print("=" * 60)
print("检查Token议题提交权限")
print("=" * 60)
print(f"GitLab URL: {gitlab_url}")
print(f"项目ID: {project_id}")
print()

headers = {'PRIVATE-TOKEN': token}

# 1. 检查token有效性
print("1️⃣ 检查Token有效性...")
try:
    user_url = f"{gitlab_url}/api/v4/user"
    req = urllib.request.Request(user_url)
    for k, v in headers.items():
        req.add_header(k, v)

    with urllib.request.urlopen(req, timeout=30) as resp:
        user_info = json.loads(resp.read().decode('utf-8'))
        print(f"✅ Token有效")
        print(f"   用户: {user_info.get('username', 'N/A')}")
        print(f"   用户ID: {user_info.get('id', 'N/A')}")
except Exception as e:
    print(f"❌ Token无效: {e}")
    exit(1)

# 2. 检查项目访问权限
print(f"\n2️⃣ 检查项目访问权限...")
try:
    project_url = f"{gitlab_url}/api/v4/projects/{project_id}"
    req = urllib.request.Request(project_url)
    for k, v in headers.items():
        req.add_header(k, v)

    with urllib.request.urlopen(req, timeout=30) as resp:
        project_info = json.loads(resp.read().decode('utf-8'))
        print(f"✅ 可以访问项目")
        print(f"   项目名称: {project_info.get('name', 'N/A')}")
        print(f"   项目路径: {project_info.get('path_with_namespace', 'N/A')}")

        # 检查权限级别
        permissions = project_info.get('permissions', {})
        project_access = permissions.get('project_access', {})
        group_access = permissions.get('group_access', {})

        access_level = None
        if project_access:
            access_level = project_access.get('access_level')
        elif group_access:
            access_level = group_access.get('access_level')

        if access_level:
            level_names = {
                10: 'Guest',
                20: 'Reporter',
                30: 'Developer',
                40: 'Maintainer',
                50: 'Owner'
            }
            level_name = level_names.get(access_level, f'Unknown({access_level})')
            print(f"   权限级别: {level_name} (Level {access_level})")

            if access_level >= 30:
                print(f"   ✅ 权限足够（Developer及以上可以创建议题）")
            else:
                print(f"   ⚠️  权限可能不足（需要Developer及以上级别）")
except urllib.error.HTTPError as e:
    print(f"❌ 无法访问项目: HTTP {e.code}")
    if e.code == 404:
        print(f"   💡 项目不存在或token没有访问权限")
    elif e.code == 403:
        print(f"   💡 Token权限不足")
    exit(1)
except Exception as e:
    print(f"❌ 异常: {e}")
    exit(1)

# 3. 测试创建议题权限
print(f"\n3️⃣ 测试创建议题权限...")
test_issue_title = "测试议题 - Token权限检查"
test_issue_data = {
    'title': test_issue_title,
    'description': '这是一个自动测试议题，用于检查token权限。可以安全删除。'
}

try:
    issues_url = f"{gitlab_url}/api/v4/projects/{project_id}/issues"
    req = urllib.request.Request(issues_url, method='POST')
    for k, v in headers.items():
        req.add_header(k, v)
    req.add_header('Content-Type', 'application/json')

    body = json.dumps(test_issue_data).encode('utf-8')

    with urllib.request.urlopen(req, body, timeout=30) as resp:
        issue_info = json.loads(resp.read().decode('utf-8'))
        issue_id = issue_info.get('iid')
        issue_url = issue_info.get('web_url', '')

        print(f"✅ 可以创建议题")
        print(f"   议题ID: {issue_id}")
        print(f"   议题URL: {issue_url}")

        # 立即删除测试议题
        print(f"\n🗑️  删除测试议题...")
        delete_url = f"{gitlab_url}/api/v4/projects/{project_id}/issues/{issue_id}"
        delete_req = urllib.request.Request(delete_url, method='DELETE')
        for k, v in headers.items():
            delete_req.add_header(k, v)

        try:
            with urllib.request.urlopen(delete_req, timeout=30) as delete_resp:
                print(f"✅ 测试议题已删除")
        except Exception as e:
            print(f"⚠️  无法删除测试议题: {e}")
            print(f"   请手动删除: {issue_url}")

except urllib.error.HTTPError as e:
    print(f"❌ 无法创建议题: HTTP {e.code}")
    if e.code == 403:
        print(f"   💡 403错误: Token权限不足")
        print(f"   需要权限:")
        print(f"      - api scope（完整API访问）")
        print(f"      - 项目权限: Developer级别或以上")
    elif e.code == 401:
        print(f"   💡 401错误: Token无效或已过期")
    try:
        error_body = e.read().decode('utf-8')
        if error_body:
            print(f"   错误详情: {error_body}")
    except Exception:
        pass
except Exception as e:
    print(f"❌ 异常: {e}")
    import traceback
    traceback.print_exc()

# 4. 测试更新议题权限
print(f"\n4️⃣ 测试更新议题权限...")
print(f"   （需要先有一个议题才能测试更新）")
print(f"   💡 如果上面创建议题成功，说明更新权限也应该可用")

# 5. 总结
print(f"\n" + "=" * 60)
print("权限检查总结")
print("=" * 60)
print(f"✅ Token有效性: 已验证")
print(f"✅ 项目访问权限: 已验证")
print(f"✅ 创建议题权限: {'已验证' if 'issue_id' in locals() else '未验证'}")
print(f"\n💡 对于议题提交，需要的权限:")
print(f"   1. Token scopes:")
print(f"      - api（完整API访问，推荐）")
print(f"      - 或 write_api（写入API权限）")
print(f"   2. 项目权限级别:")
print(f"      - Developer（30）或以上")
print(f"      - Guest和Reporter无法创建议题")
