#!/usr/bin/env python3
"""
GiteeAI API 连接测试脚本
测试指定的 API Key 和配置是否可用
"""

import sys
import time
from openai import OpenAI

# 配置参数
API_KEY = "1NJHGJ7C6C3DL4HKVFQQ655TX0ARTHRUYGTW1TWQ"
MODEL = "Qwen3-8B"
BASE_URL = "https://ai.gitee.com/v1"

def test_gitee_api():
    """测试GiteeAI API连接和响应"""
    print("🔍 GiteeAI API 连接测试")
    print("=" * 50)
    print(f"Base URL: {BASE_URL}")
    print(f"Model: {MODEL}")
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-10:]}")
    print("=" * 50)
    
    try:
        # 创建OpenAI客户端
        print("📡 创建API客户端...")
        client = OpenAI(
            base_url=BASE_URL,
            api_key=API_KEY,
        )
        
        # 发送测试请求
        print("🚀 发送测试请求...")
        start_time = time.time()
        
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Hi, please respond with just 'Hello' to test the connection."
                }
            ],
            model=MODEL,
            max_tokens=10,
            temperature=0.1,
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # 显示结果
        print("✅ 连接成功!")
        print(f"⏱️  响应时间: {response_time:.2f} 秒")
        print(f"🤖 模型响应: {response.choices[0].message.content}")
        print(f"📊 Token使用: {response.usage.total_tokens} tokens")
        
        return True
        
    except Exception as e:
        print("❌ 连接失败!")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        
        # 提供具体的错误分析
        error_str = str(e).lower()
        if "timeout" in error_str:
            print("\n💡 可能的解决方案:")
            print("1. 检查网络连接")
            print("2. 尝试使用VPN或代理")
            print("3. 等待一段时间后重试")
        elif "unauthorized" in error_str or "401" in error_str:
            print("\n💡 可能的解决方案:")
            print("1. 检查API Key是否正确")
            print("2. 确认API Key是否有效或未过期")
        elif "not found" in error_str or "404" in error_str:
            print("\n💡 可能的解决方案:")
            print("1. 检查Base URL是否正确")
            print("2. 确认模型名称是否支持")
        
        return False

def test_simple_connection():
    """简单的网络连接测试"""
    print("\n🌐 网络连通性测试")
    print("-" * 30)
    
    try:
        import requests
        print("📡 测试基础网络连接...")
        
        # 简单的HTTP请求测试
        response = requests.get("https://ai.gitee.com", timeout=10)
        print(f"✅ 基础连接成功 (状态码: {response.status_code})")
        
    except requests.exceptions.Timeout:
        print("❌ 连接超时")
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误")
    except Exception as e:
        print(f"❌ 其他错误: {e}")

if __name__ == "__main__":
    print("GiteeAI API 测试工具")
    print("Author: GitHub Copilot")
    print()
    
    # 运行测试
    success = test_gitee_api()
    
    if not success:
        # 如果API测试失败，进行网络连通性测试
        test_simple_connection()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 测试完成: API 配置可用!")
        sys.exit(0)
    else:
        print("❌ 测试完成: API 配置不可用!")
        print("\n建议:")
        print("1. 检查网络连接和防火墙设置")
        print("2. 验证API Key的有效性")
        print("3. 尝试使用其他AI提供商")
        sys.exit(1)