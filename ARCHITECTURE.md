# Polymarket 实时监控系统 - 架构文档

## 📐 系统架构概览

本系统采用模块化设计，实现了一个实时监控 Polymarket 市场的 Edge 检测系统。

### 系统流程图

```
┌─────────────────┐
│  Market URL     │
│  用户输入        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ MarketParser    │  解析 URL，获取市场信息
│ (API层)         │  ├─ Gamma API: 市场元数据
└────────┬────────┘  └─ 提取 token_ids
         │
         ▼
┌─────────────────┐
│ OutcomeState    │  为每个 outcome 初始化状态
│ (状态管理)      │  ├─ 价格历史缓存
└────────┬────────┘  └─ 时间窗口管理
         │
         ▼
┌─────────────────────────────────────┐
│     监控循环 (每 N 秒)               │
│  ┌───────────────────────────────┐  │
│  │ 1. PolymarketClient           │  │
│  │    批量获取订单簿              │  │
│  │    ├─ CLOB API: /book         │  │
│  │    └─ 速率限制 + 重试          │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │ 2. 更新状态                    │  │
│  │    ├─ 添加价格点               │  │
│  │    ├─ 计算指标                 │  │
│  │    └─ 维护时间窗口             │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │ 3. EdgeDetectionEngine        │  │
│  │    ├─ Level 1: 情绪异常检测   │  │
│  │    ├─ Level 2: 潜在 Edge      │  │
│  │    └─ Level 3: 高 EV 错配     │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │ 4. 信号过滤                    │  │
│  │    ├─ 噪声过滤                 │  │
│  │    ├─ 冷却期检查               │  │
│  │    └─ 流动性验证               │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │ 5. ConsoleOutput (如有信号)   │  │
│  │    └─ 格式化输出到终端         │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## 🏛️ 核心模块详解

### 1. API 层 (`src/api/`)

#### 1.1 MarketParser
**职责**: 解析 Polymarket URL，获取市场信息

```python
# 支持的 URL 格式
https://polymarket.com/event/slug   → 调用 Gamma API /events
https://polymarket.com/market/slug  → 调用 Gamma API /markets

# 输出
MarketInfo {
    market_id: str          # Condition ID
    event_name: str         # 事件名称
    question: str           # 市场问题
    outcomes: [OutcomeInfo] # 所有可能的结果
}
```

#### 1.2 PolymarketClient
**职责**: 与 CLOB API 交互，获取实时市场数据

**核心功能**:
- `fetch_orderbook(token_id)`: 获取单个订单簿
- `fetch_orderbooks_batch(token_ids)`: 批量获取（并发）
- 自动重试（exponential backoff）
- 速率限制（100 请求/分钟）

**API 端点**:
- `GET /book?token_id=xxx`: 订单簿数据
- `GET /trades?token_id=xxx`: 交易记录（可选）

#### 1.3 Models
**数据模型** (使用 Pydantic):
- `MarketInfo`: 市场信息
- `OutcomeInfo`: 结果信息
- `OrderBookData`: 订单簿数据
- `OrderBookLevel`: 订单簿价格层级

### 2. 核心模块 (`src/core/`)

#### 2.1 OutcomeState
**职责**: 维护每个 outcome 的状态和历史数据

**数据结构**:
```python
OutcomeState {
    # 基础信息
    outcome_name: str
    token_id: str
    
    # 滚动窗口（自动限制 1000 个点）
    price_history: deque[PricePoint]
    
    # 当前状态
    current_price: float
    current_bid: float
    current_ask: float
    
    # 时间点缓存
    price_1m_ago: float
    price_5m_ago: float
    price_15m_ago: float
    price_30m_ago: float
    
    # 统计指标
    volume_5m: float
    volatility_15m: float
    
    # 信号控制
    last_signal_time: datetime
    signal_cooldown_minutes: int
}
```

**核心方法**:
- `add_price_point()`: 添加新数据点，自动更新所有指标
- `get_price_change_pct()`: 计算价格变化百分比
- `is_extreme_price()`: 判断是否极端价格
- `can_emit_signal()`: 检查冷却期

#### 2.2 PolymarketMonitor
**职责**: 主监控器，协调所有模块

**生命周期**:
1. 初始化：加载配置，创建组件
2. 解析市场：获取 market info
3. 初始化状态：为每个 outcome 创建 OutcomeState
4. 监控循环：
   - 获取数据 → 更新状态 → 检测信号 → 输出
   - 异常处理和重试
5. 清理：关闭会话，输出统计

### 3. 检测引擎 (`src/detection/`)

#### 3.1 EdgeDetectionEngine
**职责**: 核心信号检测逻辑

**三级信号系统**:

##### Level 1: 情绪异常（内部标记）
```python
条件:
  - 价格变化 >= 15% (5分钟内)
  - 成交量放大 >= 2倍

作用: 内部状态标记，不输出
```

##### Level 2: 潜在 Edge（可选）
```python
条件:
  - 价格处于历史 10% 分位数（极端区间）
  - 市场状态未出现不可逆信息

输出: 可选（默认关闭）
```

##### Level 3: 高 EV 错配（核心）
```python
必须同时满足:
  1. 价格极端变化 >= 25% (10分钟内)
  2. 价格回归迹象 >= 5% (反向变动)
  3. 流动性充足:
     - 买卖盘深度 >= 50
     - 价差 <= 5%
  4. 冷却期外 (>= 15分钟)

输出: 必须
```

**检测流程**:
```python
def detect(state: OutcomeState) -> Optional[EdgeSignal]:
    # 1. 基础检查
    if not has_sufficient_data():
        return None
    
    # 2. 噪声过滤
    if not pass_noise_filters():
        return None
    
    # 3. Level 1 检测（内部标记）
    if is_emotion_anomaly():
        mark_internally()
    
    # 4. Level 3 检测（主要）
    signal = detect_high_ev_edge()
    if signal and can_emit_signal():
        record_signal_time()
        return signal
    
    return None
```

#### 3.2 MetricsCalculator
**职责**: 指标计算工具

**核心指标**:
- `calculate_volatility()`: 标准差波动率
- `is_extreme_price()`: 分位数判断
- `detect_price_rebound()`: 回归检测
- `has_volume_spike()`: 成交量激增
- `check_liquidity()`: 流动性检查

### 4. 输出模块 (`src/output/`)

#### 4.1 ConsoleOutput
**职责**: 终端输出格式化

**输出格式** (严格按需求):
```
============================================================
🚨 EDGE SIGNAL (Level 3 - High EV)
============================================================

Market: <事件名称>
Outcome: <YES / NO / 队伍名>

Price Movement:
  0.6500 → 0.4200 📉
  Change: -35.4% in 10 min

Market State:
  Best Bid: 0.4180
  Best Ask: 0.4220
  Spread: 0.96%
  Volume Spike: YES
  Volatility: 0.0824

Edge Indicators:
  1. 情绪驱动的恐慌性抛售 (35.4% in 10min)
  2. 价格向上回归 (12.3%)
  3. 流动性充足，可进出

⚠️  Note:
This is a market signal only, not a trade instruction.

============================================================
```

### 5. 工具模块 (`src/utils/`)

#### 5.1 RateLimiter
**职责**: API 速率限制

**实现**: 滑动窗口算法
```python
# 100 请求/分钟
rate_limiter = RateLimiter(max_requests=100, time_window=60)

await rate_limiter.acquire()  # 阻塞直到可以发送
```

#### 5.2 Logger
**职责**: 日志系统

**配置**:
- 控制台：INFO 级别，彩色输出
- 文件：DEBUG 级别，详细信息
- 错误文件：ERROR 级别，单独记录

## 🔄 数据流详解

### 完整数据流

```
1. URL 输入
   └─> MarketParser.parse_market_url()
       └─> Gamma API: GET /events or /markets
           └─> 返回 MarketInfo

2. 状态初始化
   └─> 为每个 outcome 创建 OutcomeState
       └─> 初始化空的 price_history deque

3. 监控循环开始
   └─> PolymarketClient.fetch_orderbooks_batch()
       └─> CLOB API: GET /book?token_id=xxx (并发)
           └─> 返回 OrderBookData[]

4. 状态更新
   └─> 对每个 outcome:
       └─> OutcomeState.add_price_point()
           ├─> 添加到 price_history
           ├─> 更新时间点缓存 (1m, 5m, 15m)
           ├─> 计算成交量 (5m, 15m)
           └─> 计算波动率

5. Edge 检测
   └─> EdgeDetectionEngine.detect(state)
       ├─> _has_sufficient_data()
       ├─> _pass_noise_filters()
       ├─> _is_emotion_anomaly()
       └─> _detect_high_ev_edge()
           ├─> _check_extreme_price_move()
           ├─> _check_price_rebound()
           └─> _check_liquidity()

6. 信号输出（如果有）
   └─> ConsoleOutput.print_signal()
       └─> 格式化输出到终端

7. 等待下一个周期
   └─> asyncio.sleep(poll_interval)
```

## ⚙️ 配置系统

### config.yaml
```yaml
api:
  clob_url: "https://clob.polymarket.com"
  gamma_url: "https://gamma-api.polymarket.com"
  timeout: 10
  max_retries: 3

polling:
  live_market_interval: 5    # 活跃市场
  normal_market_interval: 30  # 正常市场

rate_limit:
  max_requests_per_minute: 100

cache:
  max_history_points: 1000
  time_windows: [1, 5, 15, 30]

logging:
  level: "INFO"
  file: "logs/monitor.log"
```

### thresholds.yaml
```yaml
level1:  # 情绪异常
  price_change_pct: 0.15
  time_window_seconds: 300
  volume_spike_ratio: 2.0

level3:  # 高 EV 错配
  extreme_price_change_pct: 0.25
  extreme_time_window_min: 10
  rebound_min_pct: 0.05
  min_bid_ask_depth: 50
  max_spread_pct: 0.05
  signal_cooldown_minutes: 15

filters:  # 噪声过滤
  min_price_change: 0.01
  min_volume: 10
  require_both_sides: true
  min_data_points: 10
```

## 🎯 关键设计决策

### 1. 为什么使用轮询而非 WebSocket？
- ✅ 简单可靠，易于实现
- ✅ 易于控制频率和错误处理
- ✅ 降低复杂度，适合 MVP
- ❌ WebSocket 增加连接管理复杂度

### 2. 为什么使用 deque 而非数据库？
- ✅ 内存操作，性能高
- ✅ 自动限制大小（maxlen=1000）
- ✅ 简化部署，无需外部依赖
- ⚠️ 重启后数据丢失（可接受）

### 3. 为什么三级信号系统？
- Level 1: 早期预警，内部状态
- Level 2: 可选提示，降低噪音
- Level 3: 高置信度，核心价值

### 4. 冷却机制的意义
- 避免同一 outcome 短时间内重复信号
- 减少信息过载
- 符合"宁可少而准"的原则

## 📊 性能指标

### 资源使用
- **CPU**: 低（主要是 I/O 等待）
- **内存**: < 100 MB（1000 点 × N outcomes）
- **网络**: 取决于轮询频率
  - 5秒间隔：~12 请求/分钟/outcome
  - 30秒间隔：~2 请求/分钟/outcome

### 可扩展性
- **单市场**: 无限制
- **多 outcomes**: 并发获取，O(1) 时间
- **多市场**: 需要多进程或线程（未实现）

## 🔐 安全考虑

1. **API 速率限制**: 防止被封禁
2. **异常处理**: 所有网络请求都有重试
3. **数据验证**: Pydantic 模型验证
4. **日志隔离**: 错误日志单独记录

## 🚀 未来扩展方向

### 短期
- [ ] 添加成交量追踪（从 trades API）
- [ ] 支持多市场并发监控
- [ ] 添加信号历史记录（JSON/CSV）
- [ ] Web UI 可视化

### 中期
- [ ] 机器学习辅助信号过滤
- [ ] 历史数据回测系统
- [ ] Telegram/Discord 通知
- [ ] 数据持久化（SQLite）

### 长期
- [ ] 自动交易模块（可选）
- [ ] 策略回测框架
- [ ] 多交易所支持
- [ ] 云部署方案

## 📚 技术栈总结

| 层级 | 技术 | 用途 |
|------|------|------|
| 语言 | Python 3.9+ | 主语言 |
| 异步 | asyncio, aiohttp | 并发 I/O |
| 数据 | Pydantic | 验证和序列化 |
| 数值 | NumPy | 统计计算 |
| 日志 | Loguru | 结构化日志 |
| 重试 | Tenacity | 指数退避 |
| 配置 | PyYAML | YAML 解析 |
| 类型 | Type Hints | 静态类型检查 |

## 🎓 核心算法

### 价格回归检测
```python
def detect_price_rebound(state):
    # 主趋势（5分钟前 → 1分钟前）
    move_5m_to_1m = price_1m - price_5m
    
    # 最近趋势（1分钟前 → 现在）
    move_1m_to_now = price_now - price_1m
    
    # 方向相反 = 回归
    if move_5m_to_1m * move_1m_to_now < 0:
        rebound_magnitude = abs(move_1m_to_now) / abs(move_5m_to_1m)
        if rebound_magnitude >= threshold:
            return True
    
    return False
```

### 极端价格判断
```python
def is_extreme_price(current, history, percentile=0.1):
    prices = [p.price for p in history]
    
    lower = np.percentile(prices, percentile * 100)  # 10%
    upper = np.percentile(prices, (1-percentile) * 100)  # 90%
    
    return current <= lower or current >= upper
```

---

**本架构文档详细描述了系统的设计思路和实现细节，可作为维护和扩展的参考。**
