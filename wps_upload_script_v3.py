#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WPS表格简单上传脚本 - 优化版
直接从WPS表格读取数据并上传到服务器
"""

import requests
import json
import pandas as pd
import logging
import time
from datetime import datetime
from functools import wraps

# ==================== 配置信息 ====================
CONFIG = {
    'server': {
        'base_url': 'http://114.55.118.105',
        'upload_endpoint': '/api/wps/upload',
        'timeout': 30
    },
    'wps': {
        'range': '$B:$P',
        'sheet_name': '问题清单',
        'target_category': '软件'
    },
    'upload': {
        'batch_size': 50,
        'max_retries': 3,
        'retry_delay': 1
    },
    'fields': {
        'required': ['项目名称', '问题分类'],
        'mapping': {
            '序号': 'serial_number',
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
    }
}

# 服务器URL配置
SERVER_URL = f"{CONFIG['server']['base_url']}{CONFIG['server']['upload_endpoint']}"

# ==================== 工具函数 ====================
def setup_logging():
    """设置日志 - WPS环境适配版"""
    # 创建logger
    logger = logging.getLogger('WPSUploader')
    logger.setLevel(logging.INFO)

    # 避免重复添加handler
    if not logger.handlers:
        # 创建formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # 只使用控制台handler（WPS环境不允许文件写入）
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger

def retry(max_attempts=3, delay=1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise e
                    print(f"⚠️ 第 {attempt + 1} 次尝试失败: {e}")
                    time.sleep(delay * (2 ** attempt))  # 指数退避
            return None
        return wrapper
    return decorator

def is_empty_value(value):
    """判断值是否为空"""
    if pd.isna(value):
        return True
    str_value = str(value).strip().lower()
    return str_value in ['', 'nan', 'none', 'null']

def safe_convert_int(value, default=0):
    """安全转换为整数"""
    try:
        if is_empty_value(value):
            return default
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default

def clean_string_value(value):
    """清理字符串值"""
    if is_empty_value(value):
        return ''
    return str(value).strip()

# ==================== 数据处理函数 ====================
def clean_and_validate_data(df):
    """清洗和验证数据"""
    print("🧹 开始清洗数据...")

    # 移除完全空的行
    initial_rows = len(df)
    df = df.dropna(how='all').reset_index(drop=True)
    print(f"📋 移除空行: {initial_rows} -> {len(df)}")

    # 清理字符串列，处理nan值
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].fillna('').astype(str)
            # 处理各种空值表示
            df[col] = df[col].replace(['nan', 'NaN', 'null', 'None', 'NULL'], '')
            df[col] = df[col].str.strip()

    print("✅ 数据清洗完成")
    return df

def find_header_row(df, target_columns=['问题分类', '项目名称']):
    """智能查找表头行"""
    print("🔍 智能查找表头行...")

    for idx, row in df.iterrows():
        row_values = [clean_string_value(val) for val in row.values if not is_empty_value(val)]

        # 检查是否包含目标列名
        matches = sum(1 for col in target_columns if any(col in val for val in row_values))
        match_ratio = matches / len(target_columns)

        if match_ratio >= 0.7:  # 70%匹配度
            print(f"✅ 找到表头行: 第 {idx+1} 行 (匹配度: {match_ratio:.1%})")
            return idx

    print("⚠️ 未找到标准表头行")
    return None

def standardize_column_names(df, header_row):
    """标准化列名"""
    new_columns = []
    for i, val in enumerate(df.iloc[header_row].values):
        col_name = clean_string_value(val) if not is_empty_value(val) else f"Unnamed_{i}"
        new_columns.append(col_name)

    print(f"📋 标准化列名: {new_columns}")

    df.columns = new_columns
    result_df = df.iloc[header_row+1:].reset_index(drop=True)

    print(f"📊 处理后数据行数: {len(result_df)}")
    return result_df

def is_valid_software_record(problem_category):
    """判断是否为有效的软件记录"""
    if is_empty_value(problem_category):
        return False
    category_str = clean_string_value(problem_category)
    return CONFIG['wps']['target_category'] in category_str

def generate_issue_title(project_name, problem_description):
    """生成议题标题"""
    project_name = clean_string_value(project_name)
    problem_description = clean_string_value(problem_description)

    if project_name and problem_description:
        return f"{project_name} - {problem_description}"
    elif project_name:
        return project_name
    elif problem_description:
        return problem_description
    else:
        return "未命名议题"

def validate_required_fields(record, required_fields):
    """验证必填字段"""
    missing = []
    for field in required_fields:
        field_value = record.get(field, '')
        if is_empty_value(field_value):
            missing.append(field)
    return missing

def transform_record(row_data, field_mapping):
    """转换单条记录"""
    record = {}

    # 转换字段
    for source_field, target_field in field_mapping.items():
        value = row_data.get(source_field, '')

        # 特殊处理数字字段
        if target_field in ['severity_level', 'action_priority']:
            record[target_field] = safe_convert_int(value)
        else:
            record[target_field] = clean_string_value(value)

    # 生成议题标题
    project_name = record.get('project_name', '')
    problem_description = record.get('problem_description', '')
    record['issue_title'] = generate_issue_title(project_name, problem_description)

    return record

# ==================== 网络请求函数 ====================
@retry(max_attempts=3)
def test_server_connection():
    """测试服务器连接"""
    print("🌐 测试服务器连接...")

    response = requests.get(
        CONFIG['server']['base_url'],
        timeout=CONFIG['server']['timeout']
    )

    if response.status_code == 200:
        print("✅ 服务器连接成功")
        return True
    else:
        print(f"❌ 服务器连接失败: HTTP {response.status_code}")
        return False

@retry(max_attempts=3, delay=1)
def upload_batch(batch_data, batch_num, total_batches):
    """上传单批数据"""
    print(f"📤 上传第 {batch_num}/{total_batches} 批数据 ({len(batch_data)} 条记录)...")

    upload_payload = {
        'table_data': batch_data,
        'client_info': {
            'version': '2.0.0',
            'timestamp': datetime.now().isoformat(),
            'batch_info': {
                'current_batch': batch_num,
                'total_batches': total_batches,
                'batch_size': len(batch_data)
            },
            'source': 'WPS表格-优化版'
        }
    }

    response = requests.post(
        SERVER_URL,
        json=upload_payload,
        headers={'Content-Type': 'application/json'},
        timeout=CONFIG['server']['timeout']
    )

    return response

def upload_data_in_batches(api_data):
    """分批上传数据"""
    batch_size = CONFIG['upload']['batch_size']
    total_batches = (len(api_data) + batch_size - 1) // batch_size
    successful_uploads = 0
    failed_uploads = 0

    print(f"🚀 开始分批上传: 总计 {len(api_data)} 条记录, 分 {total_batches} 批")

    for i in range(0, len(api_data), batch_size):
        batch = api_data[i:i + batch_size]
        batch_num = (i // batch_size) + 1

        try:
            response = upload_batch(batch, batch_num, total_batches)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    successful_uploads += len(batch)
                    print(f"✅ 第 {batch_num} 批上传成功")
                else:
                    failed_uploads += len(batch)
                    print(f"❌ 第 {batch_num} 批业务失败: {result.get('error', '未知错误')}")
            else:
                failed_uploads += len(batch)
                print(f"❌ 第 {batch_num} 批上传失败: HTTP {response.status_code}")
                try:
                    error_text = response.text[:200] if response.text else "无响应内容"
                    print(f"   响应内容: {error_text}")
                except:
                    pass
        except Exception as e:
            failed_uploads += len(batch)
            print(f"❌ 第 {batch_num} 批上传异常: {e}")

    print(f"📊 上传完成: 成功 {successful_uploads}, 失败 {failed_uploads}")
    return successful_uploads

# ==================== 主要业务函数 ====================
def read_and_process_wps_data():
    """读取和处理WPS数据"""
    try:
        # 读取WPS表格数据
        print("📖 读取WPS表格数据...")
        df = xl(CONFIG['wps']['range'], headers=True, sheet_name=CONFIG['wps']['sheet_name'])

        if df is None or df.empty:
            print("❌ 没有读取到数据")
            return None

        print(f"✅ 读取到 {len(df)} 行原始数据")

        # 清洗数据
        df = clean_and_validate_data(df)

        # 查找表头行
        header_row = find_header_row(df, ['问题分类', '项目名称'])

        if header_row is not None:
            df = standardize_column_names(df, header_row)
        else:
            print("⚠️ 未找到标准表头行，使用原始列名")

        print(f"📋 最终列名: {list(df.columns)}")

        # 检查必要列是否存在
        if '问题分类' not in df.columns:
            print("❌ 表格中没有找到'问题分类'列")
            print(f"📋 可用列: {list(df.columns)}")
            return None

        return df

    except Exception as e:
        print(f"❌ 读取WPS数据失败: {e}")
        return None

def filter_and_transform_data(df):
    """筛选和转换数据"""
    print("🔍 筛选软件相关记录...")

    software_records = []
    field_mapping = CONFIG['fields']['mapping']

    # 先显示所有问题分类统计
    category_counts = {}
    for idx, row in df.iterrows():
        problem_category = clean_string_value(row.get('问题分类', ''))
        if problem_category:
            category_counts[problem_category] = category_counts.get(problem_category, 0) + 1

    print(f"📊 问题分类统计: {category_counts}")

    for idx, row in df.iterrows():
        problem_category = clean_string_value(row.get('问题分类', ''))
        project_name = clean_string_value(row.get('项目名称', ''))

        # 调试输出：显示原始数据
        print(f"🔍 第 {idx+1} 行: 项目='{project_name}', 分类='{problem_category}'")

        # 跳过空值
        if is_empty_value(problem_category) and is_empty_value(project_name):
            print(f"   ⏭️ 跳过空行")
            continue

        # 检查是否为软件相关记录
        if is_valid_software_record(problem_category):
            try:
                # 转换记录
                row_dict = row.to_dict() if hasattr(row, 'to_dict') else dict(row)
                record = transform_record(row_dict, field_mapping)

                print(f"   🔄 转换后: 项目='{record.get('project_name')}', 分类='{record.get('problem_category')}'")

                # 验证必填字段 - 使用转换后的字段名
                missing_fields = []
                for required_field in CONFIG['fields']['required']:
                    # 将中文字段名映射到英文字段名
                    mapped_field = field_mapping.get(required_field, required_field)
                    if is_empty_value(record.get(mapped_field)):
                        missing_fields.append(required_field)

                if missing_fields:
                    print(f"   ⚠️ 缺少必填字段: {missing_fields}")
                    continue

                software_records.append(record)
                print(f"   ✅ 添加成功: {record['issue_title']}")

            except Exception as e:
                print(f"   ❌ 数据转换失败: {e}")
                continue
        else:
            print(f"   ❌ 不是软件分类，跳过")

    print(f"✅ 找到 {len(software_records)} 条有效的软件相关记录")
    return software_records

def display_upload_summary(api_data):
    """显示上传摘要"""
    print("\n" + "="*60)
    print("📤 即将上传的数据摘要:")
    print("="*60)

    for i, record in enumerate(api_data[:10], 1):  # 只显示前10条
        print(f"  {i}. {record['issue_title']}")
        print(f"     问题分类: {record['problem_category']}")
        print(f"     状态: {record['status']}")
        print(f"     责任人: {record['responsible_person']}")
        print()

    if len(api_data) > 10:
        print(f"  ... 还有 {len(api_data) - 10} 条记录")

    print(f"总计: {len(api_data)} 条记录")
    print("="*60)

# ==================== 主函数 ====================
def main():
    """主函数"""
    # 设置日志（仅控制台输出）
    logger = setup_logging()

    print("=" * 60)
    print("WPS表格数据上传工具 - 优化版")
    print("=" * 60)

    try:
        # 1. 测试服务器连接
        if not test_server_connection():
            print("❌ 服务器连接失败，程序退出")
            return False

        # 2. 读取和处理WPS数据
        df = read_and_process_wps_data()
        if df is None:
            print("❌ 数据读取失败，程序退出")
            return False

        # 3. 筛选和转换数据
        valid_records = filter_and_transform_data(df)
        if not valid_records:
            print("⚠️ 没有找到符合条件的记录")
            print(f"💡 提示: 当前搜索目标分类为 '{CONFIG['wps']['target_category']}'")
            return False

        # 4. 显示上传摘要
        display_upload_summary(valid_records)

        # 5. 分批上传数据
        print("🚀 开始上传数据到服务器...")
        success_count = upload_data_in_batches(valid_records)

        # 6. 输出结果
        success_ratio = success_count / len(valid_records)
        print(f"📊 上传结果: {success_count}/{len(valid_records)} 条记录成功 ({success_ratio:.1%})")

        return success_count > 0

    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        return False

if __name__ == "__main__":
    print("开始执行WPS表格数据上传...")
    success = main()

    if success:
        print("\n🎉 上传完成! 数据已成功保存到数据库")
    else:
        print("\n😞 上传失败，请检查错误信息")

    print("\n按任意键退出...")
    try:
        input()
    except:
        pass
