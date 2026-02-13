"""
信号定义和数据结构
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class SignalLevel(Enum):
    """信号级别"""
    NONE = 0
    EMOTION_ANOMALY = 1  # Level 1: 情绪异常（内部标记）
    POTENTIAL_EDGE = 2    # Level 2: 潜在 Edge（可选输出）
    HIGH_EV_EDGE = 3      # Level 3: 高 EV 错配（必须输出）


@dataclass
class EdgeSignal:
    """Edge 信号数据结构"""
    level: SignalLevel
    outcome_name: str
    token_id: str
    
    # 价格信息
    current_price: float
    previous_price: Optional[float]
    change_pct: float
    time_window_minutes: float
    
    # 市场状态
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    spread_pct: Optional[float] = None
    
    # 成交量和流动性
    volume_spike: bool = False
    bid_depth: float = 0.0
    ask_depth: float = 0.0
    
    # 波动率
    volatility: float = 0.0
    
    # 原因列表
    reasons: List[str] = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []
    
    def add_reason(self, reason: str):
        """添加信号原因"""
        self.reasons.append(reason)
    
    def get_direction(self) -> str:
        """获取价格变动方向"""
        if self.previous_price is None:
            return "unknown"
        
        if self.current_price > self.previous_price:
            return "up"
        elif self.current_price < self.previous_price:
            return "down"
        else:
            return "flat"
    
    def is_price_extreme_low(self) -> bool:
        """判断是否为极端低价"""
        return self.change_pct < -0.2  # 下跌超过 20%
    
    def is_price_extreme_high(self) -> bool:
        """判断是否为极端高价"""
        return self.change_pct > 0.2  # 上涨超过 20%
