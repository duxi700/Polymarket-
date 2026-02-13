#!/bin/bash
# 使用 Mock API 测试监控系统的便捷脚本

echo "=================================="
echo "  Polymarket Mock API 测试工具"
echo "=================================="
echo ""

# 检查是否已安装依赖
if ! python3 -c "import aiohttp" 2>/dev/null; then
    echo "❌ 缺少依赖，请先运行: pip3 install -r requirements.txt"
    exit 1
fi

# 启动 Mock API 服务器（后台运行）
echo "🚀 启动 Mock API 服务器..."
python3 mock_api_server.py > /tmp/mock_api.log 2>&1 &
MOCK_PID=$!

# 等待服务器启动
sleep 2

# 检查服务器是否运行
if ! kill -0 $MOCK_PID 2>/dev/null; then
    echo "❌ Mock API 服务器启动失败"
    cat /tmp/mock_api.log
    exit 1
fi

echo "✅ Mock API 服务器已启动 (PID: $MOCK_PID)"
echo "📡 监听地址: http://localhost:8080"
echo ""

# 创建临时配置文件
echo "📝 创建临时配置..."
cat > /tmp/config_mock.yaml << 'EOF'
api:
  gamma_url: "http://localhost:8080"
  clob_url: "http://localhost:8080"
  timeout: 30

monitoring:
  live_market_interval: 5

rate_limit:
  max_requests_per_minute: 100

logging:
  level: "INFO"
  log_dir: "logs"
  rotation: "100 MB"
  retention: "7 days"
EOF

echo "✅ 配置文件已创建"
echo ""
echo "=================================="
echo "  开始监控测试"
echo "=================================="
echo ""
echo "💡 提示："
echo "  - Mock API 会生成模拟的市场数据"
echo "  - 价格会随机波动以触发信号"
echo "  - 按 Ctrl+C 停止测试"
echo ""
echo "=================================="
echo ""

# 清理函数
cleanup() {
    echo ""
    echo "🛑 停止 Mock API 服务器..."
    kill $MOCK_PID 2>/dev/null
    rm -f /tmp/config_mock.yaml
    echo "✅ 清理完成"
    exit 0
}

# 注册清理函数
trap cleanup EXIT INT TERM

# 运行监控系统
python3 -c "
import sys
import yaml
import asyncio

# 加载临时配置
with open('/tmp/config_mock.yaml', 'r') as f:
    config = yaml.safe_load(f)

# 保存原配置
import shutil
shutil.copy('config/config.yaml', '/tmp/config_backup.yaml')

# 写入mock配置
with open('config/config.yaml', 'w') as f:
    yaml.dump(config, f)

try:
    # 运行主程序
    import subprocess
    subprocess.run([sys.executable, 'main.py', 'https://polymarket.com/event/dota2-flc-liquid-2026-02-13'])
finally:
    # 恢复原配置
    shutil.copy('/tmp/config_backup.yaml', 'config/config.yaml')
"

# 脚本结束时会自动调用cleanup
