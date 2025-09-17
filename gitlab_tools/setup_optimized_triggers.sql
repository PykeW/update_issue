-- =====================================================
-- 优化版数据库触发器系统
-- 提供更高效的自动同步机制
-- =====================================================

-- 1. 创建变更日志表（用于跟踪数据变化）
CREATE TABLE IF NOT EXISTS issue_changes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    issue_id INT NOT NULL,
    change_type ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    INDEX idx_issue_id (issue_id),
    INDEX idx_change_type (change_type),
    INDEX idx_processed (processed),
    INDEX idx_timestamp (change_timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='议题变更日志表';

-- 2. 优化同步队列表
CREATE TABLE IF NOT EXISTS sync_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    issue_id INT NOT NULL,
    action ENUM('create', 'close', 'update', 'sync_progress') NOT NULL,
    status ENUM('pending', 'processing', 'completed', 'failed', 'retry') DEFAULT 'pending',
    priority INT DEFAULT 5 COMMENT '优先级：1-10，数字越小优先级越高',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    max_retries INT DEFAULT 3 COMMENT '最大重试次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '计划执行时间',
    processed_at TIMESTAMP NULL,
    error_message TEXT NULL,
    metadata JSON COMMENT '额外元数据',
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_scheduled_at (scheduled_at),
    INDEX idx_created_at (created_at),
    INDEX idx_issue_id (issue_id),
    INDEX idx_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='优化版同步队列表';

-- 3. 创建同步状态表（避免重复同步）
CREATE TABLE IF NOT EXISTS sync_status (
    issue_id INT PRIMARY KEY,
    gitlab_url VARCHAR(500),
    gitlab_id INT,
    last_sync_time TIMESTAMP NULL,
    sync_status ENUM('pending', 'synced', 'failed', 'outdated') DEFAULT 'pending',
    last_change_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    hash_value VARCHAR(64) COMMENT '数据哈希值，用于检测变更',
    INDEX idx_sync_status (sync_status),
    INDEX idx_last_sync_time (last_sync_time),
    INDEX idx_hash_value (hash_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='同步状态表';

-- 4. 创建同步统计表
CREATE TABLE IF NOT EXISTS sync_statistics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    action_type ENUM('create', 'update', 'close', 'sync_progress') NOT NULL,
    success_count INT DEFAULT 0,
    failure_count INT DEFAULT 0,
    retry_count INT DEFAULT 0,
    avg_processing_time DECIMAL(10,3) DEFAULT 0 COMMENT '平均处理时间（秒）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_date_action (date, action_type),
    INDEX idx_date (date),
    INDEX idx_action_type (action_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='同步统计表';

-- 5. 创建存储过程：智能队列管理
DELIMITER $$

CREATE PROCEDURE IF NOT EXISTS AddToSyncQueue(
    IN p_issue_id INT,
    IN p_action VARCHAR(20),
    IN p_priority INT,
    IN p_metadata JSON
)
BEGIN
    DECLARE existing_count INT DEFAULT 0;
    DECLARE queue_id INT;

    -- 检查是否已存在相同的待处理任务
    SELECT COUNT(*) INTO existing_count
    FROM sync_queue
    WHERE issue_id = p_issue_id
    AND action = p_action
    AND status IN ('pending', 'processing');

    -- 如果不存在，则添加到队列
    IF existing_count = 0 THEN
        INSERT INTO sync_queue (issue_id, action, priority, metadata, scheduled_at)
        VALUES (p_issue_id, p_action, p_priority, p_metadata, NOW());

        SET queue_id = LAST_INSERT_ID();

        -- 记录变更日志
        INSERT INTO issue_changes (issue_id, change_type, field_name, new_value)
        VALUES (p_issue_id, 'UPDATE', 'sync_queue', CONCAT('Added to queue: ', p_action));

        SELECT queue_id as queue_id, 'added' as result;
    ELSE
        -- 更新现有任务的优先级（如果新优先级更高）
        UPDATE sync_queue
        SET priority = LEAST(priority, p_priority),
            scheduled_at = CASE
                WHEN p_priority < priority THEN NOW()
                ELSE scheduled_at
            END
        WHERE issue_id = p_issue_id
        AND action = p_action
        AND status IN ('pending', 'processing')
        AND p_priority < priority;

        SELECT 0 as queue_id, 'updated' as result;
    END IF;
END$$

-- 6. 创建存储过程：批量处理队列
CREATE PROCEDURE IF NOT EXISTS ProcessSyncQueue(
    IN p_batch_size INT,
    IN p_max_priority INT
)
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_queue_id INT;
    DECLARE v_issue_id INT;
    DECLARE v_action VARCHAR(20);
    DECLARE v_retry_count INT;
    DECLARE v_max_retries INT;

    DECLARE queue_cursor CURSOR FOR
        SELECT id, issue_id, action, retry_count, max_retries
        FROM sync_queue
        WHERE status = 'pending'
        AND priority <= p_max_priority
        AND scheduled_at <= NOW()
        ORDER BY priority ASC, created_at ASC
        LIMIT p_batch_size;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    -- 开始事务
    START TRANSACTION;

    -- 打开游标
    OPEN queue_cursor;

    -- 处理队列
    read_loop: LOOP
        FETCH queue_cursor INTO v_queue_id, v_issue_id, v_action, v_retry_count, v_max_retries;

        IF done THEN
            LEAVE read_loop;
        END IF;

        -- 更新状态为处理中
        UPDATE sync_queue
        SET status = 'processing', processed_at = NOW()
        WHERE id = v_queue_id;

        -- 这里可以添加具体的处理逻辑
        -- 由于MySQL限制，建议使用外部脚本处理

        -- 标记为完成（实际处理结果由外部脚本更新）
        -- UPDATE sync_queue SET status = 'completed' WHERE id = v_queue_id;

    END LOOP;

    -- 关闭游标
    CLOSE queue_cursor;

    -- 提交事务
    COMMIT;

    -- 返回处理统计
    SELECT
        COUNT(*) as processed_count,
        'processing' as status
    FROM sync_queue
    WHERE status = 'processing';
END$$

-- 7. 创建存储过程：清理过期数据
CREATE PROCEDURE IF NOT EXISTS CleanupSyncData(
    IN p_days_to_keep INT
)
BEGIN
    -- 清理过期的变更日志
    DELETE FROM issue_changes
    WHERE change_timestamp < DATE_SUB(NOW(), INTERVAL p_days_to_keep DAY)
    AND processed = TRUE;

    -- 清理过期的同步队列记录
    DELETE FROM sync_queue
    WHERE status IN ('completed', 'failed')
    AND processed_at < DATE_SUB(NOW(), INTERVAL p_days_to_keep DAY);

    -- 清理过期的统计数据
    DELETE FROM sync_statistics
    WHERE date < DATE_SUB(NOW(), INTERVAL p_days_to_keep DAY);

    -- 返回清理统计
    SELECT
        'cleanup_completed' as result,
        p_days_to_keep as days_kept;
END$$

DELIMITER ;

-- 8. 创建视图：同步队列概览
CREATE OR REPLACE VIEW sync_queue_overview AS
SELECT
    sq.id,
    sq.issue_id,
    i.project_name,
    sq.action,
    sq.status,
    sq.priority,
    sq.retry_count,
    sq.max_retries,
    sq.created_at,
    sq.scheduled_at,
    sq.processed_at,
    CASE
        WHEN sq.status = 'pending' AND sq.scheduled_at <= NOW() THEN 'ready'
        WHEN sq.status = 'pending' AND sq.scheduled_at > NOW() THEN 'scheduled'
        WHEN sq.status = 'processing' THEN 'processing'
        WHEN sq.status = 'completed' THEN 'completed'
        WHEN sq.status = 'failed' THEN 'failed'
        ELSE 'unknown'
    END as queue_status,
    TIMESTAMPDIFF(SECOND, sq.created_at, COALESCE(sq.processed_at, NOW())) as processing_time_seconds
FROM sync_queue sq
LEFT JOIN issues i ON sq.issue_id = i.id
ORDER BY sq.priority ASC, sq.created_at ASC;

-- 9. 创建视图：同步统计概览
CREATE OR REPLACE VIEW sync_statistics_overview AS
SELECT
    date,
    action_type,
    success_count,
    failure_count,
    retry_count,
    avg_processing_time,
    success_count + failure_count as total_count,
    CASE
        WHEN success_count + failure_count > 0
        THEN ROUND(success_count * 100.0 / (success_count + failure_count), 2)
        ELSE 0
    END as success_rate
FROM sync_statistics
ORDER BY date DESC, action_type;

-- 10. 初始化数据
-- 为现有议题创建同步状态记录
INSERT IGNORE INTO sync_status (issue_id, gitlab_url, sync_status, hash_value)
SELECT
    id,
    COALESCE(gitlab_url, ''),
    CASE
        WHEN gitlab_url IS NOT NULL AND gitlab_url != '' THEN 'synced'
        ELSE 'pending'
    END,
    MD5(CONCAT(
        COALESCE(project_name, ''),
        COALESCE(problem_description, ''),
        COALESCE(status, ''),
        COALESCE(responsible_person, '')
    ))
FROM issues;

-- 11. 创建索引优化
-- 复合索引，提高查询性能
CREATE INDEX idx_sync_queue_status_priority ON sync_queue (status, priority, scheduled_at);
CREATE INDEX idx_sync_queue_issue_action ON sync_queue (issue_id, action, status);
CREATE INDEX idx_issue_changes_processed ON issue_changes (processed, change_timestamp);

-- 12. 示例查询语句
-- 查看待处理的同步队列
-- SELECT * FROM sync_queue_overview WHERE queue_status = 'ready';

-- 查看同步统计
-- SELECT * FROM sync_statistics_overview WHERE date >= DATE_SUB(NOW(), INTERVAL 7 DAY);

-- 查看议题变更历史
-- SELECT * FROM issue_changes WHERE issue_id = 1 ORDER BY change_timestamp DESC;

-- 手动添加同步任务
-- CALL AddToSyncQueue(1, 'create', 1, '{"reason": "manual_add"}');

-- 处理同步队列
-- CALL ProcessSyncQueue(10, 5);

-- 清理过期数据
-- CALL CleanupSyncData(30);
