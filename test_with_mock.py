"""
使用 Mock API 测试监控系统
"""
import asyncio
import subprocess
import time
import sys
import os

def start_mock_server():
    """启动 Mock API 服务器"""
    print("🚀 启动 Mock API 服务器...")
    process = subprocess.Popen(
        [sys.executable, "mock_api_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待服务器启动
    time.sleep(2)
    
    if process.poll() is None:
        print("✅ Mock API 服务器已启动 (PID: {})".format(process.pid))
        return process
    else:
        print("❌ Mock API 服务器启动失败")
        stdout, stderr = process.communicate()
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return None

def stop_mock_server(process):
    """停止 Mock API 服务器"""
    if process:
        print("\n🛑 停止 Mock API 服务器...")
        process.terminate()
        try:
            process.wait(timeout=5)
            print("✅ Mock API 服务器已停止")
        except subprocess.TimeoutExpired:
            process.kill()
            print("⚠️  强制终止 Mock API 服务器")

async def run_monitor():
    """运行监控系统"""
    # 临时修改配置文件路径
    original_config = os.environ.get('CONFIG_PATH', '')
    os.environ['CONFIG_PATH'] = 'config/config_mock.yaml'
    
    print("\n" + "="*60)
    print("📊 启动监控系统（使用 Mock API）")
    print("="*60 + "\n")
    
    # 运行监控
    process = subprocess.Popen(
        [sys.executable, "main.py", "https://polymarket.com/event/dota2-flc-liquid-2026-02-13"],
        env={**os.environ, 'CONFIG_PATH': 'config/config_mock.yaml'}
    )
    
    return process

def main():
    """主函数"""
    mock_server = None
    monitor_process = None
    
    try:
        # 启动 Mock API 服务器
        mock_server = start_mock_server()
        if not mock_server:
            print("❌ 无法启动 Mock API 服务器，退出测试")
            return
        
        # 启动监控系统
        print("\n" + "="*60)
        print("📊 启动监控系统...")
        print("="*60)
        print("\n💡 提示：")
        print("  - 监控系统将连接到本地 Mock API")
        print("  - 按 Ctrl+C 可停止测试")
        print("  - Mock API 会生成随机价格波动")
        print("\n")
        
        # 修改配置并运行
        monitor_process = subprocess.Popen(
            [
                sys.executable, "-c",
                """
import sys
import yaml

# 加载并修改配置
with open('config/config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

config['api']['gamma_url'] = 'http://localhost:8080'
config['api']['clob_url'] = 'http://localhost:8080'

# 保存到临时文件
with open('/tmp/config_mock.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(config, f)

# 运行主程序
sys.path.insert(0, '.')
import asyncio
from main import main
asyncio.run(main())
"""
            ],
            env={**os.environ, 'PYTHONPATH': '.'}
        )
        
        # 等待用户中断
        monitor_process.wait()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  收到中断信号，正在清理...")
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
    finally:
        # 清理进程
        if monitor_process:
            monitor_process.terminate()
            try:
                monitor_process.wait(timeout=3)
            except:
                monitor_process.kill()
        
        if mock_server:
            stop_mock_server(mock_server)
        
        print("\n✅ 测试完成")

if __name__ == "__main__":
    main()
