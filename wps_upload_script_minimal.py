#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WPS表格上传脚本 - 极简版（最少日志输出）
专门处理"软件算法汇总"工作表的数据
"""

import requests
from datetime import datetime

# ==================== 配置信息 ====================
CONFIG = {
    'server_url': 'http://114.55.118.105/api/wps/upload',
    'target_category': '软件',
    'batch_size': 50,
    'timeout': 30
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
    return CONFIG['target_category'] in clean_string_value(problem_category)

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
            'source': 'WPS表格-极简版'
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

def main():
    """主函数"""
    print("=" * 50)
    print("WPS表格数据上传工具 - 极简版")
    print("=" * 50)

    try:
        # 1. 测试服务器连接
        print("🌐 测试服务器连接...")
        response = requests.get('http://114.55.118.105', timeout=CONFIG['timeout'])
        if response.status_code != 200:
            print("❌ 服务器连接失败")
            return False
        print("✅ 服务器连接成功")

        # 2. 读取WPS数据
        print("📖 读取WPS表格数据...")
        print("🎯 目标工作表: '软件算法汇总'")

        try:
            # xl是WPS环境的内置函数，用于读取表格数据
            df = xl('$B:$P', headers=True, sheet_name='软件算法汇总')  # type: ignore
        except Exception as e:
            print(f"❌ 读取'软件算法汇总'表失败: {e}")
            print("💡 请确保表格中存在名为'软件算法汇总'的工作表")
            print("💡 如果工作表名称不同，请修改脚本中的sheet_name参数")
            return False

        if df is None or df.empty:
            print("❌ 没有读取到数据")
            return False

        print(f"✅ 从'软件算法汇总'表读取到 {len(df)} 行数据")

        # 3. 清洗数据
        print("🧹 清洗数据...")
        df = df.dropna(how='all').reset_index(drop=True)

        # 清理字符串列
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].fillna('').astype(str)
                df[col] = df[col].replace(['nan', 'NaN', 'null', 'None', 'NULL'], '')
                df[col] = df[col].str.strip()

        # 4. 筛选软件相关记录
        print("🔍 筛选软件相关记录...")
        software_records = []

        for _, row in df.iterrows():
            problem_category = clean_string_value(row.get('问题分类', ''))
            project_name = clean_string_value(row.get('项目名称', ''))

            # 跳过空行
            if is_empty_value(problem_category) and is_empty_value(project_name):
                continue

            # 检查是否为软件相关记录
            if is_valid_software_record(problem_category):
                try:
                    row_dict = row.to_dict() if hasattr(row, 'to_dict') else dict(row)
                    record = transform_record(row_dict)

                    # 验证必填字段
                    if not record.get('project_name') or not record.get('problem_category'):
                        continue

                    software_records.append(record)

                except Exception as e:
                    continue

        print(f"✅ 找到 {len(software_records)} 条软件相关记录")

        if not software_records:
            print("⚠️ 没有找到符合条件的记录")
            return False

        # 5. 显示摘要（只显示前3条）
        print("\n📤 即将上传的数据摘要:")
        for i, record in enumerate(software_records[:3], 1):
            project_name = record.get('project_name', '未知项目')
            problem_description = record.get('problem_description', '无描述')
            print(f"  {i}. {project_name}: {problem_description[:50]}...")
        if len(software_records) > 3:
            print(f"  ... 还有 {len(software_records) - 3} 条记录")
        print(f"总计: {len(software_records)} 条记录")

        # 6. 分批上传
        print("\n🚀 开始上传数据...")
        batch_size = CONFIG['batch_size']
        total_batches = (len(software_records) + batch_size - 1) // batch_size
        successful_uploads = 0

        for i in range(0, len(software_records), batch_size):
            batch = software_records[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            if upload_batch(batch, batch_num, total_batches):
                successful_uploads += len(batch)

        # 7. 输出结果
        success_ratio = successful_uploads / len(software_records)
        print(f"\n📊 上传结果: {successful_uploads}/{len(software_records)} 条记录成功 ({success_ratio:.1%})")

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
