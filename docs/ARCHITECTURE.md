# 项目架构文档

## 1. 概述

本项目旨在提供一个高效、可靠的GitLab议题同步解决方案，支持WPS数据上传、实时同步、队列处理和系统健康监控。通过模块化设计和清晰的职责划分，确保系统易于维护、扩展和协作。

## 2. 核心组件

### 2.1. API 服务 (`src/api/wps_api.py`)
- **职责**: 接收WPS上传数据，进行数据校验、去重、插入/更新数据库。
- **同步触发**: 在数据处理完成后，立即触发GitLab同步逻辑，并将失败任务加入同步队列。
- **技术栈**: Flask

### 2.2. GitLab 核心功能 (`src/gitlab/core/`)
- **`gitlab_operations.py`**: 封装GitLab API的创建、更新、关闭议题、管理标签等操作。
- **`database_manager.py`**: 提供数据库连接管理和CRUD操作的通用接口。
- **`config_manager.py`**: 负责加载和管理GitLab、用户映射等配置。
- **`gitlab_issue_manager.py`**: GitLab议题管理工具，支持创建、修改、关闭议题。
- **`enhanced_sync_database_to_gitlab.py`**: 增强的数据库到GitLab同步功能。

### 2.3. 业务服务 (`src/gitlab/services/`)
- **`manual_sync.py`**: 手动批量同步脚本，用于处理历史遗留或特定条件的同步队列任务。
- **`health_check.py`**: 提供系统健康检查功能，验证数据库、GitLab连接和配置。
- **`log_rotation.py`**: 日志轮转服务，管理日志文件大小和保留策略。

### 2.4. 通用工具 (`src/utils/`)
- **`helpers.py`**: 包含各种辅助函数，如日志设置、数据清理等。
- **`password_manager.py`**: 安全地管理和检索敏感密码。
- **`database_config.py`**: 数据库连接配置管理。

### 2.5. 可执行脚本 (`scripts/`)
- **`wps_upload_script_optimized.py`**: 模拟WPS数据上传的客户端脚本。
- **`test_immediate_sync.py`**: 用于测试立即同步功能的脚本。
- **`activate_venv.sh`**: 激活项目虚拟环境的便捷脚本。
- **`check_services.sh`**: 服务检查脚本。

### 2.6. 统一入口 (`main.py`)
- **职责**: 提供一个统一的命令行接口，用于启动API、执行同步、运行测试和健康检查。
- **命令**: `api`, `sync`, `test`, `health`

### 2.7. 归档模块 (`src/archive/`)
- **`auto_sync_manager.py`**: 自动同步管理器（已归档，未使用）
- **`change_detector.py`**: 变更检测器（已归档，未使用）
- **`optimized_issue_creator.py`**: 优化议题创建器（已归档，未使用）
- **`progress_monitor.py`**: 进度监控器（已归档，未使用）
- **`smart_queue_processor.py`**: 智能队列处理器（已归档，未使用）

## 3. 数据流与同步机制

1. **WPS数据上传**: 客户端 (`scripts/wps_upload_script_optimized.py`) 通过HTTP POST请求将数据发送到API服务 (`src/api/wps_api.py`)。
2. **API处理**:
   - 接收数据，进行初步校验。
   - 调用 `src/gitlab/core/database_manager.py` 进行数据库操作（去重、插入/更新）。
   - **立即同步**: 如果数据状态需要同步到GitLab（例如，新创建或状态变为`closed`），则立即调用 `src/api/wps_api.py` 中的 `sync_issue_to_gitlab` 函数。
   - **队列Fallback**: 如果立即同步失败，任务会被添加到 `sync_queue` 数据库表中。
   - **队列处理**: 在API响应返回前，调用 `src/api/wps_api.py` 中的 `process_pending_sync_queue` 函数，处理当前所有待同步的队列任务。
3. **GitLab交互**: `sync_issue_to_gitlab` 函数通过 `src/gitlab/core/gitlab_operations.py` 与GitLab API进行实际交互。
4. **数据库更新**: GitLab同步成功后，数据库中的 `issues` 表的 `gitlab_url`、`sync_status` 和 `last_sync_time` 字段会被更新。
5. **手动同步**: `src/gitlab/services/manual_sync.py` 脚本可以独立运行，用于批量处理 `sync_queue` 中的任务，或针对特定议题进行同步。

## 4. 配置管理

- 所有配置文件集中在 `config/` 目录下。
- `src/gitlab/core/config_manager.py` 负责加载这些配置。
- 敏感信息（如GitLab Private Token）通过 `keyring` 和 `cryptography` 安全管理。

## 5. 部署与运行

- **虚拟环境**: 推荐使用Python虚拟环境 (`venv`) 进行依赖管理。
- **API启动**: `python main.py api start`
- **手动同步**: `python main.py sync manual`
- **健康检查**: `python main.py health`

## 6. 优势

- **实时性**: 关键同步操作在API请求处理过程中立即完成。
- **可靠性**: 失败任务自动进入队列，并通过API请求后的队列处理机制进行重试。
- **简化架构**: 移除了独立的后台轮询服务，减少了系统复杂性和资源消耗。
- **可维护性**: 清晰的模块划分和统一的入口点，便于开发和维护。
- **可扩展性**: 新功能可以轻松集成到现有模块或作为新服务添加。

## 7. 代码结构优化

### 7.1. 导入路径标准化
- 所有模块使用绝对导入路径（如 `from src.gitlab.core.database_manager import DatabaseManager`）
- 移除了相对导入和动态路径添加

### 7.2. 模块清理
- 将未使用的模块移动到 `src/archive/` 目录
- 保留核心功能模块，提高代码可维护性

### 7.3. 文件组织
- 脚本文件统一放在 `scripts/` 目录
- 配置文件集中在 `config/` 目录
- 文档统一放在 `docs/` 目录

## 8. 模块使用说明

### 8.1. 核心模块
- **DatabaseManager**: 数据库操作的核心类，所有数据库交互都通过此类
- **ConfigManager**: 配置管理类，负责加载各种配置文件
- **GitLabOperations**: GitLab API操作类，处理所有GitLab相关操作
- **GitLabIssueManager**: GitLab议题管理工具，提供议题CRUD操作

### 8.2. 服务模块
- **ManualSync**: 手动同步服务，用于批量处理同步队列
- **HealthCheck**: 健康检查服务，验证系统各组件状态
- **LogRotation**: 日志轮转服务，管理日志文件

### 8.3. 工具模块
- **PasswordManager**: 密码管理工具，安全存储和检索敏感信息
- **DatabaseConfig**: 数据库配置工具，管理数据库连接配置
- **Helpers**: 通用辅助函数集合

## 9. 开发指南

### 9.1. 添加新功能
1. 确定功能属于哪个模块（core/services/utils）
2. 使用绝对导入路径
3. 添加适当的错误处理和日志记录
4. 更新相关文档

### 9.2. 代码规范
- 使用类型提示
- 遵循PEP 8代码风格
- 添加适当的文档字符串
- 保持函数和类的职责单一

### 9.3. 测试
- 为核心功能添加单元测试
- 使用集成测试验证模块间交互
- 保持测试覆盖率在合理水平
