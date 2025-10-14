#!/bin/bash
# -*- coding: utf-8 -*-
# 服务状态检查脚本
# 检查WPS上传API服务、GitLab同步服务和网络配置状态

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

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

log_header() {
    echo -e "${PURPLE}[HEADER]${NC} $1"
}

log_detail() {
    echo -e "${CYAN}[DETAIL]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "命令 '$1' 未找到，请先安装"
        return 1
    fi
    return 0
}

# 获取服务器公网IP
get_public_ip() {
    local ip=""
    # 尝试多种方法获取公网IP
    if command -v curl &> /dev/null; then
        ip=$(curl -s --connect-timeout 5 http://ipinfo.io/ip 2>/dev/null || curl -s --connect-timeout 5 http://ifconfig.me 2>/dev/null || curl -s --connect-timeout 5 http://icanhazip.com 2>/dev/null)
    fi

    if [ -z "$ip" ] && command -v wget &> /dev/null; then
        ip=$(wget -qO- --timeout=5 http://ipinfo.io/ip 2>/dev/null || wget -qO- --timeout=5 http://ifconfig.me 2>/dev/null)
    fi

    if [ -z "$ip" ]; then
        ip="无法获取"
    fi

    echo "$ip"
}

# 检查WPS上传API服务
check_wps_api_service() {
    log_header "=== 检查WPS数据上传API服务 ==="

    local service_running=false
    local port_listening=false
    local health_check_ok=false
    local external_access_ok=false

    # 1. 检查进程是否运行
    log_info "检查WPS API服务进程..."
    if pgrep -f "wps_upload_api.py" > /dev/null; then
        local pid=$(pgrep -f "wps_upload_api.py")
        log_success "WPS API服务正在运行 (PID: $pid)"
        service_running=true
    else
        log_error "WPS API服务未运行"
    fi

    # 2. 检查端口80监听状态
    log_info "检查端口80监听状态..."
    if command -v ss &> /dev/null; then
        if ss -tlnp | grep -q ":80 "; then
            log_success "端口80正在监听"
            port_listening=true
            log_detail "端口80监听详情:"
            ss -tlnp | grep ":80 " | while read line; do
                log_detail "  $line"
            done
        else
            log_error "端口80未监听"
        fi
    elif command -v netstat &> /dev/null; then
        if netstat -tlnp | grep -q ":80 "; then
            log_success "端口80正在监听"
            port_listening=true
            log_detail "端口80监听详情:"
            netstat -tlnp | grep ":80 " | while read line; do
                log_detail "  $line"
            done
        else
            log_error "端口80未监听"
        fi
    else
        log_warning "无法检查端口状态 (ss和netstat都不可用)"
    fi

    # 3. 测试本地健康检查
    log_info "测试本地健康检查..."
    if command -v curl &> /dev/null; then
        local health_response=$(curl -s --connect-timeout 5 http://localhost/ 2>/dev/null || echo "")
        if [ -n "$health_response" ] && echo "$health_response" | grep -q "success"; then
            log_success "本地健康检查通过"
            health_check_ok=true
            log_detail "健康检查响应: $health_response"
        else
            log_error "本地健康检查失败"
            if [ -n "$health_response" ]; then
                log_detail "响应内容: $health_response"
            fi
        fi
    else
        log_warning "curl不可用，跳过健康检查测试"
    fi

    # 4. 测试外部访问
    log_info "测试外部访问能力..."
    local public_ip=$(get_public_ip)
    if [ "$public_ip" != "无法获取" ] && command -v curl &> /dev/null; then
        local external_response=$(curl -s --connect-timeout 5 "http://$public_ip/" 2>/dev/null || echo "")
        if [ -n "$external_response" ] && echo "$external_response" | grep -q "success"; then
            log_success "外部访问测试通过"
            external_access_ok=true
        else
            log_warning "外部访问测试失败 (可能被防火墙阻止)"
        fi
    else
        log_warning "无法测试外部访问 (公网IP获取失败或curl不可用)"
    fi

    # 5. 显示服务器信息
    log_info "服务器信息:"
    log_detail "公网IP: $public_ip"
    log_detail "本地访问: http://localhost/"
    log_detail "外部访问: http://$public_ip/"

    # 6. 总结WPS API服务状态
    echo ""
    log_header "WPS API服务状态总结:"
    if [ "$service_running" = true ] && [ "$port_listening" = true ] && [ "$health_check_ok" = true ]; then
        log_success "✅ WPS API服务运行正常，可以接收其他电脑的上传请求"
        if [ "$external_access_ok" = true ]; then
            log_success "✅ 外部访问正常，其他电脑可以连接"
        else
            log_warning "⚠️ 外部访问可能受限，请检查防火墙设置"
        fi
    else
        log_error "❌ WPS API服务存在问题"
        echo ""
        log_info "启动命令:"
        log_detail "cd $PROJECT_ROOT && python3 wps_upload_api.py"
    fi

    echo ""
}

# 检查GitLab同步服务
check_gitlab_sync_service() {
    log_header "=== 检查GitLab同步服务 ==="

    local service_running=false
    local log_file_exists=false
    local log_recent=false

    # 1. 检查进程是否运行
    log_info "检查GitLab同步服务进程..."
    if pgrep -f "optimized_auto_sync.py" > /dev/null; then
        local pid=$(pgrep -f "optimized_auto_sync.py")
        log_success "GitLab同步服务正在运行 (PID: $pid)"
        service_running=true

        # 显示进程详细信息
        log_detail "进程详细信息:"
        ps aux | grep "optimized_auto_sync.py" | grep -v grep | while read line; do
            log_detail "  $line"
        done
    else
        log_error "GitLab同步服务未运行"
    fi

    # 2. 检查日志文件
    log_info "检查同步服务日志..."
    local log_file="$PROJECT_ROOT/logs/optimized_sync.log"
    if [ -f "$log_file" ]; then
        log_success "日志文件存在: $log_file"
        log_file_exists=true

        # 检查日志文件大小和最后修改时间
        local file_size=$(du -h "$log_file" | cut -f1)
        local last_modified=$(stat -c %y "$log_file" 2>/dev/null || stat -f %Sm "$log_file" 2>/dev/null || echo "未知")
        log_detail "日志文件大小: $file_size"
        log_detail "最后修改时间: $last_modified"

        # 检查最近是否有活动（最近5分钟）
        if [ -f "$log_file" ]; then
            local recent_activity=$(find "$log_file" -mmin -5 2>/dev/null | wc -l)
            if [ "$recent_activity" -gt 0 ]; then
                log_success "最近5分钟内有活动"
                log_recent=true
            else
                log_warning "最近5分钟内无活动"
            fi
        fi

        # 显示最后几行日志
        log_detail "最近日志内容:"
        tail -5 "$log_file" | while read line; do
            log_detail "  $line"
        done
    else
        log_error "日志文件不存在: $log_file"
    fi

    # 3. 检查数据库连接状态
    log_info "检查数据库连接..."
    cd "$PROJECT_ROOT"
    if python3 -c "
import sys
sys.path.append('$PROJECT_ROOT')
try:
    from gitlab_tools.core.database_manager import DatabaseManager
    db_manager = DatabaseManager()
    result = db_manager.execute_query('SELECT COUNT(*) as count FROM issues')
    if result:
        print('✅ 数据库连接正常')
        print(f'📊 当前议题总数: {result[0][\"count\"]}')
    else:
        print('❌ 数据库查询失败')
except Exception as e:
    print(f'❌ 数据库连接失败: {e}')
" 2>/dev/null; then
        log_success "数据库连接正常"
    else
        log_error "数据库连接失败"
    fi

    # 4. 总结GitLab同步服务状态
    echo ""
    log_header "GitLab同步服务状态总结:"
    if [ "$service_running" = true ] && [ "$log_file_exists" = true ]; then
        log_success "✅ GitLab同步服务运行正常"
        if [ "$log_recent" = true ]; then
            log_success "✅ 服务活跃，正在处理同步任务"
        else
            log_warning "⚠️ 服务运行但最近无活动，可能没有新的同步任务"
        fi
    else
        log_error "❌ GitLab同步服务存在问题"
        echo ""
        log_info "启动命令:"
        log_detail "cd $PROJECT_ROOT && ./gitlab_tools/manage_optimized_service.sh start"
        log_detail "或手动启动: python3 gitlab_tools/scripts/optimized_auto_sync.py continuous --interval 30"
    fi

    echo ""
}

# 检查网络和防火墙配置
check_network_firewall() {
    log_header "=== 检查网络和防火墙配置 ==="

    # 1. 检查端口监听状态
    log_info "检查所有端口监听状态..."
    if command -v ss &> /dev/null; then
        log_detail "端口监听详情 (ss):"
        ss -tlnp | grep -E ":(80|443|22|3306)" | while read line; do
            log_detail "  $line"
        done
    elif command -v netstat &> /dev/null; then
        log_detail "端口监听详情 (netstat):"
        netstat -tlnp | grep -E ":(80|443|22|3306)" | while read line; do
            log_detail "  $line"
        done
    fi

    # 2. 检查防火墙状态
    log_info "检查防火墙状态..."

    # 检查iptables
    if command -v iptables &> /dev/null; then
        log_detail "iptables状态:"
        if iptables -L INPUT | grep -q "ACCEPT.*tcp.*dpt:80"; then
            log_success "iptables允许端口80访问"
        else
            log_warning "iptables可能阻止端口80访问"
        fi

        # 显示相关规则
        iptables -L INPUT | grep -E "(80|ACCEPT|DROP)" | while read line; do
            log_detail "  $line"
        done
    fi

    # 检查firewalld
    if command -v firewall-cmd &> /dev/null; then
        log_detail "firewalld状态:"
        if firewall-cmd --state &> /dev/null; then
            log_info "firewalld正在运行"
            if firewall-cmd --query-port=80/tcp &> /dev/null; then
                log_success "firewalld允许端口80访问"
            else
                log_warning "firewalld可能阻止端口80访问"
            fi
        else
            log_info "firewalld未运行"
        fi
    fi

    # 3. 检查网络接口
    log_info "检查网络接口..."
    if command -v ip &> /dev/null; then
        log_detail "网络接口信息:"
        ip addr show | grep -E "(inet |UP|DOWN)" | while read line; do
            log_detail "  $line"
        done
    elif command -v ifconfig &> /dev/null; then
        log_detail "网络接口信息:"
        ifconfig | grep -E "(inet |UP|DOWN)" | while read line; do
            log_detail "  $line"
        done
    fi

    # 4. 测试网络连通性
    log_info "测试网络连通性..."
    if command -v ping &> /dev/null; then
        log_detail "测试网络连通性:"
        if ping -c 1 8.8.8.8 &> /dev/null; then
            log_success "外网连通性正常"
        else
            log_warning "外网连通性异常"
        fi

        if ping -c 1 114.55.118.105 &> /dev/null; then
            log_success "服务器IP连通性正常"
        else
            log_warning "服务器IP连通性异常"
        fi
    fi

    echo ""
}

# 显示系统信息
show_system_info() {
    log_header "=== 系统信息 ==="

    log_info "操作系统信息:"
    if [ -f /etc/os-release ]; then
        log_detail "  $(cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"')"
    fi

    log_info "内核版本:"
    log_detail "  $(uname -r)"

    log_info "系统负载:"
    log_detail "  $(uptime)"

    log_info "内存使用:"
    if command -v free &> /dev/null; then
        free -h | while read line; do
            log_detail "  $line"
        done
    fi

    log_info "磁盘使用:"
    if command -v df &> /dev/null; then
        df -h | grep -E "(/$|/root)" | while read line; do
            log_detail "  $line"
        done
    fi

    echo ""
}

# 显示服务管理命令
show_management_commands() {
    log_header "=== 服务管理命令 ==="

    log_info "WPS API服务管理:"
    log_detail "启动: cd $PROJECT_ROOT && python3 wps_upload_api.py"
    log_detail "停止: pkill -f wps_upload_api.py"
    log_detail "重启: pkill -f wps_upload_api.py && sleep 2 && cd $PROJECT_ROOT && python3 wps_upload_api.py"

    log_info "GitLab同步服务管理:"
    log_detail "启动: cd $PROJECT_ROOT && ./gitlab_tools/manage_optimized_service.sh start"
    log_detail "停止: cd $PROJECT_ROOT && ./gitlab_tools/manage_optimized_service.sh stop"
    log_detail "重启: cd $PROJECT_ROOT && ./gitlab_tools/manage_optimized_service.sh restart"
    log_detail "状态: cd $PROJECT_ROOT && ./gitlab_tools/manage_optimized_service.sh status"
    log_detail "日志: cd $PROJECT_ROOT && ./gitlab_tools/manage_optimized_service.sh logs"

    log_info "防火墙管理:"
    log_detail "开放端口80: iptables -A INPUT -p tcp --dport 80 -j ACCEPT"
    log_detail "或使用firewalld: firewall-cmd --permanent --add-port=80/tcp && firewall-cmd --reload"

    echo ""
}

# 主函数
main() {
    echo "=========================================="
    echo "🔍 服务状态检查工具"
    echo "检查WPS上传API和GitLab同步服务状态"
    echo "=========================================="
    echo ""

    # 检查必要的命令
    local missing_commands=()
    for cmd in pgrep ps curl ss netstat; do
        if ! check_command "$cmd"; then
            missing_commands+=("$cmd")
        fi
    done

    if [ ${#missing_commands[@]} -gt 0 ]; then
        log_warning "缺少以下命令: ${missing_commands[*]}"
        log_info "建议安装: yum install -y procps-ng curl iproute2 net-tools"
        echo ""
    fi

    # 执行各项检查
    check_wps_api_service
    check_gitlab_sync_service
    check_network_firewall
    show_system_info
    show_management_commands

    echo "=========================================="
    log_success "检查完成！"
    echo "=========================================="
}

# 执行主函数
main "$@"
