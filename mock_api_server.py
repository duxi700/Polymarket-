"""
Polymarket Mock API Server
模拟 Polymarket API 服务器用于本地测试
"""
from aiohttp import web
import json
import random
import time

# 模拟事件数据
MOCK_EVENT_DATA = {
    "slug": "dota2-flc-liquid-2026-02-13",
    "title": "Dota2: FLC vs Liquid",
    "markets": [
        {
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
        }
    ]
}

# 模拟订单簿数据生成器
def generate_mock_orderbook(base_price=0.5, volatility=0.05):
    """生成模拟的订单簿数据"""
    # 添加随机波动
    price_shift = random.uniform(-volatility, volatility)
    mid_price = max(0.01, min(0.99, base_price + price_shift))
    
    # 生成买单和卖单
    bids = []
    asks = []
    
    # 生成5档买单
    for i in range(5):
        price = mid_price - 0.01 * (i + 1)
        size = random.uniform(100, 1000)
        if price > 0.01:
            bids.append({"price": f"{price:.4f}", "size": f"{size:.2f}"})
    
    # 生成5档卖单
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

# 存储每个token的基础价格（用于生成连续的价格序列）
token_prices = {}
token_poll_count = {}  # 记录每个token的轮询次数

async def handle_event(request):
    """处理事件查询请求 GET /events"""
    slug = request.query.get('slug', '')
    
    if slug == MOCK_EVENT_DATA['slug']:
        print(f"[Mock API] Event request: slug={slug}")
        # 返回数组格式，符合真实API的响应结构
        return web.json_response([MOCK_EVENT_DATA])
    else:
        return web.json_response({"error": "Event not found"}, status=404)

async def handle_orderbook(request):
    """处理订单簿查询请求 GET /book"""
    token_id = request.query.get('token_id', '')
    
    print(f"[Mock API] Orderbook request: token_id={token_id}")
    
    # 为每个token维护独立的价格走势
    if token_id not in token_prices:
        # 初始化基础价格
        if 'yes' in token_id.lower():
            token_prices[token_id] = random.uniform(0.4, 0.6)
        else:
            token_prices[token_id] = random.uniform(0.4, 0.6)
        token_poll_count[token_id] = 0
    
    token_poll_count[token_id] += 1
    poll_count = token_poll_count[token_id]
    
    # 每10-15次轮询产生一次大幅波动（模拟情绪驱动的价格错配）
    if poll_count % random.randint(10, 15) == 0:
        # 大幅跳跃：30-40%的价格变化
        jump_direction = random.choice([-1, 1])
        jump_magnitude = random.uniform(0.25, 0.35)  # 25-35%跳跃
        token_prices[token_id] += jump_direction * jump_magnitude
        print(f"\n🚨 [Mock API] 触发大幅波动！ {token_id}: {jump_direction * jump_magnitude:+.2%}\n")
    # 每5-8次轮询产生一次中等波动
    elif poll_count % random.randint(5, 8) == 0:
        # 中等波动：10-20%的价格变化
        jump_direction = random.choice([-1, 1])
        jump_magnitude = random.uniform(0.08, 0.15)
        token_prices[token_id] += jump_direction * jump_magnitude
        print(f"⚡ [Mock API] 中等波动: {token_id}: {jump_direction * jump_magnitude:+.2%}")
    else:
        # 正常小幅随机游走
        token_prices[token_id] += random.uniform(-0.03, 0.03)
    
    # 限制价格范围
    token_prices[token_id] = max(0.05, min(0.95, token_prices[token_id]))
    
    # 生成订单簿
    orderbook = generate_mock_orderbook(
        base_price=token_prices[token_id],
        volatility=0.05  # 提高基础波动率到5%
    )
    
    return web.json_response(orderbook)

async def handle_health(request):
    """健康检查端点"""
    return web.json_response({"status": "ok", "message": "Mock API Server Running"})

def create_app():
    """创建应用"""
    app = web.Application()
    
    # 添加路由
    app.router.add_get('/events', handle_event)
    app.router.add_get('/book', handle_orderbook)
    app.router.add_get('/health', handle_health)
    
    return app

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Polymarket Mock API Server Starting...")
    print("="*60)
    print("\n📡 Available Endpoints:")
    print("  - GET http://localhost:8080/events?slug=dota2-flc-liquid-2026-02-13")
    print("  - GET http://localhost:8080/book?token_id=<token_id>")
    print("  - GET http://localhost:8080/health")
    print("\n✅ Server ready at http://localhost:8080")
    print("="*60 + "\n")
    
    app = create_app()
    web.run_app(app, host='localhost', port=8080)
