#!/usr/bin/env python3
"""
快速触发信号的测试脚本 - 强制产生大幅波动
"""
import asyncio
import sys
from aiohttp import web
import random
import time

MOCK_EVENT_DATA = {
    "slug": "dota2-flc-liquid-2026-02-13",
    "title": "Dota2: FLC vs Liquid",
    "markets": [{
        "conditionId": "0x1234567890abcdef",
        "question": "Will FLC win?",
        "tokens": [
            {"outcome": "Yes", "token_id": "token-yes-1", "outcome_id": "0xyes1", "price": "0.45"},
            {"outcome": "No", "token_id": "token-no-1", "outcome_id": "0xno1", "price": "0.55"}
        ]
    }]
}

token_prices = {}
token_poll_count = {}
last_extreme_jump = {}  # 记录上次极端跳跃：{token_id: {'direction': 1/-1, 'poll': count}}

def generate_mock_orderbook(base_price=0.5, volatility=0.05):
    price_shift = random.uniform(-volatility, volatility)
    mid_price = max(0.01, min(0.99, base_price + price_shift))
    
    # 增加流动性：每档1000-3000，确保总流动性 > 5000
    bids = [{"price": f"{max(0.01, mid_price - 0.01 * (i + 1)):.4f}", "size": f"{random.uniform(1000, 3000):.2f}"} for i in range(5)]
    asks = [{"price": f"{min(0.99, mid_price + 0.01 * (i + 1)):.4f}", "size": f"{random.uniform(1000, 3000):.2f}"} for i in range(5)]
    
    return {"bids": bids, "asks": asks, "timestamp": int(time.time() * 1000)}

async def handle_event(request):
    slug = request.query.get('slug', '')
    if slug == MOCK_EVENT_DATA['slug']:
        print(f"[Mock API] 事件查询: slug={slug}")
        return web.json_response([MOCK_EVENT_DATA])
    return web.json_response({"error": "Event not found"}, status=404)

async def handle_orderbook(request):
    token_id = request.query.get('token_id', '')
    
    if token_id not in token_prices:
        token_prices[token_id] = random.uniform(0.45, 0.55)
        token_poll_count[token_id] = 0
        last_extreme_jump[token_id] = None
    
    token_poll_count[token_id] += 1
    poll_count = token_poll_count[token_id]
    
    # 检查是否需要产生回弹（在极端跳跃后的1-2次轮询）
    if last_extreme_jump[token_id] is not None:
        jump_info = last_extreme_jump[token_id]
        polls_since_jump = poll_count - jump_info['poll']
        
        if polls_since_jump == 1:
            # 第一次回弹：5-8%反向
            rebound_pct = random.uniform(0.05, 0.08)
            old_price = token_prices[token_id]
            token_prices[token_id] += -jump_info['direction'] * rebound_pct
            token_prices[token_id] = max(0.05, min(0.95, token_prices[token_id]))
            print(f"🔄 [Mock API] 回弹！ {token_id}: {old_price:.4f} → {token_prices[token_id]:.4f} ({-jump_info['direction'] * rebound_pct:+.2%})")
        elif polls_since_jump >= 2:
            # 清除跳跃记录
            last_extreme_jump[token_id] = None
            print(f"✅ [Mock API] 回弹周期结束: {token_id}")
    # 每3-5次轮询产生极端波动（且不在回弹期）
    elif poll_count % random.randint(3, 5) == 0 and poll_count > 5:
        # 超大幅跳跃：28-38%
        jump_direction = random.choice([-1, 1])
        jump_magnitude = random.uniform(0.28, 0.38)
        old_price = token_prices[token_id]
        token_prices[token_id] += jump_direction * jump_magnitude
        token_prices[token_id] = max(0.05, min(0.95, token_prices[token_id]))
        
        # 记录跳跃信息，用于后续回弹
        last_extreme_jump[token_id] = {'direction': jump_direction, 'poll': poll_count}
        
        print(f"\n🚨🚨🚨 [Mock API] 极端波动！ {token_id}")
        print(f"    价格: {old_price:.4f} → {token_prices[token_id]:.4f} ({jump_direction * jump_magnitude:+.2%})")
        print(f"    下次将产生反向回弹\n")
    elif poll_count % 2 == 0 and poll_count > 3:
        # 中等波动：12-18%
        jump_direction = random.choice([-1, 1])
        jump_magnitude = random.uniform(0.12, 0.18)
        token_prices[token_id] += jump_direction * jump_magnitude
        token_prices[token_id] = max(0.05, min(0.95, token_prices[token_id]))
        print(f"⚡ [Mock API] 强波动: {token_id}: {jump_direction * jump_magnitude:+.2%}")
    else:
        # 正常小幅随机游走
        token_prices[token_id] += random.uniform(-0.05, 0.05)
        token_prices[token_id] = max(0.05, min(0.95, token_prices[token_id]))
    
    orderbook = generate_mock_orderbook(base_price=token_prices[token_id], volatility=0.08)
    
    print(f"[Mock API] 📊 {token_id}: {token_prices[token_id]:.4f} (第{poll_count}次)")
    
    return web.json_response(orderbook)

async def handle_health(request):
    return web.json_response({"status": "ok"})

async def start_mock_server(app):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    print("\n" + "="*60)
    print("✅ Mock API 服务器已启动 (激进模式)")
    print("="*60 + "\n")
    return runner

async def run_monitor():
    await asyncio.sleep(1)
    
    print("\n" + "="*60)
    print("📊 启动监控系统 (快速信号触发模式)")
    print("="*60 + "\n")
    
    from src.core.monitor import PolymarketMonitor
    from src.utils.logger import setup_logging
    import yaml
    
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    with open('config/thresholds.yaml', 'r', encoding='utf-8') as f:
        thresholds = yaml.safe_load(f)
    
    setup_logging(config['logging'])
    
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
    app = web.Application()
    app.router.add_get('/events', handle_event)
    app.router.add_get('/book', handle_orderbook)
    app.router.add_get('/health', handle_health)
    
    runner = await start_mock_server(app)
    
    try:
        await run_monitor()
    finally:
        await runner.cleanup()
        print("\n✅ 测试完成")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(0)
