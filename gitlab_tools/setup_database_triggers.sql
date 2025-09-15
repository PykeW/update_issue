-- 创建数据库触发器，当有新的open状态议题时自动创建GitLab议题
-- 注意：这个触发器需要在数据库中手动执行

DELIMITER $$

-- 创建触发器：当插入新议题且状态为open时
CREATE TRIGGER trigger_create_gitlab_issue_after_insert
AFTER INSERT ON issues
FOR EACH ROW
BEGIN
    -- 只有当状态为open且没有GitLab URL时才触发
    IF NEW.status = 'open' AND (NEW.gitlab_url IS NULL OR NEW.gitlab_url = '') THEN
        -- 这里可以调用外部脚本或存储过程
        -- 由于MySQL触发器不能直接调用外部程序，建议使用事件调度器
        INSERT INTO sync_queue (issue_id, action, created_at)
        VALUES (NEW.id, 'create', NOW());
    END IF;
END$$

-- 创建触发器：当更新议题状态为closed时
CREATE TRIGGER trigger_close_gitlab_issue_after_update
AFTER UPDATE ON issues
FOR EACH ROW
BEGIN
    -- 当状态从非closed变为closed时
    IF OLD.status != 'closed' AND NEW.status = 'closed' AND NEW.gitlab_url IS NOT NULL AND NEW.gitlab_url != '' THEN
        -- 添加到同步队列
        INSERT INTO sync_queue (issue_id, action, created_at)
        VALUES (NEW.id, 'close', NOW());
    END IF;
END$$

DELIMITER ;

-- 创建同步队列表
CREATE TABLE IF NOT EXISTS sync_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    issue_id INT NOT NULL,
    action ENUM('create', 'close', 'update') NOT NULL,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL,
    error_message TEXT NULL,
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- 创建事件调度器（需要开启事件调度器）
-- SET GLOBAL event_scheduler = ON;

-- 创建事件：每分钟检查同步队列
CREATE EVENT IF NOT EXISTS event_process_sync_queue
ON SCHEDULE EVERY 1 MINUTE
DO
BEGIN
    -- 这里可以调用存储过程处理队列
    -- 由于MySQL限制，建议使用外部脚本定期处理队列
    CALL process_sync_queue();
END;

-- 创建存储过程处理同步队列
DELIMITER $$

CREATE PROCEDURE process_sync_queue()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE queue_id INT;
    DECLARE issue_id INT;
    DECLARE action_type VARCHAR(10);

    -- 声明游标
    DECLARE queue_cursor CURSOR FOR
        SELECT id, issue_id, action
        FROM sync_queue
        WHERE status = 'pending'
        ORDER BY created_at
        LIMIT 10;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    -- 打开游标
    OPEN queue_cursor;

    -- 处理队列
    read_loop: LOOP
        FETCH queue_cursor INTO queue_id, issue_id, action_type;
        IF done THEN
            LEAVE read_loop;
        END IF;

        -- 更新状态为处理中
        UPDATE sync_queue SET status = 'processing', processed_at = NOW() WHERE id = queue_id;

        -- 这里可以添加具体的处理逻辑
        -- 由于MySQL限制，建议使用外部脚本处理

        -- 标记为完成
        UPDATE sync_queue SET status = 'completed' WHERE id = queue_id;

    END LOOP;

    -- 关闭游标
    CLOSE queue_cursor;

END$$

DELIMITER ;
