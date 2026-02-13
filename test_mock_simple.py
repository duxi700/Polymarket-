#!/usr/bin/env python3
"""
简单的 Mock API 测试脚本
在单个进程中启动 Mock API 和监控程序
"""
import asyncio
import sys
from aiohttp import web
import random
import time

# Mock API 数据和处理函数
MOCK_EVENT_DATA = {
    "slug": "dota2-flc-liquid-2026-02-13",
    "title": "Dota2: FLC vs Liquid",
    "markets": [{
        "conditionId": "0x1234567890abcdef",
        "question": "Will FLC win?",
        "tokens": [
            {
                "outcome": "Yes",
                "token_id": "token-yes-1",
                "outcome_id": "0xyes1",
                "price": "0.45"
            },
            {
                "outcome": "No",
                "token_id": "token-no-1",
                "outcome_id": "0xno1",
                "price": "0.55"
            }
        ]
    }]
}

token_prices = {}
token_poll_count = {}  # 记录每个token的轮询次数

def generate_mock_orderbook(base_price=0.5, volatility=0.05):
    """生成模拟订单簿"""
    price_shift = random.uniform(-volatility, volatility)
    mid_price = max(0.01, min(0.99, base_price + price_shift))
    
    bids = []
    asks = []
    
    for i in range(5):
        price = mid_price - 0.01 * (i + 1)
        size = random.uniform(100, 1000)
        if price > 0.01:
            bids.append({"price": f"{price:.4f}", "size": f"{size:.2f}"})
    
    for i in range(5):
        price = mid_price + 0.01 * (i + 1)
        size = random.uniform(100, 1000)
        if price < 0.99:
            asks.append({"price": f"{price:.4f}", "size": f"{size:.2f}"})
    
    return {
        "bids": bids,
        "asks": asks,
        "timestamp": int(time.time() * 1000)
    }

async def handle_event(request):
    """处理事件查询"""
    slug = request.query.get('slug', '')
    if slug == MOCK_EVENT_DATA['slug']:
        print(f"[Mock API] 事件查询: slug={slug}")
        return web.json_response([MOCK_EVENT_DATA])
    return web.json_response({"error": "Event not found"}, status=404)

async def handle_orderbook(request):
    """处理订单簿查询"""
    token_id = request.query.get('token_id', '')
    print(f"[Mock API] 订单簿查询: token_id={token_id}")
    
    if token_id not in token_prices:
        token_prices[token_id] = random.uniform(0.4, 0.6)
        token_poll_count[token_id] = 0
    
    token_poll_count[token_id] += 1
    poll_count = token_poll_count[token_id]
    
    # 每10-15次轮询产生一次大幅波动（模拟情绪驱动的价格错配）
    if poll_count % random.randint(10, 15) == 0:
        # 大幅跳跃：25-35%的价格变化
        jump_direction = random.choice([-1, 1])
        jump_magnitude = random.uniform(0.25, 0.35)
        token_prices[token_id] += jump_direction * jump_magnitude
        print(f"\n🚨 [Mock API] 触发大幅波动！ {token_id}: {jump_direction * jump_magnitude:+.2%}\n")
    # 每5-8次轮询产生一次中等波动
    elif poll_count % random.randint(5, 8) == 0:
        jump_direction = random.choice([-1, 1])
        jump_magnitude = random.uniform(0.08, 0.15)
        token_prices[token_id] += jump_direction * jump_magnitude
        print(f"⚡ [Mock API] 中等波动: {token_id}: {jump_direction * jump_magnitude:+.2%}")
    else:
        # 正常小幅随机游走
        token_prices[token_id] += random.uniform(-0.03, 0.03)
    
    # 限制价格范围
    token_prices[token_id] = max(0.05, min(0.95, token_prices[token_id]))
    
    orderbook = generate_mock_orderbook(
        base_price=token_prices[token_id],
        volatility=0.05
    )
    
    return web.json_response(orderbook)

async def handle_health(request):
    """健康检查"""
    return web.json_response({"status": "ok"})

async def start_mock_server(app):
    """启动 Mock API 服务器"""
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    print("\n" + "="*60)
    print("✅ Mock API 服务器已启动: http://localhost:8080")
    print("="*60 + "\n")
    return runner

async def run_monitor():
    """运行监控系统"""
    # 等待 Mock API 启动
    await asyncio.sleep(1)
    
    print("\n" + "="*60)
    print("📊 启动监控系统")
    print("="*60 + "\n")
    
    # 导入并运行监控器
    from src.core.monitor import PolymarketMonitor
    from src.utils.logger import setup_logging
    import yaml
    
    # 加载配置
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    with open('config/thresholds.yaml', 'r', encoding='utf-8') as f:
        thresholds = yaml.safe_load(f)
    
    # 设置日志
    setup_logging(config['logging'])
    
    # 创建监控器
    monitor = PolymarketMonitor(
        market_url="https://polymarket.com/event/dota2-flc-liquid-2026-02-13",
        config=config,
        thresholds=thresholds
    )
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        print("\n⚠️  收到停止信号")
    except Exception as e:
        print(f"\n❌ 监控出错: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主函数"""
    # 创建 Mock API 应用
    app = web.Application()
    app.router.add_get('/events', handle_event)
    app.router.add_get('/book', handle_orderbook)
    app.router.add_get('/health', handle_health)
    
    # 启动 Mock API
    runner = await start_mock_server(app)
    
    try:
        # 运行监控
        await run_monitor()
    finally:
        # 清理
        await runner.cleanup()
        print("\n✅ 测试完成")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(0)
