#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WPS表格上传脚本 - 增强版
专门处理包含"软件"关键词的问题分类数据
在WPS环境下运行，负责数据上传到服务器
"""

import requests
from datetime import datetime

# ==================== 配置信息 ====================
CONFIG = {
    'server_url': 'http://114.55.118.105/api/wps/upload',
    'target_category': '软件',
    'batch_size': 50,
    'timeout': 30,
    'sheet_names': ['软件算法汇总', '问题清单', '议题清单', '问题汇总'],  # 支持的工作表名称
    'process_all_sheets': True,  # 是否处理所有工作表
    'target_sheet': None,  # 指定目标工作表，None表示自动检测
    'software_keywords': ['软件'],  # 软件相关关键词
    'filter_mode': 'software'  # 筛选模式: 'software'(软件相关), 'all'(所有记录)
}

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
    # 只匹配包含"软件"两个字的记录
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

    # 字段映射
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

    # 不再生成issue_title，统一由数据库向GitLab推送创建议题

    return record

def upload_batch(batch_data, batch_num, total_batches):
    """上传单批数据"""
    print(f"📤 上传第 {batch_num}/{total_batches} 批 ({len(batch_data)} 条)...")

    # 调试：显示第一条数据的字段
    if batch_data and batch_num == 1:
        print(f"🔍 调试 - 第一条数据字段: {list(batch_data[0].keys())}")
        print(f"🔍 调试 - 第一条数据内容: {batch_data[0]}")

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
            'source': 'WPS表格-增强版'
        }
    }

    try:
        response = requests.post(
            CONFIG['server_url'],
            json=upload_payload,
            headers={'Content-Type': 'application/json'},
            timeout=CONFIG['timeout']
        )

        if response.status_code == 200:
            result = response.json()
            print(f"🔍 调试 - 服务器响应: {result}")
            if result.get('success'):
                print(f"✅ 第 {batch_num} 批上传成功")
                return True
            else:
                print(f"❌ 第 {batch_num} 批业务失败: {result.get('error', '未知错误')}")
                return False
        else:
            print(f"❌ 第 {batch_num} 批上传失败: HTTP {response.status_code}")
            print(f"🔍 调试 - 错误响应: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 第 {batch_num} 批上传异常: {e}")
        return False

# GitLab同步功能已移除 - 此脚本在WPS环境下运行，不负责GitLab同步

def get_database_status():
    """获取数据库状态信息"""
    print("\n📊 获取数据库状态信息...")

    try:
        response = requests.get(
            'http://114.55.118.105/api/database/status',
            timeout=CONFIG['timeout']
        )

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                data = result.get('data', {})
                print(f"📋 数据库状态:")
                print(f"  总议题数: {data.get('total_issues', 0)}")
                print(f"  开放议题: {data.get('open_issues', 0)}")
                print(f"  关闭议题: {data.get('closed_issues', 0)}")
                print(f"  已同步议题: {data.get('synced_issues', 0)}")
                return True
            else:
                print(f"❌ 获取状态失败: {result.get('error', '未知错误')}")
                return False
        else:
            print(f"❌ 状态请求失败: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 获取状态异常: {e}")
        return False

def read_sheet_data(sheet_name):
    """读取指定工作表的数据"""
    try:
        print(f"🎯 读取工作表: '{sheet_name}'")
        df = xl('$B:$P', headers=True, sheet_name=sheet_name)  # type: ignore
        if df is not None and not df.empty:
            print(f"✅ 成功读取工作表: '{sheet_name}' - {len(df)} 行数据")
            return df
        else:
            print(f"⚠️ 工作表 '{sheet_name}' 为空或无法读取")
            return None
    except Exception as e:
        print(f"⚠️ 读取工作表 '{sheet_name}' 失败: {e}")
        return None

def process_sheet_data(df, sheet_name):
    """处理单个工作表的数据"""
    print(f"\n📊 处理工作表: '{sheet_name}'")

    # 清洗数据
    print("🧹 清洗数据...")
    df = df.dropna(how='all').reset_index(drop=True)

    # 清理字符串列
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].fillna('').astype(str)
            df[col] = df[col].replace(['nan', 'NaN', 'null', 'None', 'NULL'], '')
            df[col] = df[col].str.strip()

    # 筛选有效记录
    print("🔍 筛选有效记录...")
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

    print(f"✅ 从工作表 '{sheet_name}' 找到 {len(valid_records)} 条有效记录")
    return valid_records

def show_config_info():
    """显示配置信息"""
    print("📋 当前配置:")
    print(f"  支持的工作表: {', '.join(CONFIG['sheet_names'])}")
    print(f"  处理模式: {'处理所有工作表' if CONFIG['process_all_sheets'] else '处理第一个可用工作表'}")
    if CONFIG['target_sheet']:
        print(f"  指定工作表: {CONFIG['target_sheet']}")
    print(f"  筛选模式: {CONFIG['filter_mode']}")
    print(f"  软件关键词: {', '.join(CONFIG['software_keywords'])}")
    print(f"  批次大小: {CONFIG['batch_size']}")
    print("💡 提示: 问题分类包含'软件'的记录会被处理")
    print()

def main():
    """主函数"""
    print("=" * 50)
    print("WPS表格数据上传工具 - 增强版")
    print("专门处理包含'软件'关键词的问题分类数据")
    print("=" * 50)

    # 显示配置信息
    show_config_info()

    try:
        # 1. 测试服务器连接
        print("🌐 测试服务器连接...")
        response = requests.get('http://114.55.118.105', timeout=CONFIG['timeout'])
        if response.status_code != 200:
            print("❌ 服务器连接失败")
            return False
        print("✅ 服务器连接成功")

        # 2. 获取当前数据库状态
        get_database_status()

        # 3. 读取和处理WPS数据
        print("📖 读取WPS表格数据...")

        all_valid_records = []
        processed_sheets = []

        # 确定要处理的工作表
        if CONFIG['target_sheet']:
            # 指定了目标工作表
            sheets_to_process = [CONFIG['target_sheet']]
        elif CONFIG['process_all_sheets']:
            # 处理所有支持的工作表
            sheets_to_process = CONFIG['sheet_names']
        else:
            # 自动检测第一个可用的工作表
            sheets_to_process = CONFIG['sheet_names']

        # 处理每个工作表
        for sheet_name in sheets_to_process:
            df = read_sheet_data(sheet_name)
            if df is not None:
                valid_records = process_sheet_data(df, sheet_name)
                if valid_records:
                    all_valid_records.extend(valid_records)
                    processed_sheets.append(sheet_name)

                    # 如果只处理一个工作表，处理完就停止
                    if not CONFIG['process_all_sheets']:
                        break

        if not all_valid_records:
            print("❌ 没有找到任何有效记录")
            print("💡 请确保表格中存在以下工作表之一:")
            for sheet_name in CONFIG['sheet_names']:
                print(f"   - {sheet_name}")
            return False

        print(f"\n✅ 总共处理了 {len(processed_sheets)} 个工作表: {', '.join(processed_sheets)}")
        print(f"✅ 总共找到 {len(all_valid_records)} 条有效记录")

        # 4. 显示摘要和调试信息
        print("\n📤 即将上传的数据摘要:")

        # 按分类统计
        category_stats = {}
        for record in all_valid_records:
            category = record.get('problem_category', '未知分类')
            category_stats[category] = category_stats.get(category, 0) + 1

        print("📊 分类统计:")
        for category, count in sorted(category_stats.items()):
            print(f"  {category}: {count} 条")

        print("\n📋 记录详情（前5条）:")
        for i, record in enumerate(all_valid_records[:5], 1):
            project_name = record.get('project_name', '未知项目')
            problem_description = record.get('problem_description', '无描述')
            status = record.get('status', '未知状态')
            category = record.get('problem_category', '未知分类')
            source_sheet = record.get('source_sheet', '未知工作表')
            print(f"  {i}. {project_name}: {problem_description[:50]}... (状态: {status}, 分类: {category}, 来源: {source_sheet})")

        if len(all_valid_records) > 5:
            print(f"  ... 还有 {len(all_valid_records) - 5} 条记录")
        print(f"总计: {len(all_valid_records)} 条记录")

        # 5. 分批上传
        print("\n🚀 开始上传数据...")
        batch_size = CONFIG['batch_size']
        total_batches = (len(all_valid_records) + batch_size - 1) // batch_size
        successful_uploads = 0

        for i in range(0, len(all_valid_records), batch_size):
            batch = all_valid_records[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            if upload_batch(batch, batch_num, total_batches):
                successful_uploads += len(batch)

        # GitLab同步已移除 - 由服务器端处理

        # 6. 输出结果
        success_ratio = successful_uploads / len(all_valid_records)
        print(f"\n📊 上传结果: {successful_uploads}/{len(all_valid_records)} 条记录成功 ({success_ratio:.1%})")

        # 10. 获取最终状态
        print("\n📊 最终数据库状态:")
        get_database_status()

        return successful_uploads > 0

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
