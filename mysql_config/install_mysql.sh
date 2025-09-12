#!/bin/bash

# MySQL 8.0 安装脚本
# 适用于 CentOS/RHEL/AlmaLinux 系统

echo "开始安装 MySQL 8.0..."

# 更新系统包
echo "更新系统包..."
yum update -y

# 安装 MySQL 8.0 仓库
echo "安装 MySQL 8.0 仓库..."
rpm -Uvh https://dev.mysql.com/get/mysql80-community-release-el8-1.noarch.rpm

# 安装 MySQL 服务器
echo "安装 MySQL 服务器..."
yum install -y mysql-community-server

# 启动 MySQL 服务
echo "启动 MySQL 服务..."
systemctl start mysqld
systemctl enable mysqld

# 获取临时密码
echo "获取 MySQL 临时密码..."
TEMP_PASSWORD=$(grep 'temporary password' /var/log/mysqld.log | awk '{print $NF}')
echo "临时密码: $TEMP_PASSWORD"

# 创建 MySQL 配置脚本
cat > /root/update_issue/mysql_setup.sql << EOF
-- 设置新密码
ALTER USER 'root'@'localhost' IDENTIFIED BY 'NewRootPassword123!';

-- 创建新数据库
CREATE DATABASE IF NOT EXISTS myapp_database;

-- 创建新用户
CREATE USER IF NOT EXISTS 'app_user'@'localhost' IDENTIFIED BY 'AppUserPassword123!';
CREATE USER IF NOT EXISTS 'app_user'@'%' IDENTIFIED BY 'AppUserPassword123!';

-- 授权
GRANT ALL PRIVILEGES ON myapp_database.* TO 'app_user'@'localhost';
GRANT ALL PRIVILEGES ON myapp_database.* TO 'app_user'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 显示数据库
SHOW DATABASES;
EOF

echo "MySQL 安装完成！"
echo "请使用以下命令完成初始配置："
echo "mysql -u root -p"
echo "然后输入临时密码: $TEMP_PASSWORD"
echo "执行配置脚本: source /root/update_issue/mysql_setup.sql"
