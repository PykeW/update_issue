-- 更新issues表结构以支持完整的WPS表格字段
-- 备份现有数据
CREATE TABLE IF NOT EXISTS issues_backup AS SELECT * FROM issues;

-- 删除现有表
DROP TABLE IF EXISTS issues;

-- 创建新的issues表，包含完整的WPS表格字段
CREATE TABLE issues (
    id INT AUTO_INCREMENT PRIMARY KEY,
    serial_number VARCHAR(50) COMMENT '序号',
    project_name VARCHAR(255) NOT NULL COMMENT '项目名称',
    problem_category VARCHAR(100) COMMENT '问题分类',
    severity_level INT DEFAULT 0 COMMENT '严重程度',
    problem_description TEXT COMMENT '问题/需求描述',
    solution TEXT COMMENT '解决方案',
    action_priority INT DEFAULT 0 COMMENT '行动优先级',
    action_record TEXT COMMENT '行动记录',
    initiator VARCHAR(100) COMMENT '发起人',
    responsible_person VARCHAR(100) COMMENT '责任人',
    status ENUM('open', 'in_progress', 'closed', 'resolved') DEFAULT 'open' COMMENT '状态',
    start_time DATETIME COMMENT '开始时间',
    target_completion_time DATETIME COMMENT '目标完成时间',
    actual_completion_time DATETIME COMMENT '实完时间',
    remarks TEXT COMMENT '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_project_name (project_name),
    INDEX idx_problem_category (problem_category),
    INDEX idx_status (status),
    INDEX idx_responsible_person (responsible_person),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='问题清单表';

-- 插入示例数据
INSERT INTO issues (
    serial_number, project_name, problem_category, severity_level,
    problem_description, solution, action_priority, action_record,
    initiator, responsible_person, status, start_time,
    target_completion_time, actual_completion_time, remarks
) VALUES (
    '1', '管壳六面检', '机构', 2,
    '上料直线电机y轴动力线和编码器线短了', '更换更长线缆', 2, '7/29更换线缆',
    '甘伪民', '蒋盟', 'closed', '2025-07-25 00:00:00',
    NULL, '2025-07-29 00:00:00', ''
);
