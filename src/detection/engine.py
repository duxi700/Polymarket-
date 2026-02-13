"""
Edge 检测引擎
核心信号判断逻辑
"""

from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger

from ..core.state import OutcomeState
from .signals import SignalLevel, EdgeSignal
from .metrics import MetricsCalculator


class EdgeDetectionEngine:
    """Edge 检测引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化检测引擎
        
        Args:
            config: 阈值配置字典
        """
        self.config = config
        self.level1_config = config.get('level1', {})
        self.level2_config = config.get('level2', {})
        self.level3_config = config.get('level3', {})
        self.filters_config = config.get('filters', {})
        
        # 信号冷却管理
        self.cooldown_minutes = self.level3_config.get('signal_cooldown_minutes', 15)
    
    def detect(self, state: OutcomeState) -> Optional[EdgeSignal]:
        """
        执行 Edge 检测
        
        Args:
            state: Outcome 状态
            
        Returns:
            EdgeSignal 如果检测到信号，否则返回 None
        """
        # 基础检查
        if not self._has_sufficient_data(state):
            return None
        
        # 噪声过滤
        if not self._pass_noise_filters(state):
            return None
        
        # Level 1: 情绪异常检测（内部标记）
        if self._is_emotion_anomaly(state):
            state.emotion_anomaly_detected = True
            state.last_emotion_check = datetime.now()
            logger.debug(f"[{state.outcome_name}] 检测到情绪异常（Level 1）")
        
        # Level 2: 潜在 Edge 检测（可选，默认关闭）
        if self.level2_config.get('enabled', False):
            if signal := self._detect_potential_edge(state):
                logger.info(f"[{state.outcome_name}] 检测到潜在 Edge（Level 2）")
                return signal
        
        # Level 3: 高 EV 错配检测（主要信号）
        if self.level3_config.get('enabled', True):
            if signal := self._detect_high_ev_edge(state):
                # 检查冷却期
                if state.can_emit_signal():
                    state.record_signal()
                    logger.warning(f"[{state.outcome_name}] 🚨 检测到高 EV Edge 信号！（Level 3）")
                    return signal
                else:
                    remaining = state.get_remaining_cooldown()
                    logger.debug(
                        f"[{state.outcome_name}] 信号在冷却期内，剩余 {remaining:.1f} 分钟"
                    )
        
        return None
    
    def _has_sufficient_data(self, state: OutcomeState) -> bool:
        """检查是否有足够的数据进行分析"""
        min_points = self.filters_config.get('min_data_points', 10)
        return state.has_sufficient_data(min_points)
    
    def _pass_noise_filters(self, state: OutcomeState) -> bool:
        """噪声过滤"""
        # 最小价格变化检查
        min_change = self.filters_config.get('min_price_change', 0.01)
        change_5m = state.get_price_change_pct(5)
        
        if change_5m is not None and abs(change_5m) < min_change:
            return False
        
        # 最小成交量检查
        min_volume = self.filters_config.get('min_volume', 10)
        if state.volume_5m < min_volume:
            return False
        
        # 买卖双边检查
        if self.filters_config.get('require_both_sides', True):
            if state.current_bid is None or state.current_ask is None:
                return False
        
        return True
    
    def _is_emotion_anomaly(self, state: OutcomeState) -> bool:
        """
        检测 Level 1: 情绪异常
        内部标记，不输出
        """
        if not self.level1_config.get('enabled', True):
            return False
        
        threshold = self.level1_config.get('price_change_pct', 0.15)
        volume_ratio = self.level1_config.get('volume_spike_ratio', 2.0)
        
        # 检查价格剧烈变化
        change_5m = state.get_price_change_pct(5)
        if change_5m is None or abs(change_5m) < threshold:
            return False
        
        # 检查成交量放大
        has_volume_spike = MetricsCalculator.has_volume_spike(state, volume_ratio)
        
        return has_volume_spike
    
    def _detect_potential_edge(self, state: OutcomeState) -> Optional[EdgeSignal]:
        """
        检测 Level 2: 潜在 Edge
        可选输出，默认关闭
        """
        percentile = self.level2_config.get('extreme_percentile', 0.1)
        
        # 检查价格是否处于极端区间
        if not MetricsCalculator.is_extreme_price(
            state.current_price,
            list(state.price_history),
            percentile
        ):
            return None
        
        # 构建信号
        change_15m = state.get_price_change_pct(15)
        
        signal = EdgeSignal(
            level=SignalLevel.POTENTIAL_EDGE,
            outcome_name=state.outcome_name,
            token_id=state.token_id,
            current_price=state.current_price,
            previous_price=state.price_15m_ago,
            change_pct=change_15m or 0.0,
            time_window_minutes=15,
            best_bid=state.current_bid,
            best_ask=state.current_ask,
            volatility=state.volatility_15m,
            reasons=["价格处于历史极端区间"]
        )
        
        return signal
    
    def _detect_high_ev_edge(self, state: OutcomeState) -> Optional[EdgeSignal]:
        """
        检测 Level 3: 高 EV 情绪错配
        必须输出
        """
        reasons = []
        
        # 条件 1: 价格极端变化
        extreme_result = self._check_extreme_price_move(state)
        if not extreme_result:
            return None
        reasons.append(extreme_result)
        
        # 条件 2: 价格回归迹象
        rebound_result = self._check_price_rebound(state)
        if not rebound_result:
            return None
        reasons.append(rebound_result)
        
        # 条件 3: 流动性检查
        liquidity_result = self._check_liquidity(state)
        if not liquidity_result:
            return None
        reasons.append(liquidity_result)
        
        # 计算价格变化
        change_pct = state.get_price_change_pct(10) or 0.0
        
        # 计算价差百分比
        spread_pct = MetricsCalculator.calculate_spread_pct(
            state.current_bid,
            state.current_ask
        )
        
        # 检查成交量激增
        volume_spike = MetricsCalculator.has_volume_spike(state)
        
        # 构建信号
        signal = EdgeSignal(
            level=SignalLevel.HIGH_EV_EDGE,
            outcome_name=state.outcome_name,
            token_id=state.token_id,
            current_price=state.current_price,
            previous_price=state.price_15m_ago,
            change_pct=change_pct,
            time_window_minutes=10,
            best_bid=state.current_bid,
            best_ask=state.current_ask,
            spread_pct=spread_pct,
            volume_spike=volume_spike,
            volatility=state.volatility_15m,
            reasons=reasons
        )
        
        return signal
    
    def _check_extreme_price_move(self, state: OutcomeState) -> Optional[str]:
        """检查极端价格变动"""
        threshold = self.level3_config.get('extreme_price_change_pct', 0.25)
        time_window = self.level3_config.get('extreme_time_window_min', 10)
        
        change = state.get_price_change_pct(time_window)
        
        if change is None:
            return None
        
        if abs(change) >= threshold:
            if change > 0:
                direction = "飙升"
                reason_type = "情绪驱动的价格飙升"
            else:
                direction = "暴跌"
                reason_type = "情绪驱动的恐慌性抛售"
            
            return f"{reason_type} ({abs(change):.1%} in {time_window}min)"
        
        return None
    
    def _check_price_rebound(self, state: OutcomeState) -> Optional[str]:
        """检查价格回归迹象"""
        min_rebound = self.level3_config.get('rebound_min_pct', 0.05)
        
        rebound = MetricsCalculator.detect_price_rebound(state, min_rebound)
        return rebound
    
    def _check_liquidity(self, state: OutcomeState) -> Optional[str]:
        """检查流动性"""
        min_depth = self.level3_config.get('min_bid_ask_depth', 50)
        max_spread = self.level3_config.get('max_spread_pct', 0.05)
        
        # 检查买卖盘深度
        if state.current_bid is None or state.current_ask is None:
            return None
        
        # 从 price_history 获取最新的 bid/ask 深度
        if not state.price_history:
            return None
        
        latest = state.price_history[-1]
        bid_depth = latest.volume if latest.bid else 0  # 简化处理
        ask_depth = latest.volume if latest.ask else 0
        
        # 实际应该从订单簿获取深度，这里简化处理
        # 假设有流动性（实际应该从 OrderBookData 获取）
        has_liquidity = True  # 简化判断
        
        # 检查价差
        spread_pct = MetricsCalculator.calculate_spread_pct(
            state.current_bid,
            state.current_ask
        )
        
        if spread_pct is not None and spread_pct > max_spread:
            return None
        
        if has_liquidity:
            return "流动性充足，可进出"
        
        return None
