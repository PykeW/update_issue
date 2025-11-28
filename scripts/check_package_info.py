#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查package信息和token权限
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

project_id = 9
package_id = 6739
file_id = 52166

headers = {'PRIVATE-TOKEN': token}

print("=" * 60)
print("检查 Package 信息和 Token 权限")
print("=" * 60)
print(f"GitLab URL: {gitlab_url}")
print(f"项目ID: {project_id}")
print(f"Package ID: {package_id}")
print(f"File ID: {file_id}")
print()

# 1. 检查token权限 - 获取当前用户信息
print("1️⃣ 检查Token权限...")
try:
    user_url = f"{gitlab_url}/api/v4/user"
    req = urllib.request.Request(user_url)
    for k, v in headers.items():
        req.add_header(k, v)

    with urllib.request.urlopen(req, timeout=30) as resp:
        user_info = json.loads(resp.read().decode('utf-8'))
        print(f"✅ Token有效，用户: {user_info.get('username', 'N/A')}")
        print(f"   用户ID: {user_info.get('id', 'N/A')}")
except Exception as e:
    print(f"❌ Token无效或权限不足: {e}")
    exit(1)

# 2. 获取package详细信息
print(f"\n2️⃣ 获取Package {package_id} 详细信息...")
package_url = f"{gitlab_url}/api/v4/projects/{project_id}/packages/{package_id}"

try:
    req = urllib.request.Request(package_url)
    for k, v in headers.items():
        req.add_header(k, v)

    with urllib.request.urlopen(req, timeout=30) as resp:
        package_info = json.loads(resp.read().decode('utf-8'))
        print(f"✅ Package信息:")
        print(f"   ID: {package_info.get('id')}")
        print(f"   名称: {package_info.get('name', 'N/A')}")
        print(f"   版本: {package_info.get('version', 'N/A')}")
        print(f"   类型: {package_info.get('package_type', 'N/A')}")
        print(f"   状态: {package_info.get('status', 'N/A')}")
        print(f"   创建时间: {package_info.get('created_at', 'N/A')}")
        package_type = package_info.get('package_type', '')
except urllib.error.HTTPError as e:
    print(f"❌ 获取package信息失败: HTTP {e.code}")
    try:
        error_body = e.read().decode('utf-8')
        print(f"错误详情: {error_body}")
        if e.code == 404:
            print("💡 提示: Package不存在或token没有访问权限")
        elif e.code == 403:
            print("💡 提示: Token权限不足，需要read_package_registry权限")
    except Exception:
        pass
    exit(1)
except Exception as e:
    print(f"❌ 异常: {e}")
    exit(1)

# 3. 获取文件列表
print(f"\n3️⃣ 获取Package文件列表...")
files_url = f"{gitlab_url}/api/v4/projects/{project_id}/packages/{package_id}/package_files"

try:
    req = urllib.request.Request(files_url)
    for k, v in headers.items():
        req.add_header(k, v)

    with urllib.request.urlopen(req, timeout=30) as resp:
        files = json.loads(resp.read().decode('utf-8'))
        print(f"✅ 找到 {len(files)} 个文件:")
        for f in files:
            print(f"   File ID: {f.get('id')}, 文件名: {f.get('file_name', 'N/A')}")

        target_file = [f for f in files if f.get('id') == file_id]
        if not target_file:
            print(f"\n❌ 未找到file_id={file_id}")
            exit(1)

        file_info = target_file[0]
        print(f"\n✅ 目标文件:")
        print(f"   File ID: {file_info.get('id')}")
        print(f"   文件名: {file_info.get('file_name')}")
        print(f"   大小: {file_info.get('size', 'N/A')} 字节")

except urllib.error.HTTPError as e:
    print(f"❌ 获取文件列表失败: HTTP {e.code}")
    if e.code == 403:
        print("💡 提示: Token权限不足，需要read_package_registry权限")
    try:
        error_body = e.read().decode('utf-8')
        print(f"错误详情: {error_body}")
    except Exception:
        pass
    exit(1)

# 4. 尝试不同的下载方式
print(f"\n4️⃣ 尝试下载文件...")

# 方式1: 标准API端点
download_url1 = f"{gitlab_url}/api/v4/projects/{project_id}/packages/{package_id}/package_files/{file_id}/download"
print(f"   方式1: {download_url1}")

try:
    req = urllib.request.Request(download_url1)
    for k, v in headers.items():
        req.add_header(k, v)

    with urllib.request.urlopen(req, timeout=10) as resp:
        print(f"   ✅ 方式1成功！可以下载")
        exit(0)
except urllib.error.HTTPError as e:
    print(f"   ❌ 方式1失败: HTTP {e.code}")
    if e.code == 404:
        print(f"   💡 404错误可能原因:")
        print(f"      1. Token权限不足（需要read_package_registry）")
        print(f"      2. Package类型特殊，需要不同的下载方式")
        print(f"      3. GitLab版本问题")
    elif e.code == 403:
        print(f"   💡 403错误: Token权限不足")
    try:
        error_body = e.read().decode('utf-8')
        print(f"   错误详情: {error_body}")
    except Exception:
        pass

# 如果是pypi类型的package，尝试不同的端点
if package_type == 'pypi':
    print(f"\n   方式2: PyPI类型package，尝试alternative端点...")
    # PyPI packages可能需要通过不同的方式下载
    alt_url = f"{gitlab_url}/api/v4/projects/{project_id}/packages/pypi/files/{file_id}/download"
    print(f"   URL: {alt_url}")
    try:
        req = urllib.request.Request(alt_url)
        for k, v in headers.items():
            req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"   ✅ 方式2成功！")
            exit(0)
    except Exception as e:
        print(f"   ❌ 方式2失败: {e}")

print(f"\n💡 建议:")
print(f"   1. 检查token是否有read_package_registry权限")
print(f"   2. 在GitLab中创建新的Personal Access Token，确保勾选read_package_registry scope")
print(f"   3. 如果是PyPI package，可能需要通过pip install方式下载")
