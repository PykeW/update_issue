#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WPS表格上传脚本 - 优化版
专门处理包含"软件"关键词的问题分类数据
在WPS环境下运行，负责数据上传到服务器
优化了日志记录和用户体验
"""

import requests
import time
from datetime import datetime
from typing import Dict, List, Any

# ==================== 配置信息 ====================
CONFIG = {
    'server_url': 'http://114.55.118.105/api/wps/upload',
    'target_category': '软件',
    'batch_size': 50,
    'timeout': 30,
    'sheet_names': ['软件算法汇总', '问题清单', '议题清单', '问题汇总'],
    'process_all_sheets': True,
    'target_sheet': None,
    'software_keywords': ['软件'],
    'filter_mode': 'software',
    'debug_mode': False,  # 新增：调试模式开关
    'show_progress': True,  # 新增：显示进度条
    'log_level': 'INFO'  # 新增：日志级别
}

class Logger:
    """日志管理器"""

    def __init__(self, level: str = 'INFO'):
        self.level = level
        self.levels = {'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'ERROR': 3}
        self.start_time = time.time()

    def _should_log(self, level: str) -> bool:
        return self.levels.get(level, 1) >= self.levels.get(self.level, 1)

    def debug(self, message: str):
        if self._should_log('DEBUG'):
            print(f"🔍 [DEBUG] {message}")

    def info(self, message: str):
        if self._should_log('INFO'):
            print(f"ℹ️  [INFO] {message}")

    def warning(self, message: str):
        if self._should_log('WARNING'):
            print(f"⚠️  [WARN] {message}")

    def error(self, message: str):
        if self._should_log('ERROR'):
            print(f"❌ [ERROR] {message}")

    def success(self, message: str):
        print(f"✅ [SUCCESS] {message}")

    def get_elapsed_time(self) -> str:
        elapsed = time.time() - self.start_time
        return f"{elapsed:.2f}s"

# 全局日志器
logger = Logger(CONFIG['log_level'])

def is_empty_value(value):
    """判断值是否为空"""
    if value is None:
        return True
    str_value = str(value).strip().lower()
    return str_value in ['', 'nan', 'none', 'null']

def clean_string_value(value):
    """清理字符串值"""
    if is_empty_value(value):
        return ''
    return str(value).strip()

def is_valid_software_record(problem_category):
    """判断是否为有效的软件记录"""
    if is_empty_value(problem_category):
        return False
    category = clean_string_value(problem_category)
    return '软件' in category

def is_valid_record(problem_category, filter_mode):
    """判断是否为有效记录"""
    if is_empty_value(problem_category):
        return False

    if filter_mode == 'all':
        return True
    elif filter_mode == 'software':
        return is_valid_software_record(problem_category)
    else:
        return True

def transform_record(row_data):
    """转换单条记录"""
    record = {}

    field_mapping = {
        '项目名称': 'project_name',
        '问题分类': 'problem_category',
        '严重程度': 'severity_level',
        '问题/需求描述': 'problem_description',
        '解决方案': 'solution',
        '行动优先级': 'action_priority',
        '行动记录': 'action_record',
        '发起人': 'initiator',
        '责任人': 'responsible_person',
        '状态': 'status',
        '开始时间': 'start_time',
        '目标完成时间': 'target_completion_time',
        '实完时间': 'actual_completion_time',
        '备注': 'remarks'
    }

    for source_field, target_field in field_mapping.items():
        value = row_data.get(source_field, '')
        record[target_field] = clean_string_value(value)

    return record

def show_progress(current: int, total: int, prefix: str = "进度"):
    """显示进度条"""
    if not CONFIG['show_progress']:
        return

    percent = (current / total) * 100
    bar_length = 30
    filled_length = int(bar_length * current // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)

    print(f"\r{prefix}: |{bar}| {current}/{total} ({percent:.1f}%)", end='', flush=True)

    if current == total:
        print()  # 换行

def upload_batch(batch_data, batch_num, total_batches):
    """上传单批数据"""
    logger.info(f"上传第 {batch_num}/{total_batches} 批 ({len(batch_data)} 条)")

    # 调试信息（仅在调试模式下显示）
    if CONFIG['debug_mode'] and batch_data and batch_num == 1:
        logger.debug(f"第一条数据字段: {list(batch_data[0].keys())}")
        logger.debug(f"第一条数据内容: {batch_data[0]}")

    upload_payload = {
        'table_data': batch_data,
        'client_info': {
            'version': '2.2.0',  # 更新版本号
            'timestamp': datetime.now().isoformat(),
            'batch_info': {
                'current_batch': batch_num,
                'total_batches': total_batches,
                'batch_size': len(batch_data)
            },
            'source': 'WPS表格-优化版'
        }
    }

    try:
        start_time = time.time()
        response = requests.post(
            CONFIG['server_url'],
            json=upload_payload,
            headers={'Content-Type': 'application/json'},
            timeout=CONFIG['timeout']
        )
        upload_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()

            # 调试模式下显示完整响应
            if CONFIG['debug_mode']:
                logger.debug(f"服务器响应: {result}")

            if result.get('success'):
                stats = result.get('statistics', {})
                success_count = stats.get('success', 0)
                skipped_count = stats.get('skipped', 0)  # 新增：获取跳过计数
                failed_count = stats.get('failed', 0)

                # 优化后的显示逻辑
                if success_count > 0 or skipped_count > 0:
                    logger.success(f"第 {batch_num} 批处理完成 ({upload_time:.2f}s)")
                    if success_count > 0:
                        logger.success(f"  ✅ 新增: {success_count} 条")
                    if skipped_count > 0:
                        logger.info(f"  ⏭️  跳过: {skipped_count} 条 (数据已存在)")
                    if failed_count > 0:
                        logger.warning(f"  ❌ 失败: {failed_count} 条")

                    # 返回统计信息字典
                    return {'success': success_count, 'skipped': skipped_count, 'failed': failed_count}
                else:
                    logger.warning(f"第 {batch_num} 批无有效数据")
                    return {'success': 0, 'skipped': 0, 'failed': failed_count}
            else:
                error_msg = result.get('error', '未知错误')
                errors = result.get('errors', [])
                logger.error(f"第 {batch_num} 批业务失败: {error_msg}")

                # 显示前3个错误详情
                for i, error in enumerate(errors[:3], 1):
                    logger.error(f"  错误 {i}: {error}")

                if len(errors) > 3:
                    logger.error(f"  ... 还有 {len(errors) - 3} 个错误")

                return None
        else:
            logger.error(f"第 {batch_num} 批上传失败: HTTP {response.status_code}")
            if CONFIG['debug_mode']:
                logger.debug(f"错误响应: {response.text}")
            return None

    except Exception as e:
        logger.error(f"第 {batch_num} 批上传异常: {e}")
        return None

def get_database_status():
    """获取数据库状态信息"""
    logger.info("获取数据库状态信息")

    try:
        response = requests.get(
            'http://114.55.118.105/api/database/status',
            timeout=CONFIG['timeout']
        )

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                data = result.get('data', {})
                logger.info(f"数据库状态: 总议题 {data.get('total_issues', 0)}, "
                          f"开放 {data.get('open_issues', 0)}, "
                          f"关闭 {data.get('closed_issues', 0)}, "
                          f"已同步 {data.get('synced_issues', 0)}")
                return True
            else:
                logger.error(f"获取状态失败: {result.get('error', '未知错误')}")
                return False
        else:
            logger.error(f"状态请求失败: HTTP {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"获取状态异常: {e}")
        return False

def read_sheet_data(sheet_name):
    """读取指定工作表的数据"""
    try:
        logger.info(f"读取工作表: '{sheet_name}'")
        df = xl('$B:$P', headers=True, sheet_name=sheet_name)  # type: ignore
        if df is not None and not df.empty:
            logger.success(f"成功读取工作表: '{sheet_name}' - {len(df)} 行数据")
            return df
        else:
            logger.warning(f"工作表 '{sheet_name}' 为空或无法读取")
            return None
    except Exception as e:
        logger.error(f"读取工作表 '{sheet_name}' 失败: {e}")
        return None

def process_sheet_data(df, sheet_name):
    """处理单个工作表的数据"""
    logger.info(f"处理工作表: '{sheet_name}'")

    # 清洗数据
    logger.debug("清洗数据")
    df = df.dropna(how='all').reset_index(drop=True)

    # 清理字符串列
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].fillna('').astype(str)
            df[col] = df[col].replace(['nan', 'NaN', 'null', 'None', 'NULL'], '')
            df[col] = df[col].str.strip()

    # 筛选有效记录
    logger.debug("筛选有效记录")
    valid_records = []

    for _, row in df.iterrows():
        problem_category = clean_string_value(row.get('问题分类', ''))
        project_name = clean_string_value(row.get('项目名称', ''))

        # 跳过空行
        if is_empty_value(problem_category) and is_empty_value(project_name):
            continue

        # 检查是否为有效记录
        if is_valid_record(problem_category, CONFIG['filter_mode']):
            try:
                row_dict = row.to_dict() if hasattr(row, 'to_dict') else dict(row)
                record = transform_record(row_dict)

                # 验证必填字段
                if not record.get('project_name'):
                    continue

                # 如果没有问题分类，设置默认值
                if not record.get('problem_category'):
                    record['problem_category'] = '其他'

                # 添加来源工作表信息
                record['source_sheet'] = sheet_name

                valid_records.append(record)

            except Exception:
                continue

    logger.success(f"从工作表 '{sheet_name}' 找到 {len(valid_records)} 条有效记录")
    return valid_records

def show_config_info():
    """显示配置信息"""
    logger.info("当前配置:")
    logger.info(f"  支持的工作表: {', '.join(CONFIG['sheet_names'])}")
    logger.info(f"  处理模式: {'处理所有工作表' if CONFIG['process_all_sheets'] else '处理第一个可用工作表'}")
    if CONFIG['target_sheet']:
        logger.info(f"  指定工作表: {CONFIG['target_sheet']}")
    logger.info(f"  筛选模式: {CONFIG['filter_mode']}")
    logger.info(f"  软件关键词: {', '.join(CONFIG['software_keywords'])}")
    logger.info(f"  批次大小: {CONFIG['batch_size']}")
    logger.info(f"  调试模式: {'开启' if CONFIG['debug_mode'] else '关闭'}")
    logger.info(f"  进度显示: {'开启' if CONFIG['show_progress'] else '关闭'}")
    logger.info("💡 提示: 问题分类包含'软件'的记录会被处理")

def main():
    """主函数"""
    print("=" * 60)
    print("WPS表格数据上传工具 - 优化版")
    print("专门处理包含'软件'关键词的问题分类数据")
    print("=" * 60)

    # 显示配置信息
    show_config_info()

    try:
        # 1. 测试服务器连接
        logger.info("测试服务器连接")
        response = requests.get('http://114.55.118.105', timeout=CONFIG['timeout'])
        if response.status_code != 200:
            logger.error("服务器连接失败")
            return False
        logger.success("服务器连接成功")

        # 2. 获取当前数据库状态
        get_database_status()

        # 3. 读取和处理WPS数据
        logger.info("读取WPS表格数据")

        all_valid_records = []
        processed_sheets = []

        # 确定要处理的工作表
        if CONFIG['target_sheet']:
            sheets_to_process = [CONFIG['target_sheet']]
        elif CONFIG['process_all_sheets']:
            sheets_to_process = CONFIG['sheet_names']
        else:
            sheets_to_process = CONFIG['sheet_names']

        # 处理每个工作表
        for sheet_name in sheets_to_process:
            df = read_sheet_data(sheet_name)
            if df is not None:
                valid_records = process_sheet_data(df, sheet_name)
                if valid_records:
                    all_valid_records.extend(valid_records)
                    processed_sheets.append(sheet_name)

                    if not CONFIG['process_all_sheets']:
                        break

        if not all_valid_records:
            logger.error("没有找到任何有效记录")
            logger.info("请确保表格中存在以下工作表之一:")
            for sheet_name in CONFIG['sheet_names']:
                logger.info(f"   - {sheet_name}")
            return False

        logger.success(f"总共处理了 {len(processed_sheets)} 个工作表: {', '.join(processed_sheets)}")
        logger.success(f"总共找到 {len(all_valid_records)} 条有效记录")

        # 4. 显示摘要信息
        logger.info("数据摘要:")

        # 按分类统计
        category_stats = {}
        for record in all_valid_records:
            category = record.get('problem_category', '未知分类')
            category_stats[category] = category_stats.get(category, 0) + 1

        logger.info("分类统计:")
        for category, count in sorted(category_stats.items()):
            logger.info(f"  {category}: {count} 条")

        # 显示前3条记录详情
        logger.info("记录详情（前3条）:")
        for i, record in enumerate(all_valid_records[:3], 1):
            project_name = record.get('project_name', '未知项目')
            problem_description = record.get('problem_description', '无描述')
            status = record.get('status', '未知状态')
            category = record.get('problem_category', '未知分类')
            logger.info(f"  {i}. {project_name}: {problem_description[:50]}... (状态: {status}, 分类: {category})")

        if len(all_valid_records) > 3:
            logger.info(f"  ... 还有 {len(all_valid_records) - 3} 条记录")

        # 5. 分批上传
        logger.info("开始上传数据")
        batch_size = CONFIG['batch_size']
        total_batches = (len(all_valid_records) + batch_size - 1) // batch_size
        successful_uploads = 0
        skipped_uploads = 0  # 新增：跳过计数
        failed_uploads = 0

        for i in range(0, len(all_valid_records), batch_size):
            batch = all_valid_records[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            # 显示进度
            show_progress(batch_num, total_batches, "上传进度")

            result = upload_batch(batch, batch_num, total_batches)
            if result:
                successful_uploads += result.get('success', 0)
                skipped_uploads += result.get('skipped', 0)
                failed_uploads += result.get('failed', 0)
            else:
                failed_uploads += len(batch)

        # 6. 输出结果
        total_time = logger.get_elapsed_time()

        logger.info("=" * 60)
        logger.info("上传完成总结")
        logger.info(f"⏱️  总耗时: {total_time}")
        logger.info(f"📊 上传结果:")

        if successful_uploads > 0:
            logger.success(f"  ✅ 新增: {successful_uploads} 条")

        if skipped_uploads > 0:
            logger.info(f"  ⏭️  跳过: {skipped_uploads} 条 (数据已存在，无需重复上传)")

        if failed_uploads > 0:
            logger.warning(f"  ❌ 失败: {failed_uploads} 条")

        # 处理全部跳过的特殊情况
        if skipped_uploads == len(all_valid_records) and failed_uploads == 0:
            logger.success("✅ 数据验证完成！所有记录都已在数据库中")
        elif successful_uploads == 0 and skipped_uploads == 0 and failed_uploads > 0:
            logger.error("❌ 上传失败，所有记录都未能处理")
        elif successful_uploads > 0:
            logger.success("✅ 数据上传成功！")

        # 7. 获取最终状态
        logger.info("最终数据库状态:")
        get_database_status()

        return successful_uploads > 0 or skipped_uploads > 0

    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        return False

if __name__ == "__main__":
    print("开始执行WPS表格数据上传...")
    success = main()

    if success:
        logger.success("✅ 处理完成! 数据已验证/保存到数据库")
    else:
        logger.error("❌ 处理失败，请检查错误信息")

    print("\n按任意键退出...")
    try:
        input()
    except:
        pass
