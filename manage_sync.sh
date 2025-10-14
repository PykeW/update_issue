#!/bin/bash
# GitLab同步工具管理脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

case "$1" in
    start)
        echo "🚀 启动GitLab同步服务..."
        systemctl start gitlab-sync
        systemctl enable gitlab-sync
        ;;
    stop)
        echo "🛑 停止GitLab同步服务..."
        systemctl stop gitlab-sync
        ;;
    restart)
        echo "🔄 重启GitLab同步服务..."
        systemctl restart gitlab-sync
        ;;
    status)
        echo "📊 GitLab同步服务状态:"
        systemctl status gitlab-sync
        ;;
    logs)
        echo "📋 GitLab同步服务日志:"
        journalctl -u gitlab-sync -f
        ;;
    test)
        echo "🧪 测试同步功能..."
        cd "$PROJECT_ROOT"
        python3 gitlab_tools/scripts/optimized_auto_sync.py single
        ;;
    monitor)
        echo "👁️ 启动变更监控..."
        cd "$PROJECT_ROOT"
        python3 gitlab_tools/core/change_detector.py continuous --interval 10
        ;;
    queue)
        echo "⚙️ 处理同步队列..."
        cd "$PROJECT_ROOT"
        python3 gitlab_tools/scripts/optimized_auto_sync.py queue --batch-size 10
        ;;
    cleanup)
        echo "🧹 清理系统数据..."
        cd "$PROJECT_ROOT"
        python3 gitlab_tools/scripts/optimized_auto_sync.py cleanup --days 30
        ;;
    *)
        echo "GitLab同步工具管理脚本"
        echo "用法: $0 {start|stop|restart|status|logs|test|monitor|queue|cleanup}"
        echo ""
        echo "命令说明:"
        echo "  start    - 启动同步服务"
        echo "  stop     - 停止同步服务"
        echo "  restart  - 重启同步服务"
        echo "  status   - 查看服务状态"
        echo "  logs     - 查看服务日志"
        echo "  test     - 测试同步功能"
        echo "  monitor  - 启动变更监控"
        echo "  queue    - 处理同步队列"
        echo "  cleanup  - 清理系统数据"
        ;;
esac
