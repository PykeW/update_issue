#!/bin/bash
# 自动化同步设置脚本

echo "🚀 设置GitLab自动化同步系统..."

# 设置脚本路径
SCRIPT_DIR="/root/update_issue/gitlab_tools"
AUTO_SYNC_SCRIPT="$SCRIPT_DIR/scripts/simple_auto_sync.py"
LOG_DIR="$SCRIPT_DIR/logs"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 设置脚本执行权限
chmod +x "$AUTO_SYNC_SCRIPT"

echo "📋 当前定时任务:"
crontab -l

echo ""
echo "🔧 添加新的定时任务..."

# 创建临时crontab文件
TEMP_CRON=$(mktemp)

# 保留现有的crontab
crontab -l > "$TEMP_CRON" 2>/dev/null || touch "$TEMP_CRON"

# 添加GitLab同步任务
cat >> "$TEMP_CRON" << EOF

# GitLab自动化同步任务
# 每天上午8点执行完整同步
0 8 * * * cd $SCRIPT_DIR && python3 $AUTO_SYNC_SCRIPT full >> $LOG_DIR/auto_sync_8am.log 2>&1

# 每天下午1点执行完整同步
0 13 * * * cd $SCRIPT_DIR && python3 $AUTO_SYNC_SCRIPT full >> $LOG_DIR/auto_sync_1pm.log 2>&1

# 每5分钟检查同步队列（处理实时同步）
*/5 * * * * cd $SCRIPT_DIR && python3 $AUTO_SYNC_SCRIPT queue >> $LOG_DIR/auto_sync_queue.log 2>&1

# 每小时同步进度（保持数据最新）
0 * * * * cd $SCRIPT_DIR && python3 $AUTO_SYNC_SCRIPT progress >> $LOG_DIR/auto_sync_progress.log 2>&1

# 每天凌晨2点清理旧日志（保留7天）
0 2 * * * find $LOG_DIR -name "*.log" -mtime +7 -delete

EOF

# 安装新的crontab
crontab "$TEMP_CRON"

# 清理临时文件
rm "$TEMP_CRON"

echo "✅ 定时任务设置完成！"
echo ""
echo "📋 新的定时任务:"
crontab -l

echo ""
echo "📊 定时任务说明:"
echo "  🕗 08:00 - 完整同步（新议题 + 进度同步）"
echo "  🕐 13:00 - 完整同步（新议题 + 进度同步）"
echo "  ⏰ 每5分钟 - 处理同步队列（实时同步）"
echo "  🕐 每小时 - 同步进度（保持最新）"
echo "  🧹 02:00 - 清理旧日志（保留7天）"

echo ""
echo "📁 日志文件位置:"
echo "  $LOG_DIR/auto_sync_8am.log"
echo "  $LOG_DIR/auto_sync_1pm.log"
echo "  $LOG_DIR/auto_sync_queue.log"
echo "  $LOG_DIR/auto_sync_progress.log"

echo ""
echo "🔍 查看定时任务状态:"
echo "  crontab -l"
echo ""
echo "🔍 查看日志:"
echo "  tail -f $LOG_DIR/auto_sync_8am.log"
echo "  tail -f $LOG_DIR/auto_sync_queue.log"

echo ""
echo "✅ 自动化设置完成！系统将自动运行GitLab同步。"
