#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试立即同步到 GitLab 功能
"""

import requests
from datetime import datetime

def test_immediate_gitlab_sync():
    """测试立即同步到 GitLab 功能"""
    print("=" * 60)
    print("测试立即同步到 GitLab 功能")
    print("=" * 60)

    api_url = "http://localhost/api/wps/upload"

    # 生成唯一的测试项目名
    unique_id = datetime.now().strftime('%Y%m%d%H%M%S')

    # 测试数据 - 新记录，状态为 Open
    test_data = {
        'table_data': [{
            'project_name': f'测试项目-立即同步-{unique_id}',
            'problem_category': '软件',
            'severity_level': '2',
            'problem_description': f'测试立即同步到GitLab功能-{unique_id}',
            'solution': '实现立即同步',
            'action_priority': '2',
            'action_record': '开发中',
            'initiator': '测试用户',
            'responsible_person': '陆杰',
            'status': 'O',  # Open状态
            'start_time': '2025-10-20 14:00:00',
            'target_completion_time': '2025-10-22 18:00:00',
            'actual_completion_time': '',
            'remarks': '测试立即同步功能'
        }],
        'client_info': {
            'version': '3.0.0',
            'timestamp': datetime.now().isoformat(),
            'source': '测试脚本-立即同步'
        }
    }

    # 第一次上传 - 应该立即创建 GitLab 议题
    print(f"\\n1️⃣ 第一次上传（状态: O - Open）")
    print(f"预期结果: 插入成功并立即创建 GitLab 议题")

    response1 = requests.post(api_url, json=test_data, timeout=60)
    if response1.status_code == 200:
        result1 = response1.json()
        print(f"✅ 响应: {result1['message']}")
        print(f"📊 统计: {result1['statistics']}")

        if result1['statistics']['success'] > 0:
            print("✅ 第一次上传成功")
            print("📋 检查日志以确认 GitLab 议题是否已创建")
        else:
            print("❌ 第一次上传失败")
            return False
    else:
        print(f"❌ HTTP错误: {response1.status_code}")
        return False

    # 等待3秒，让同步完成
    print("\\n⏳ 等待3秒...")
    import time
    time.sleep(3)

    # 第二次上传 - 更新状态为 Closed
    print(f"\\n2️⃣ 第二次上传（状态: C - Closed）")
    print(f"预期结果: 更新状态并立即关闭 GitLab 议题")

    test_data['table_data'][0]['status'] = 'C'
    test_data['table_data'][0]['action_record'] = '已完成'
    test_data['table_data'][0]['actual_completion_time'] = '2025-10-20 14:15:00'

    response2 = requests.post(api_url, json=test_data, timeout=60)
    if response2.status_code == 200:
        result2 = response2.json()
        print(f"✅ 响应: {result2['message']}")
        print(f"📊 统计: {result2['statistics']}")

        if result2['statistics']['updated'] > 0:
            print("✅ 第二次上传成功 - 状态已更新")
            if 'updated' in result2 and result2['updated']:
                print(f"🔄 更新详情: {result2['updated'][0]}")
            print("📋 检查日志以确认 GitLab 议题是否已关闭")
        else:
            print("❌ 第二次上传结果不符合预期")
    else:
        print(f"❌ HTTP错误: {response2.status_code}")

    print("\\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\\n💡 提示:")
    print("1. 检查 logs/wps_api.log 查看详细的同步日志")
    print("2. 访问 GitLab 项目确认议题是否已创建和关闭")
    print("3. 检查数据库 sync_queue 表是否有失败的任务")

    return True

if __name__ == "__main__":
    test_immediate_gitlab_sync()
