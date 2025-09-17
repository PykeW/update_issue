# GitLab同步工具

## 📋 项目结构

```
gitlab_tools/
├── core/                           # 核心功能模块
│   ├── auto_sync_manager.py       # 自动化同步管理器（主要）
│   ├── database_manager.py        # 数据库操作
│   ├── gitlab_operations.py       # GitLab操作
│   └── config_manager.py          # 配置管理
├── scripts/                        # 脚本文件
│   ├── simple_auto_sync.py        # 简化版自动同步脚本
│   ├── sync_progress.py           # 进度同步脚本
│   ├── sync_issues.py             # 议题同步脚本
│   ├── process_queue.py           # 队列处理脚本
│   ├── scheduled_sync.py          # 定时同步脚本
│   └── health_check.py            # 系统健康检查
├── config/                         # 配置文件
│   ├── gitlab.env                 # GitLab环境配置
│   ├── wps_gitlab_config.json     # GitLab项目配置
│   ├── user_mapping.json          # 用户映射配置
│   ├── auto_sync_config.json      # 自动同步配置
│   └── setup_cron.sh              # 定时任务设置
├── utils/                          # 工具函数
│   └── helpers.py                 # 辅助函数
├── logs/                           # 日志文件
├── main.py                         # 主入口脚本
├── setup_automation.sh            # 自动化设置脚本
└── README.md                       # 说明文档
```

## 🚀 功能特性

### 1. 统一管理
- **单一入口**: 所有功能通过 `main.py` 统一管理
- **模块化设计**: 核心功能分离，避免代码重复
- **配置集中**: 所有配置统一管理

### 2. 自动化同步
- **实时同步**: 每5分钟处理同步队列
- **定时同步**: 每天8点和13点完整同步
- **进度同步**: 每小时同步进度更新
- **自动关闭**: 数据库状态为closed时自动关闭GitLab议题

### 3. 健康监控
- **系统检查**: 检查数据库、GitLab连接状态
- **配置验证**: 验证所有配置文件完整性
- **日志监控**: 检查日志文件状态
- **同步状态**: 监控待同步议题数量

### 4. 错误处理
- **重试机制**: 失败操作自动重试
- **错误日志**: 详细记录错误信息
- **状态跟踪**: 跟踪每个操作的状态

## 📖 使用方法

### 命令行接口

```bash
# 完整同步（推荐）
python3 main.py sync-full

# 同步新议题
python3 main.py sync-issues

# 同步进度
python3 main.py sync-progress

# 处理队列
python3 main.py sync-queue

# 健康检查
python3 main.py health-check

# 备份数据库
python3 main.py backup

# 设置自动化
python3 main.py setup
```

### 自动化设置

```bash
# 一键设置自动化同步
chmod +x setup_automation.sh
./setup_automation.sh
```

### 定时任务说明

- **08:00** - 完整同步（新议题 + 进度同步）
- **13:00** - 完整同步（新议题 + 进度同步）
- **每5分钟** - 处理同步队列（实时同步）
- **每小时** - 同步进度（保持最新）
- **02:00** - 清理旧日志（保留7天）

## ⚙️ 配置说明

### 核心配置文件

1. **gitlab.env** - GitLab连接配置
2. **wps_gitlab_config.json** - GitLab项目配置
3. **user_mapping.json** - 用户映射配置
4. **auto_sync_config.json** - 自动同步配置

### 环境要求

- Python 3.6+
- MySQL 5.7+
- GitLab API访问权限

## 📊 监控和维护

### 日志文件

- `logs/auto_sync_8am.log` - 上午8点同步日志
- `logs/auto_sync_1pm.log` - 下午1点同步日志
- `logs/auto_sync_queue.log` - 队列处理日志
- `logs/auto_sync_progress.log` - 进度同步日志

### 健康检查

```bash
# 运行健康检查
python3 main.py health-check

# 检查特定组件
python3 scripts/health_check.py
```

### 故障排除

1. **检查日志**: 查看相关日志文件
2. **运行健康检查**: 诊断系统状态
3. **检查配置**: 验证配置文件完整性
4. **重启服务**: 必要时重启相关服务

## 🔧 开发说明

### 代码结构原则

1. **单一职责**: 每个模块只负责一个功能
2. **避免重复**: 统一使用核心管理器
3. **错误处理**: 完善的异常处理机制
4. **日志记录**: 详细的操作日志

### 添加新功能

1. 在 `core/` 中添加核心功能
2. 在 `scripts/` 中添加脚本
3. 在 `main.py` 中添加命令
4. 更新配置文件

## 📝 注意事项

1. **权限要求**: 确保数据库用户有足够权限
2. **网络连接**: 确保能访问GitLab服务器
3. **定期备份**: 建议定期备份数据库
4. **监控日志**: 定期检查日志文件
5. **更新配置**: 及时更新用户映射等配置

## 🆘 常见问题

### Q: 同步失败怎么办？
A: 运行 `python3 main.py health-check` 检查系统状态

### Q: 如何查看同步状态？
A: 查看日志文件或运行健康检查

### Q: 如何添加新用户映射？
A: 编辑 `config/user_mapping.json` 文件

### Q: 如何修改同步频率？
A: 编辑 `config/auto_sync_config.json` 文件
