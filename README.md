# 议题同步系统

WPS 表格数据到 GitLab 议题的自动化同步系统。

## 🚀 快速开始

```bash
# 启动 API 服务（默认端口 80）
python main.py api start --port 80

# 查看 API 运行状态
python main.py api status

# 手动批量处理同步队列
python main.py sync manual --limit 50 --action-filter create

# 查看同步队列状态
python main.py sync status

# 运行测试
python main.py test --type all

# 健康检查
python main.py health
```

## 📋 主要功能

- ✅ WPS 数据自动上传
- ✅ GitLab 议题创建和更新
- ✅ 实时状态同步
- ✅ 队列化任务处理
- ✅ 健康检查和监控

## 📁 项目结构

```
update_issue/
├── src/           # 源代码
│   ├── api/       # API 服务层
│   ├── gitlab/    # GitLab 核心
│   └── archive/   # 历史归档（仅保留 README）
├── scripts/       # 可执行脚本（测试等）
├── config/        # 配置文件
├── docs/          # 文档与示例（含 wps_upload_script_optimized.py）
├── tests/         # 测试
└── main.py        # 命令行入口
```

## 📚 文档

- [使用指南](docs/README.md)
- [架构文档](docs/ARCHITECTURE.md)
- [历史文档](docs/archive/)

## 🛠️ 命令行工具

```bash
# API 管理
python main.py api start --port 80     # 启动服务
python main.py api status              # 查看状态

# 同步管理
python main.py sync status             # 队列状态
python main.py sync manual             # 手动同步
python main.py sync manual --limit 20  # 限制处理数量
python main.py sync manual --action-filter create|close|create_and_close

# 健康检查
python main.py health                  # 系统检查

# 测试
python main.py test --type all         # 运行测试（sync/api/all）
```

## ⚙️ 配置

编辑配置文件：
- `config/gitlab.env` - GitLab 配置
- `config/database.env` - 数据库配置
- `config/user_mapping.json` - 用户映射

## 🔧 开发

```bash
# 创建并激活虚拟环境（示例）
python -m venv venv && source venv/bin/activate
pip install -U pip
pip install -e .[dev]

# 查看帮助
python main.py --help
```

## 📝 版本

- **v2.0.0** (2025-10-20) - 代码结构重构
- **v1.0.0** (2025-09-20) - 初始版本

## 📄 许可证

版权所有 © 2025
