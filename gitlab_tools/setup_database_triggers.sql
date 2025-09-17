-- 创建数据库触发器，当有新的open状态议题时自动创建GitLab议题
-- 注意：这个触发器需要在数据库中手动执行

-- 创建同步队列表（先创建表）
CREATE TABLE IF NOT EXISTS sync_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    issue_id INT NOT NULL,
    action ENUM('create', 'close', 'update') NOT NULL,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL,
    error_message TEXT NULL,
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_issue_id (issue_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='同步队列表';

-- 注意：由于权限限制，触发器功能将通过外部脚本实现
-- 建议使用定时任务（cron）定期检查新议题并同步到GitLab

-- 示例：手动添加需要同步的议题到队列
-- INSERT INTO sync_queue (issue_id, action) VALUES (1, 'create');

-- 查看待处理的同步队列
-- SELECT * FROM sync_queue WHERE status = 'pending' ORDER BY created_at;
