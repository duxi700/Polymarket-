# Polymarket 实时监控系统

## 📋 项目简介

这是一个实时监控 Polymarket 市场的 Python 程序，专门用于识别情绪驱动的价格错配机会（Edge）。

**核心特点：**
- 🎯 **专注监控**：不自动下单，只输出信号
- 🔍 **情绪检测**：识别市场情绪导致的价格异常
- 📊 **三级信号**：多层次的 Edge 检测系统
- ⚡ **实时追踪**：2-30秒可配置的轮询间隔
- 🛡️ **噪声过滤**：智能去除虚假信号

## 🏗️ 系统架构

```
polymarket信号机器人/
│
├── config/                      # 配置文件
│   ├── config.yaml             # 系统配置
│   └── thresholds.yaml         # 信号阈值配置
│
├── src/                         # 源代码
│   ├── api/                    # API 层
│   │   ├── models.py           # 数据模型
│   │   ├── parser.py           # URL 解析
│   │   └── client.py           # API 客户端
│   │
│   ├── core/                   # 核心模块
│   │   ├── state.py            # 状态管理
│   │   └── monitor.py          # 主监控器
│   │
│   ├── detection/              # 检测引擎
│   │   ├── signals.py          # 信号定义
│   │   ├── metrics.py          # 指标计算
│   │   └── engine.py           # Edge 检测
│   │
│   ├── output/                 # 输出模块
│   │   └── console.py          # 终端输出
│   │
│   └── utils/                  # 工具函数
│       ├── logger.py           # 日志系统
│       └── rate_limiter.py     # 速率限制
│
├── logs/                        # 日志目录
├── main.py                      # 程序入口
├── requirements.txt             # 依赖列表
└── README.md                    # 本文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\\Scripts\\activate    # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置系统

配置文件位于 `config/` 目录：

- **config.yaml**: 系统配置（API、轮询、日志等）
- **thresholds.yaml**: 信号检测阈值

默认配置已可用，可根据需要调整。

### 3. 运行监控

```bash
# 方式 1: 命令行参数
python main.py "https://polymarket.com/event/your-event-slug"

# 方式 2: 交互式输入
python main.py
# 然后输入市场 URL
```

### 4. 查看日志

```bash
# 实时查看日志
tail -f logs/monitor.log

# 查看错误日志
tail -f logs/errors.log
```

## 📊 信号级别说明

### Level 1: 情绪异常（内部标记）
- **不输出到终端**
- 用于内部状态追踪
- 触发条件：价格短时间剧烈变化 + 成交量放大

### Level 2: 潜在 Edge（可选）
- **默认关闭**
- 价格处于历史极端区间
- 需在配置中启用

### Level 3: 高 EV 错配（核心信号）
- **必须输出**
- 同时满足：
  1. ✅ 价格极端变化（25%以上）
  2. ✅ 价格回归迹象（反向变动）
  3. ✅ 流动性充足（可进出）
  4. ✅ 冷却期外（15分钟间隔）

## ⚙️ 配置说明

### 轮询间隔

在 `config/config.yaml` 中调整：

```yaml
polling:
  live_market_interval: 5   # 活跃市场：5秒
  normal_market_interval: 30  # 正常市场：30秒
```

### 信号阈值

在 `config/thresholds.yaml` 中调整：

```yaml
level3:
  extreme_price_change_pct: 0.25  # 极端价格变化：25%
  rebound_min_pct: 0.05            # 最小回归：5%
  signal_cooldown_minutes: 15      # 冷却时间：15分钟
```

### 速率限制

```yaml
rate_limit:
  max_requests_per_minute: 100  # 每分钟最大100请求
```

## 📈 使用示例

### 监控单个市场

```bash
python main.py "https://polymarket.com/event/super-bowl-2026"
```

### 典型输出

```
╔════════════════════════════════════════════════════════════╗
║        Polymarket 实时 Edge 监控系统 v1.0                 ║
╚════════════════════════════════════════════════════════════╝

🚀 系统启动中...

监控市场: https://polymarket.com/event/super-bowl-2026
轮询间隔: 5 秒

✓ 准备就绪，开始监控...

============================================================
🚨 EDGE SIGNAL (Level 3 - High EV)
============================================================

Market: Super Bowl 2026 Winner
Outcome: Kansas City Chiefs

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
Always verify market conditions before taking action.

============================================================
```

## 🔧 开发指南

### 项目结构说明

- **src/api**: 与 Polymarket API 交互
- **src/core**: 核心监控逻辑和状态管理
- **src/detection**: Edge 检测算法
- **src/output**: 终端输出格式化
- **src/utils**: 工具函数（日志、速率限制）

### 添加新的检测规则

编辑 `src/detection/engine.py` 中的检测方法。

### 自定义输出格式

编辑 `src/output/console.py` 中的输出模板。

## 🛠️ 故障排查

### 无法获取市场数据

1. 检查网络连接
2. 验证 URL 格式正确
3. 查看 `logs/errors.log` 获取详细错误

### API 速率限制

- 降低轮询频率
- 增加 `rate_limit.max_requests_per_minute` 配置

### 无信号输出

- 检查阈值配置是否过于严格
- 确认市场有足够的价格波动
- 启用 Level 2 信号查看潜在 Edge

## 📝 注意事项

### ⚠️ 免责声明

- **本程序仅供监控使用，不构成投资建议**
- **信号输出不等于交易指令**
- **需要人工判断和验证**
- **请自行承担交易风险**

### 系统定位

这是一个"市场情绪雷达"，而非交易机器人。它的作用是：

- ✅ 解放你的盯盘时间
- ✅ 将"感觉不对劲"结构化
- ✅ 辅助冷静决策

而不是：
- ❌ 自动执行交易
- ❌ 预测比赛结果
- ❌ 保证盈利

## 📚 技术栈

- **Python 3.9+**: 编程语言
- **aiohttp**: 异步 HTTP 客户端
- **asyncio**: 异步 I/O
- **pydantic**: 数据验证
- **loguru**: 日志系统
- **numpy**: 数值计算
- **tenacity**: 重试机制

## 🔄 更新日志

### v1.0.0 (2026-02-14)
- ✨ 初始版本发布
- ✅ 三级信号检测系统
- ✅ 实时监控和状态管理
- ✅ 完整的配置系统
- ✅ 日志和错误处理

## 📞 支持

如有问题或建议，请查看：
- 日志文件: `logs/monitor.log` 和 `logs/errors.log`
- 配置文件: `config/config.yaml` 和 `config/thresholds.yaml`

## 📄 许可证

本项目仅供学习和研究使用。

---

**祝你交易顺利！记住：这是监控工具，不是水晶球。** 🔮
