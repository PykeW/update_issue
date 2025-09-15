# GitLab同步工具

## 项目结构

```
gitlab_tools/
├── core/                    # 核心功能模块
│   ├── database_manager.py  # 数据库操作
│   ├── gitlab_operations.py # GitLab操作
│   └── config_manager.py    # 配置管理
├── utils/                   # 工具函数
│   └── helpers.py          # 辅助函数
├── scripts/                 # 脚本文件
│   ├── sync_progress.py    # 进度同步脚本
│   ├── sync_issues.py      # 议题同步脚本
│   ├── process_queue.py    # 队列处理脚本
│   └── scheduled_sync.py   # 定时同步脚本
├── config/                  # 配置文件
│   └── setup_cron.sh       # 定时任务设置
├── logs/                    # 日志文件
├── main.py                  # 主入口脚本
└── README.md               # 说明文档
```

## 功能说明

### 1. 自动创建议题
- 当数据库新增`status='open'`的议题时，自动创建GitLab议题
- 通过数据库触发器将任务添加到同步队列
- 队列处理脚本每分钟检查并处理队列

### 2. 定时同步进度
- 每天上午8点和下午1点执行同步
- 同步所有有GitLab URL的议题进度
- 处理状态为`closed`的议题（关闭GitLab议题并移除进度标签）

### 3. 关闭议题处理
- 当数据库`status`更新为`closed`时
- 移除GitLab议题的进度标签
- 关闭GitLab议题并更新描述
- 清空数据库中的进度信息

## 使用方法

### 命令行接口

```bash
# 同步进度
python3 main.py sync-progress

# 同步议题
python3 main.py sync-issues --limit 20

# 处理队列
python3 main.py process-queue

# 备份数据库
python3 main.py backup

# 执行前备份数据库
python3 main.py sync-progress --backup
```

### 定时任务设置

```bash
# 设置定时任务
chmod +x config/setup_cron.sh
./config/setup_cron.sh
```

### 数据库触发器设置

```bash
# 设置数据库触发器
mysql -u issue -phszc8888 issue_database < setup_database_triggers.sql
```

## 配置说明

### 环境变量
- `gitlab.env`: GitLab连接配置

### 配置文件
- `wps_gitlab_config.json`: GitLab项目配置
- `user_mapping.json`: 用户映射配置

## 日志文件

- `logs/sync.log`: 同步操作日志
- `logs/queue.log`: 队列处理日志
- `logs/cron.log`: 定时任务日志

## 注意事项

1. 确保数据库用户有足够权限
2. 定期检查日志文件
3. 建议定期备份数据库
4. 监控队列处理状态
