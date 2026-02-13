"""
指标计算工具
"""

import numpy as np
from typing import List, Optional
from datetime import datetime, timedelta

from ..core.state import OutcomeState, PricePoint


class MetricsCalculator:
    """指标计算器"""
    
    @staticmethod
    def calculate_price_change_rate(
        current: float,
        previous: Optional[float],
        time_delta_minutes: float
    ) -> Optional[float]:
        """
        计算价格变化率
        
        Args:
            current: 当前价格
            previous: 之前价格
            time_delta_minutes: 时间间隔（分钟）
            
        Returns:
            价格变化率（百分比/分钟），如果无法计算则返回 None
        """
        if previous is None or previous == 0 or time_delta_minutes == 0:
            return None
        
        pct_change = (current - previous) / previous
        return pct_change / time_delta_minutes
    
    @staticmethod
    def calculate_volatility(
        price_history: List[PricePoint],
        window_minutes: int = 15
    ) -> float:
        """
        计算价格波动率（标准差）
        
        Args:
            price_history: 价格历史记录
            window_minutes: 时间窗口（分钟）
            
        Returns:
            波动率（标准差）
        """
        if len(price_history) < 2:
            return 0.0
        
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        prices = [
            p.price for p in price_history
            if p.timestamp >= cutoff
        ]
        
        if len(prices) < 2:
            return 0.0
        
        return float(np.std(prices))
    
    @staticmethod
    def is_extreme_price(
        current: float,
        price_history: List[PricePoint],
        percentile: float = 0.1
    ) -> bool:
        """
        判断当前价格是否为极端值
        
        Args:
            current: 当前价格
            price_history: 价格历史
            percentile: 分位数阈值（0.1 表示最低10%或最高90%）
            
        Returns:
            是否为极端价格
        """
        if len(price_history) < 10:
            return False
        
        prices = [p.price for p in price_history]
        lower = np.percentile(prices, percentile * 100)
        upper = np.percentile(prices, (1 - percentile) * 100)
        
        return current <= lower or current >= upper
    
    @staticmethod
    def calculate_volume_ratio(
        current_volume: float,
        historical_avg: float
    ) -> Optional[float]:
        """
        计算成交量比率
        
        Args:
            current_volume: 当前时间窗口成交量
            historical_avg: 历史平均成交量
            
        Returns:
            成交量比率，如果无法计算则返回 None
        """
        if historical_avg == 0:
            return None
        
        return current_volume / historical_avg
    
    @staticmethod
    def has_volume_spike(
        state: OutcomeState,
        threshold: float = 2.0
    ) -> bool:
        """
        检测是否存在成交量激增
        
        Args:
            state: Outcome 状态
            threshold: 阈值倍数
            
        Returns:
            是否存在成交量激增
        """
        if state.volume_15m == 0:
            return False
        
        # 计算 5 分钟成交量占 15 分钟成交量的比例
        ratio = state.volume_5m / state.volume_15m
        
        # 如果 5 分钟成交量占比过高，说明有激增
        # 正常情况下应该是 5/15 = 0.33
        return ratio > (threshold * 0.33)
    
    @staticmethod
    def calculate_spread_pct(bid: Optional[float], ask: Optional[float]) -> Optional[float]:
        """
        计算买卖价差百分比
        
        Args:
            bid: 最佳买价
            ask: 最佳卖价
            
        Returns:
            价差百分比，如果无法计算则返回 None
        """
        if bid is None or ask is None or bid == 0:
            return None
        
        spread = ask - bid
        return spread / bid
    
    @staticmethod
    def detect_price_rebound(
        state: OutcomeState,
        min_rebound_pct: float = 0.05
    ) -> Optional[str]:
        """
        检测价格回归迹象
        
        Args:
            state: Outcome 状态
            min_rebound_pct: 最小回归百分比
            
        Returns:
            回归描述，如果没有回归则返回 None
        """
        if state.price_1m_ago is None or state.price_5m_ago is None:
            return None
        
        # 计算 5 分钟前到 1 分钟前的变化（主趋势）
        move_5m_to_1m = state.price_1m_ago - state.price_5m_ago
        
        # 计算 1 分钟前到现在的变化（最近趋势）
        move_1m_to_now = state.current_price - state.price_1m_ago
        
        # 检查是否方向相反（回归）
        if move_5m_to_1m * move_1m_to_now < 0:  # 方向相反
            rebound_magnitude = abs(move_1m_to_now) / abs(move_5m_to_1m) if move_5m_to_1m != 0 else 0
            
            if rebound_magnitude >= min_rebound_pct:
                direction = "向上" if move_1m_to_now > 0 else "向下"
                return f"价格{direction}回归 ({rebound_magnitude:.1%})"
        
        return None
    
    @staticmethod
    def check_liquidity(
        bid_depth: float,
        ask_depth: float,
        min_depth: float = 50.0
    ) -> bool:
        """
        检查流动性是否充足
        
        Args:
            bid_depth: 买单深度
            ask_depth: 卖单深度
            min_depth: 最小深度要求
            
        Returns:
            流动性是否充足
        """
        return bid_depth >= min_depth and ask_depth >= min_depth
