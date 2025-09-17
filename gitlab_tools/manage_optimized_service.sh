#!/bin/bash
# -*- coding: utf-8 -*-
"""
优化版GitLab同步服务管理脚本
"""

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python环境
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "未找到Python3，请先安装Python3"
        exit 1
    fi
    log_success "Python3环境检查通过"
}

# 检查依赖
check_dependencies() {
    log_info "检查Python依赖..."
    python3 -c "import keyring, cryptography, mysql.connector" 2>/dev/null || {
        log_warning "缺少必要的Python包，正在安装..."
        pip3 install keyring cryptography mysql-connector-python
    }
    log_success "Python依赖检查通过"
}

# 检查数据库连接
check_database() {
    log_info "检查数据库连接..."
    cd "$PROJECT_ROOT"
    if     python3 -c "
import sys
sys.path.append('$PROJECT_ROOT')
from gitlab_tools.utils.database_config import DatabaseConfig
db_config = DatabaseConfig()
if db_config.test_connection('issue'):
    print('✅ 数据库连接正常')
else:
    print('❌ 数据库连接失败')
    sys.exit(1)
" 2>/dev/null; then
        log_success "数据库连接正常"
    else
        log_error "数据库连接失败，请检查配置"
        exit 1
    fi
}

# 启动服务
start_service() {
    log_info "启动优化版GitLab同步服务..."

    # 检查是否已经在运行
    if pgrep -f "optimized_auto_sync.py" > /dev/null; then
        log_warning "服务已在运行中"
        return 0
    fi

    # 启动服务
    cd "$PROJECT_ROOT"
    nohup python3 gitlab_tools/scripts/optimized_auto_sync.py continuous --interval 30 > logs/optimized_sync.log 2>&1 &

    sleep 2

    if pgrep -f "optimized_auto_sync.py" > /dev/null; then
        log_success "服务启动成功"
        log_info "PID: $(pgrep -f 'optimized_auto_sync.py')"
        log_info "日志文件: logs/optimized_sync.log"
    else
        log_error "服务启动失败"
        exit 1
    fi
}

# 停止服务
stop_service() {
    log_info "停止优化版GitLab同步服务..."

    if pgrep -f "optimized_auto_sync.py" > /dev/null; then
        pkill -f "optimized_auto_sync.py"
        sleep 2

        if ! pgrep -f "optimized_auto_sync.py" > /dev/null; then
            log_success "服务已停止"
        else
            log_error "服务停止失败"
            exit 1
        fi
    else
        log_warning "服务未运行"
    fi
}

# 重启服务
restart_service() {
    log_info "重启优化版GitLab同步服务..."
    stop_service
    sleep 1
    start_service
}

# 查看服务状态
status_service() {
    log_info "查看服务状态..."

    if pgrep -f "optimized_auto_sync.py" > /dev/null; then
        log_success "服务正在运行"
        log_info "PID: $(pgrep -f 'optimized_auto_sync.py')"

        # 显示系统状态
        cd "$PROJECT_ROOT"
        python3 gitlab_tools/scripts/optimized_auto_sync.py status
    else
        log_warning "服务未运行"
    fi
}

# 查看日志
view_logs() {
    log_info "查看服务日志..."

    if [ -f "logs/optimized_sync.log" ]; then
        tail -f logs/optimized_sync.log
    else
        log_warning "日志文件不存在"
    fi
}

# 测试功能
test_service() {
    log_info "测试服务功能..."

    cd "$PROJECT_ROOT"

    # 运行测试脚本
    if python3 test_optimized_system.py; then
        log_success "功能测试通过"
    else
        log_error "功能测试失败"
        exit 1
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    cd "$PROJECT_ROOT"
    python3 gitlab_tools/main.py health-check
}

# 系统监控
monitor_system() {
    log_info "执行系统监控..."

    cd "$PROJECT_ROOT"
    python3 gitlab_tools/main.py monitor
}

# 清理数据
cleanup_data() {
    log_info "清理系统数据..."

    cd "$PROJECT_ROOT"
    python3 gitlab_tools/scripts/optimized_auto_sync.py cleanup --days 30

    log_success "数据清理完成"
}

# 显示帮助
show_help() {
    echo "优化版GitLab同步服务管理脚本"
    echo ""
    echo "用法: $0 {command}"
    echo ""
    echo "命令:"
    echo "  start      - 启动服务"
    echo "  stop       - 停止服务"
    echo "  restart    - 重启服务"
    echo "  status     - 查看服务状态"
    echo "  logs       - 查看服务日志"
    echo "  test       - 测试服务功能"
    echo "  health     - 健康检查"
    echo "  monitor    - 系统监控"
    echo "  cleanup    - 清理数据"
    echo "  check      - 检查环境"
    echo "  help       - 显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 start    # 启动服务"
    echo "  $0 status   # 查看状态"
    echo "  $0 logs     # 查看日志"
}

# 主函数
main() {
    case "$1" in
        start)
            check_python
            check_dependencies
            check_database
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            check_python
            check_dependencies
            check_database
            restart_service
            ;;
        status)
            status_service
            ;;
        logs)
            view_logs
            ;;
        test)
            check_python
            check_dependencies
            check_database
            test_service
            ;;
        health)
            check_python
            check_dependencies
            check_database
            health_check
            ;;
        monitor)
            check_python
            check_dependencies
            check_database
            monitor_system
            ;;
        cleanup)
            check_python
            check_dependencies
            check_database
            cleanup_data
            ;;
        check)
            check_python
            check_dependencies
            check_database
            log_success "环境检查完成"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
