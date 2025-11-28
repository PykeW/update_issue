#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Token的权限范围（scopes）
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

headers = {'PRIVATE-TOKEN': token}

print("=" * 60)
print("检查 Token 权限范围")
print("=" * 60)
print(f"GitLab URL: {gitlab_url}")
print()

# 1. 获取当前用户信息
print("1️⃣ 获取Token关联的用户信息...")
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
        print(f"   邮箱: {user_info.get('email', 'N/A')}")
except Exception as e:
    print(f"❌ Token无效: {e}")
    exit(1)

# 2. 尝试不同的API操作来推断权限
print(f"\n2️⃣ 测试Token权限...")

permissions = {
    'read_api': False,
    'read_package_registry': False,
    'write_package_registry': False,
    'read_repository': False,
}

# 测试 read_api - 读取项目信息
print(f"   测试 read_api 权限...")
try:
    project_url = f"{gitlab_url}/api/v4/projects/9"
    req = urllib.request.Request(project_url)
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30) as resp:
        permissions['read_api'] = True
        print(f"   ✅ read_api: 有权限")
except urllib.error.HTTPError as e:
    if e.code == 403:
        print(f"   ❌ read_api: 无权限 (403)")
    else:
        print(f"   ⚠️  read_api: 未知错误 ({e.code})")
except Exception as e:
    print(f"   ⚠️  read_api: {e}")

# 测试 read_package_registry - 读取package信息（已确认可以）
print(f"   测试 read_package_registry 权限...")
try:
    package_url = f"{gitlab_url}/api/v4/projects/9/packages/6739"
    req = urllib.request.Request(package_url)
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30) as resp:
        permissions['read_package_registry'] = True
        print(f"   ✅ read_package_registry: 有权限（可以读取package信息）")
except urllib.error.HTTPError as e:
    if e.code == 403:
        print(f"   ❌ read_package_registry: 无权限 (403)")
    else:
        print(f"   ⚠️  read_package_registry: 未知错误 ({e.code})")
except Exception as e:
    print(f"   ⚠️  read_package_registry: {e}")

# 测试下载文件权限
print(f"   测试下载package文件权限...")
try:
    download_url = f"{gitlab_url}/api/v4/projects/9/packages/6739/package_files/52166/download"
    req = urllib.request.Request(download_url)
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(f"   ✅ 下载权限: 有权限")
        permissions['read_package_registry'] = True  # 如果能下载，说明有权限
except urllib.error.HTTPError as e:
    if e.code == 404:
        print(f"   ❌ 下载权限: 404错误（可能是权限不足或端点不正确）")
    elif e.code == 403:
        print(f"   ❌ 下载权限: 无权限 (403)")
        permissions['read_package_registry'] = False
    else:
        print(f"   ⚠️  下载权限: 未知错误 ({e.code})")
except Exception as e:
    print(f"   ⚠️  下载权限: {e}")

# 3. 总结和建议
print(f"\n3️⃣ 权限总结:")
print(f"   read_api: {'✅' if permissions['read_api'] else '❌'}")
print(f"   read_package_registry: {'✅' if permissions['read_package_registry'] else '❌'}")

print(f"\n💡 对于下载PyPI package文件，需要的权限:")
print(f"   1. ✅ read_api - 基础API访问权限")
print(f"   2. ✅ read_package_registry - 读取package注册表权限")
print(f"   3. ⚠️  可能还需要: api 权限（完整API访问）")

print(f"\n📝 创建/更新Token的步骤:")
print(f"   1. 访问: {gitlab_url}/-/user_settings/personal_access_tokens")
print(f"   2. 创建新的Personal Access Token或编辑现有token")
print(f"   3. 确保勾选以下scopes:")
print(f"      - ✅ api (完整API访问)")
print(f"      - ✅ read_api (读取API)")
print(f"      - ✅ read_package_registry (读取package注册表)")
print(f"   4. 保存token并更新配置文件")

print(f"\n🔍 当前Token类型:")
print(f"   从用户名 'project_1_bot_...' 可以看出，这是一个Project Access Token")
print(f"   Project Access Token的权限由项目管理员设置")
print(f"   如果权限不足，需要联系项目管理员增加权限")

print(f"\n💡 替代方案:")
print(f"   如果是PyPI package，可以尝试使用pip安装:")
print(f"   pip install --index-url {gitlab_url}/api/v4/projects/9/packages/pypi/simple web-zc-liuyan==0.4+heils.main.55d9bf50")
