# 议题同步系统使用指南

## 🚀 快速开始

### 1. 环境准备

```bash
# 激活虚拟环境
source venv/bin/activate

# 或使用脚本
source scripts/activate_venv.sh
```

### 2. 配置设置

编辑配置文件：
- `config/wps_gitlab_config.json` - GitLab 配置（包含 URL、Token、项目信息、标签映射等）
- `config/database.env` - 数据库配置

### 3. 启动服务

```bash
# 启动 API 服务
python main.py api start

# 查看 API 服务状态
python main.py api status
```

## 📋 命令行工具

### API 管理

```bash
# 启动 API 服务
python main.py api start

# 在指定端口启动
python main.py api start --port 8080

# 查看服务状态
python main.py api status
```

### 同步管理

```bash
# 查看同步队列状态
python main.py sync status

# 手动批量同步
python main.py sync manual

# 指定操作类型同步
python main.py sync manual --action-filter close

# 限制处理数量
python main.py sync manual --limit 10
```

### 健康检查

```bash
# 运行系统健康检查
python main.py health
```

### 测试

```bash
# 运行所有测试
python main.py test

# 只运行同步测试
python main.py test --type sync
```

## 📁 目录说明

- `src/api/` - API 服务层
- `src/gitlab/core/` - GitLab 核心功能
- `src/gitlab/services/` - 业务服务
- `src/utils/` - 工具模块
- `scripts/` - 可执行脚本
- `config/` - 配置文件
- `docs/` - 文档
- `tests/` - 测试文件

## 🔧 常见任务

### 上传 WPS 数据

```bash
# 使用上传脚本
python scripts/wps_upload_script_optimized.py
```

### 处理积压队列

```bash
# 查看队列状态
python main.py sync status

# 批量处理待同步任务
python main.py sync manual --limit 50
```

### 查看日志

```bash
# API 日志
tail -f logs/wps_api.log

# 同步日志
tail -f logs/gitlab_sync.log
```

## 🐛 故障排查

### API 服务无法启动

1. 检查端口是否被占用
2. 验证配置文件是否正确
3. 查看错误日志

### GitLab 同步失败

1. 检查 GitLab 配置
2. 验证网络连接
3. 查看同步队列错误信息

### 数据库连接失败

1. 检查数据库服务状态
2. 验证数据库配置
3. 检查网络和权限

## 📊 监控

### 服务状态

```bash
# 检查 API 服务
python main.py api status

# 系统健康检查
python main.py health
```

### 同步状态

```bash
# 查看队列统计
python main.py sync status
```

## 🔐 安全配置

### 密码管理

系统使用 keyring 安全存储密码。首次运行时会提示输入密码。

### 权限配置

确保以下文件权限正确：
- `config/*.env` - 600 (仅所有者可读写)
- `config/*.json` - 644 (所有者可读写，组和其他人可读)

## 📝 开发指南

### 添加新 API 端点

1. 在 `src/api/wps_api.py` 中添加路由
2. 实现业务逻辑
3. 更新文档

### 添加新同步逻辑

1. 在 `src/gitlab/core/` 或 `src/gitlab/services/` 添加模块
2. 更新导入
3. 添加测试

### 运行测试

```bash
python main.py test
```

## 🔄 更新和维护

### 代码更新

```bash
git pull
pip install -r requirements.txt
```

### 数据库迁移

根据需要执行数据库架构更新脚本。

### 日志清理

系统会自动轮转日志，旧日志会被压缩或删除。

## 📚 更多资源

- [架构文档](ARCHITECTURE.md)
- [API 文档](API_GUIDE.md)
- [开发指南](../README.md)

## 🆘 获取帮助

```bash
# 查看帮助
python main.py --help

# 查看子命令帮助
python main.py sync --help
python main.py api --help
```

## 📄 许可证

版权所有 © 2025

