"""
状态管理模块
维护市场数据的时间序列和计算指标
"""

from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timedelta
from typing import Optional, Deque, List
import numpy as np


@dataclass
class PricePoint:
    """价格数据点"""
    timestamp: datetime
    price: float
    volume: float = 0.0
    bid: Optional[float] = None
    ask: Optional[float] = None


@dataclass
class OutcomeState:
    """Outcome 状态管理器"""
    outcome_name: str
    token_id: str
    
    # 滚动窗口历史数据（自动限制大小）
    price_history: Deque[PricePoint] = field(default_factory=lambda: deque(maxlen=1000))
    
    # 当前状态
    current_price: float = 0.0
    current_bid: Optional[float] = None
    current_ask: Optional[float] = None
    current_volume: float = 0.0
    
    # 关键时间点价格缓存
    price_1m_ago: Optional[float] = None
    price_5m_ago: Optional[float] = None
    price_15m_ago: Optional[float] = None
    price_30m_ago: Optional[float] = None
    
    # 统计指标
    volume_5m: float = 0.0
    volume_15m: float = 0.0
    volatility_15m: float = 0.0
    
    # 信号冷却
    last_signal_time: Optional[datetime] = None
    signal_cooldown_minutes: int = 15
    
    # 内部状态标记
    emotion_anomaly_detected: bool = False
    last_emotion_check: Optional[datetime] = None
    
    def add_price_point(
        self,
        price: float,
        volume: float = 0.0,
        bid: Optional[float] = None,
        ask: Optional[float] = None
    ):
        """添加新的价格数据点并更新所有指标"""
        now = datetime.now()
        
        # 添加到历史记录
        self.price_history.append(PricePoint(
            timestamp=now,
            price=price,
            volume=volume,
            bid=bid,
            ask=ask
        ))
        
        # 更新当前状态
        self.current_price = price
        self.current_bid = bid
        self.current_ask = ask
        self.current_volume = volume
        
        # 更新时间点缓存
        self.price_1m_ago = self._get_price_at(now - timedelta(minutes=1))
        self.price_5m_ago = self._get_price_at(now - timedelta(minutes=5))
        self.price_15m_ago = self._get_price_at(now - timedelta(minutes=15))
        self.price_30m_ago = self._get_price_at(now - timedelta(minutes=30))
        
        # 更新统计指标
        self.volume_5m = self._get_volume_in_window(timedelta(minutes=5))
        self.volume_15m = self._get_volume_in_window(timedelta(minutes=15))
        self.volatility_15m = self._calculate_volatility(timedelta(minutes=15))
    
    def _get_price_at(self, target_time: datetime) -> Optional[float]:
        """获取指定时间点的价格（最近邻）"""
        if not self.price_history:
            return None
        
        # 找到最接近目标时间的价格点
        closest = min(
            self.price_history,
            key=lambda p: abs((p.timestamp - target_time).total_seconds())
        )
        
        # 只有在时间差小于2倍轮询间隔时才返回（避免数据过时）
        time_diff = abs((closest.timestamp - target_time).total_seconds())
        if time_diff < 120:  # 2分钟容差
            return closest.price
        
        return None
    
    def _get_volume_in_window(self, window: timedelta) -> float:
        """计算时间窗口内的成交量"""
        if not self.price_history:
            return 0.0
        
        cutoff = datetime.now() - window
        return sum(
            p.volume for p in self.price_history 
            if p.timestamp >= cutoff
        )
    
    def _calculate_volatility(self, window: timedelta) -> float:
        """计算时间窗口内的价格波动率（标准差）"""
        if len(self.price_history) < 2:
            return 0.0
        
        cutoff = datetime.now() - window
        prices = [
            p.price for p in self.price_history 
            if p.timestamp >= cutoff
        ]
        
        if len(prices) < 2:
            return 0.0
        
        return float(np.std(prices))
    
    def get_price_change_pct(self, minutes_ago: int) -> Optional[float]:
        """计算相对于N分钟前的价格变化百分比"""
        past_price = None
        
        if minutes_ago == 1:
            past_price = self.price_1m_ago
        elif minutes_ago == 5:
            past_price = self.price_5m_ago
        elif minutes_ago == 15:
            past_price = self.price_15m_ago
        elif minutes_ago == 30:
            past_price = self.price_30m_ago
        
        if past_price is None or past_price == 0:
            return None
        
        return (self.current_price - past_price) / past_price
    
    def get_price_change_rate(self, minutes_ago: int) -> Optional[float]:
        """计算价格变化率（百分比/分钟）"""
        change_pct = self.get_price_change_pct(minutes_ago)
        if change_pct is None:
            return None
        return change_pct / minutes_ago
    
    def is_extreme_price(self, percentile: float = 0.1) -> bool:
        """判断当前价格是否处于极端区间"""
        if len(self.price_history) < 10:
            return False
        
        prices = [p.price for p in self.price_history]
        lower = np.percentile(prices, percentile * 100)
        upper = np.percentile(prices, (1 - percentile) * 100)
        
        return self.current_price <= lower or self.current_price >= upper
    
    def can_emit_signal(self) -> bool:
        """检查是否在信号冷却期"""
        if self.last_signal_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_signal_time).total_seconds() / 60
        return elapsed >= self.signal_cooldown_minutes
    
    def get_remaining_cooldown(self) -> Optional[float]:
        """获取剩余冷却时间（分钟）"""
        if self.last_signal_time is None:
            return None
        
        elapsed = (datetime.now() - self.last_signal_time).total_seconds() / 60
        remaining = self.signal_cooldown_minutes - elapsed
        
        return max(0, remaining)
    
    def record_signal(self):
        """记录信号发出时间"""
        self.last_signal_time = datetime.now()
    
    def has_sufficient_data(self, min_points: int = 10) -> bool:
        """检查是否有足够的数据进行分析"""
        return len(self.price_history) >= min_points
    
    def get_price_history_in_window(self, window: timedelta) -> List[PricePoint]:
        """获取指定时间窗口内的价格历史"""
        cutoff = datetime.now() - window
        return [p for p in self.price_history if p.timestamp >= cutoff]
