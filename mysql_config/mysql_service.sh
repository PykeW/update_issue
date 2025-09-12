#!/bin/bash

# MySQL 服务管理脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo "MySQL 服务管理脚本"
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  install    安装 MySQL 8.0"
    echo "  start      启动 MySQL 服务"
    echo "  stop       停止 MySQL 服务"
    echo "  restart    重启 MySQL 服务"
    echo "  status     查看 MySQL 服务状态"
    echo "  config     应用 MySQL 配置"
    echo "  setup      初始化数据库和用户"
    echo "  connect    连接到 MySQL"
    echo "  logs       查看 MySQL 日志"
    echo "  help       显示此帮助信息"
}

# 安装 MySQL
install_mysql() {
    echo -e "${GREEN}开始安装 MySQL 8.0...${NC}"
    chmod +x /root/update_issue/install_mysql.sh
    /root/update_issue/install_mysql.sh
}

# 启动服务
start_service() {
    echo -e "${GREEN}启动 MySQL 服务...${NC}"
    systemctl start mysqld
    systemctl enable mysqld
    echo -e "${GREEN}MySQL 服务已启动${NC}"
}

# 停止服务
stop_service() {
    echo -e "${YELLOW}停止 MySQL 服务...${NC}"
    systemctl stop mysqld
    echo -e "${GREEN}MySQL 服务已停止${NC}"
}

# 重启服务
restart_service() {
    echo -e "${YELLOW}重启 MySQL 服务...${NC}"
    systemctl restart mysqld
    echo -e "${GREEN}MySQL 服务已重启${NC}"
}

# 查看状态
check_status() {
    echo -e "${GREEN}MySQL 服务状态:${NC}"
    systemctl status mysqld
}

# 应用配置
apply_config() {
    echo -e "${GREEN}应用 MySQL 配置...${NC}"
    cp /root/update_issue/mysql.cnf /etc/my.cnf
    systemctl restart mysqld
    echo -e "${GREEN}配置已应用${NC}"
}

# 初始化数据库
setup_database() {
    echo -e "${GREEN}初始化数据库和用户...${NC}"
    echo "请先使用临时密码登录 MySQL，然后执行以下命令："
    echo "mysql -u root -p"
    echo "source /root/update_issue/mysql_setup.sql"
}

# 连接数据库
connect_mysql() {
    echo -e "${GREEN}连接到 MySQL...${NC}"
    mysql -u root -p
}

# 查看日志
view_logs() {
    echo -e "${GREEN}MySQL 日志:${NC}"
    tail -f /var/log/mysqld.log
}

# 主程序
case "$1" in
    install)
        install_mysql
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        check_status
        ;;
    config)
        apply_config
        ;;
    setup)
        setup_database
        ;;
    connect)
        connect_mysql
        ;;
    logs)
        view_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}未知命令: $1${NC}"
        show_help
        exit 1
        ;;
esac
