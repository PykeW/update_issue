# MySQL 服务部署指南

本项目提供了在 Linux 系统上直接安装和配置 MySQL 8.0 服务的完整解决方案。

## 文件说明

- `install_mysql.sh` - MySQL 8.0 安装脚本
- `mysql.cnf` - MySQL 配置文件
- `mysql_setup.sql` - 数据库初始化脚本
- `mysql_service.sh` - 服务管理脚本

## 快速开始

### 1. 安装 MySQL

```bash
# 给脚本执行权限
chmod +x mysql_service.sh

# 安装 MySQL
./mysql_service.sh install
```

### 2. 应用配置

```bash
# 应用 MySQL 配置
./mysql_service.sh config
```

### 3. 初始化数据库

```bash
# 查看初始化说明
./mysql_service.sh setup
```

然后按照提示使用临时密码登录 MySQL 并执行初始化脚本。

## 服务管理

```bash
# 启动服务
./mysql_service.sh start

# 停止服务
./mysql_service.sh stop

# 重启服务
./mysql_service.sh restart

# 查看状态
./mysql_service.sh status

# 查看日志
./mysql_service.sh logs

# 连接数据库
./mysql_service.sh connect
```

## 默认配置

- **Root 密码**: `NewRootPassword123!`
- **数据库名**: `myapp_database`
- **应用用户**: `app_user`
- **应用密码**: `AppUserPassword123!`
- **端口**: `3306`

## 安全建议

1. 安装完成后请立即修改默认密码
2. 根据需要调整防火墙规则
3. 定期备份数据库
4. 监控 MySQL 日志文件

## 故障排除

如果遇到问题，请检查：

1. MySQL 服务状态：`./mysql_service.sh status`
2. MySQL 日志：`./mysql_service.sh logs`
3. 系统日志：`journalctl -u mysqld`
