#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步队列处理脚本
处理数据库中的同步队列，自动创建和关闭GitLab议题
"""

import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_manager import DatabaseManager
from core.gitlab_operations import GitLabOperations
from core.config_manager import ConfigManager
from utils.helpers import setup_logging

def process_sync_queue():
    """
    处理同步队列
    """
    # 设置日志
    setup_logging('/root/update_issue/gitlab_tools/logs/queue.log')
    logging.info("开始处理同步队列")

    try:
        # 初始化管理器
        db_manager = DatabaseManager()
        gitlab_ops = GitLabOperations()
        config_manager = ConfigManager()

        # 加载配置
        config = config_manager.load_gitlab_config()
        user_mapping_config = config_manager.load_user_mapping()
        user_mapping = user_mapping_config.get('user_mapping', {}) if user_mapping_config else {}

        if not config:
            logging.error("无法加载GitLab配置")
            return

        # 获取待处理项
        items = db_manager.get_pending_queue_items()
        if not items:
            logging.info("没有待处理的队列项")
            return

        logging.info(f"找到 {len(items)} 个待处理项")

        # 处理每个项
        success_count = 0
        for item in items:
            if process_queue_item(item, db_manager, gitlab_ops, config, user_mapping):
                success_count += 1

        logging.info(f"队列处理完成: {success_count}/{len(items)} 成功")

    except Exception as e:
        logging.error(f"队列处理异常: {e}")

def process_queue_item(item: dict, db_manager: DatabaseManager,
                      gitlab_ops: GitLabOperations, config: dict,
                      user_mapping: dict) -> bool:
    """
    处理单个队列项
    """
    queue_id = item.get('id')
    issue_id = item.get('issue_id')
    action = item.get('action')

    logging.info(f"处理队列项 {queue_id}: 议题 {issue_id}, 动作 {action}")

    try:
        # 更新状态为处理中
        if queue_id and db_manager.update_queue_status(int(queue_id), 'processing'):
            pass

        # 获取议题数据
        if issue_id:
            issue_data = db_manager.get_issue_by_id(int(issue_id))
            if not issue_data:
                logging.error(f"无法获取议题 {issue_id} 的数据")
                if queue_id:
                    db_manager.update_queue_status(int(queue_id), 'failed', '无法获取议题数据')
                return False
        else:
            logging.error("议题ID为空")
            if queue_id:
                db_manager.update_queue_status(int(queue_id), 'failed', '议题ID为空')
            return False

        if action == 'create':
            # 创建GitLab议题
            gitlab_issue = gitlab_ops.create_issue(issue_data, config, user_mapping)
            if gitlab_issue:
                gitlab_url = gitlab_issue.get('web_url', '')
                gitlab_progress = gitlab_ops.get_issue_progress(gitlab_issue)

                # 更新数据库
                if issue_id and db_manager.update_issue_gitlab_info(int(issue_id), gitlab_url, gitlab_progress):
                    logging.info(f"✅ 议题 {issue_id} 创建成功")
                    if queue_id:
                        db_manager.update_queue_status(int(queue_id), 'completed')
                    return True
                else:
                    logging.error(f"❌ 议题 {issue_id} 数据库更新失败")
                    if queue_id:
                        db_manager.update_queue_status(int(queue_id), 'failed', '数据库更新失败')
                    return False
            else:
                logging.error(f"❌ 议题 {issue_id} 创建失败")
                if queue_id:
                    db_manager.update_queue_status(int(queue_id), 'failed', 'GitLab议题创建失败')
                return False

        elif action == 'close':
            # 关闭GitLab议题
            gitlab_url = issue_data.get('gitlab_url', '')
            if not gitlab_url:
                logging.warning(f"议题 {issue_id} 没有GitLab URL，跳过关闭")
                if queue_id:
                    db_manager.update_queue_status(int(queue_id), 'completed')
                return True

            # 提取议题ID
            issue_iid = gitlab_ops.extract_issue_iid_from_url(gitlab_url)
            if not issue_iid:
                logging.error(f"无法从URL提取议题ID: {gitlab_url}")
                if queue_id:
                    db_manager.update_queue_status(int(queue_id), 'failed', '无法从URL提取议题ID')
                return False

            # 关闭议题
            if gitlab_ops.close_issue(issue_iid, issue_data):
                # 清空数据库中的进度信息
                if issue_id:
                    db_manager.update_issue_progress(int(issue_id), '')
                logging.info(f"✅ 议题 {issue_id} 关闭成功")
                if queue_id:
                    db_manager.update_queue_status(int(queue_id), 'completed')
                return True
            else:
                logging.error(f"❌ 议题 {issue_id} 关闭失败")
                if queue_id:
                    db_manager.update_queue_status(int(queue_id), 'failed', 'GitLab议题关闭失败')
                return False
        else:
            logging.error(f"未知动作: {action}")
            if queue_id:
                db_manager.update_queue_status(int(queue_id), 'failed', f'未知动作: {action}')
            return False

    except Exception as e:
        logging.error(f"处理队列项异常: {e}")
        if queue_id:
            db_manager.update_queue_status(int(queue_id), 'failed', str(e))
        return False

if __name__ == "__main__":
    process_sync_queue()
