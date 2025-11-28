# GitLab Package 文件下载指南

## 概述

本指南介绍如何从自建GitLab实例下载Package文件。经过测试验证，对于自建GitLab，需要使用Web界面URL格式而不是标准API端点。

## 快速开始

### 下载Package文件

```bash
# 基本用法
python3 scripts/get_gitlab_packages.py <project_path> download <package_id> <file_id> [save_path]

# 示例
python3 scripts/get_gitlab_packages.py aoi-public/aoi-smartvision download 6739 52166
```

### 列出Package文件

```bash
# 列出指定package的所有文件
python3 scripts/get_gitlab_packages.py <project_path> list-files <package_id>

# 示例
python3 scripts/get_gitlab_packages.py aoi-public/aoi-smartvision list-files 6739
```

### 列出所有Packages

```bash
# 列出项目的所有packages
python3 scripts/get_gitlab_packages.py <project_path> list
```

## 工作原理

### 已验证成功的方案

对于自建GitLab，脚本使用**Web界面URL格式**下载文件：

```
https://<gitlab_url>/<project_path>/-/package_files/<file_id>/download
```

例如：
```
https://dev.heils.cn/aoi-public/aoi-smartvision/-/package_files/52166/download
```

### 为什么不用API端点？

标准的GitLab API端点格式：
```
/api/v4/projects/<project_id>/packages/<package_id>/package_files/<file_id>/download
```

在自建GitLab中可能返回404错误，即使token权限正确。这是因为：
1. 自建GitLab版本可能较旧，API端点支持不完整
2. Web界面URL格式更通用，适用于所有GitLab版本
3. 浏览器中能正常下载的URL，脚本也能使用

## Token权限要求

### 必需的Scopes

确保你的token有以下权限：

1. **`read_api`** ✅ **必需**
   - 基础API访问权限
   - 允许通过API读取项目信息

2. **`read_package_registry`** ✅ **必需**
   - 读取Package Registry的权限
   - 允许读取package信息和文件列表
   - 允许下载package文件

### 检查Token权限

运行以下命令检查当前token的权限：

```bash
python3 scripts/check_token_scopes.py
```

### 创建/更新Token

1. 访问：`https://<gitlab_url>/-/user_settings/personal_access_tokens`
2. 创建新的Personal Access Token
3. 确保勾选以下scopes：
   - ✅ `api`（完整API访问，推荐）
   - ✅ `read_api`（读取API）
   - ✅ `read_package_registry`（读取package注册表）
4. 保存token并更新配置文件 `config/wps_gitlab_config.json`

## 配置文件

Token配置在 `config/wps_gitlab_config.json` 中：

```json
{
  "gitlab": {
    "url": "https://dev.heils.cn",
    "token": "glpat-xxxxxxxxxxxxx",
    "project_id": "1",
    "project_path": "aoi/aoi-demo-r"
  }
}
```

## 功能特性

### 1. 自动文件名解析

脚本会自动从HTTP响应头中解析文件名，支持：
- 标准格式：`filename="web_zc_liuyan-0.4+heils.main.55d9bf50-py3-none-any.whl"`
- RFC 5987格式：`filename*=UTF-8''web_zc_liuyan-0.4+heils.main.55d9bf50-py3-none-any.whl`

如果无法从响应头获取，会使用package文件列表中的文件名。

### 2. 下载进度显示

下载大文件时会显示进度：
```
   已下载: 1.46 MB
```

### 3. 文件保存位置

- 如果指定了 `save_path`，文件保存到指定路径
- 如果未指定，文件保存到项目根目录（`/root/update_issue/`）

### 4. 错误处理

脚本会提供详细的错误信息：
- **401错误**：Token无效或已过期
- **403错误**：Token权限不足
- **404错误**：文件不存在或URL不正确

## 使用示例

### 示例1：下载PyPI Package文件

```bash
# 1. 先列出package的文件，找到file_id
python3 scripts/get_gitlab_packages.py aoi-public/aoi-smartvision list-files 6739

# 输出：
# 找到 1 个文件:
# 1. File ID: 52166
#    文件名: web_zc_liuyan-0.4+heils.main.55d9bf50-py3-none-any.whl
#    大小: 1536198

# 2. 使用file_id下载
python3 scripts/get_gitlab_packages.py aoi-public/aoi-smartvision download 6739 52166

# 输出：
# ✅ 文件已下载: /root/update_issue/web_zc_liuyan-0.4+heils.main.55d9bf50-py3-none-any.whl
#    文件大小: 1,536,198 字节 (1.47 MB)
```

### 示例2：下载到指定目录

```bash
python3 scripts/get_gitlab_packages.py aoi-public/aoi-smartvision download 6739 52166 /tmp/my_file.whl
```

### 示例3：查找并下载文件

```bash
# 如果只知道file_id，不知道package_id
python3 scripts/get_gitlab_packages.py aoi-public/aoi-smartvision download-file 52166
```

## 故障排除

### 问题1：404错误

**症状**：下载时返回404错误

**可能原因**：
1. Token权限不足
2. 项目路径不正确
3. file_id不存在

**解决方案**：
1. 检查token是否有 `read_package_registry` 权限
2. 使用 `list-files` 命令确认file_id是否正确
3. 确认项目路径格式正确（例如：`aoi-public/aoi-smartvision`）

### 问题2：403错误

**症状**：下载时返回403错误

**可能原因**：Token权限不足

**解决方案**：
1. 检查token的scopes
2. 创建新的token，确保勾选 `read_package_registry`
3. 更新配置文件中的token

### 问题3：文件大小不正确

**症状**：下载的文件大小与预期不符

**可能原因**：下载中断或网络问题

**解决方案**：
1. 重新运行下载命令
2. 检查网络连接
3. 检查磁盘空间

## 相关脚本

- `scripts/get_gitlab_packages.py` - 主下载脚本
- `scripts/check_package_info.py` - 检查package信息和token权限
- `scripts/check_token_scopes.py` - 检查token权限范围

## 技术细节

### URL格式

脚本使用以下URL格式（已验证成功）：

```
https://<gitlab_url>/<project_path>/-/package_files/<file_id>/download
```

其中：
- `<gitlab_url>`: GitLab服务器地址（例如：`https://dev.heils.cn`）
- `<project_path>`: 项目路径，斜杠需要URL编码为 `%2F`（例如：`aoi-public%2Faoi-smartvision`）
- `<file_id>`: Package文件ID

### 认证方式

使用 `PRIVATE-TOKEN` header进行认证：

```python
headers = {
    'PRIVATE-TOKEN': token,
}
```

### 文件名解析

脚本按以下优先级解析文件名：

1. 从HTTP响应头的 `Content-Disposition` 中提取
2. 从package文件列表中获取
3. 使用默认格式：`package_file_{file_id}`

## 参考文档

- [GitLab Personal Access Tokens](https://docs.gitlab.com/user/profile/personal_access_tokens.html)
- [GitLab Package Registry](https://docs.gitlab.com/user/packages/package_registry/)
- [GitLab PyPI Package Registry](https://docs.gitlab.com/user/packages/pypi_repository/)

## 更新日志

### 2025-11-28
- ✅ 优化下载脚本，仅使用已验证成功的Web界面URL格式
- ✅ 改进文件名解析，支持RFC 5987格式
- ✅ 添加下载进度显示
- ✅ 删除所有失败的API端点尝试
- ✅ 优化错误处理和提示信息
