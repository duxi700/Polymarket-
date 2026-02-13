"""
数据模型定义
使用 Pydantic 进行数据验证
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class OutcomeInfo(BaseModel):
    """市场结果信息"""
    name: str = Field(..., description="结果名称，如 YES/NO")
    token_id: str = Field(..., description="Token ID")
    outcome_id: str = Field(default="", description="Outcome ID")
    price: float = Field(default=0.0, ge=0.0, le=1.0, description="当前价格")


class MarketInfo(BaseModel):
    """市场信息"""
    market_id: str = Field(..., description="市场 ID / Condition ID")
    event_name: str = Field(..., description="事件名称")
    question: str = Field(default="", description="市场问题")
    outcomes: List[OutcomeInfo] = Field(default_factory=list, description="所有可能的结果")
    
    class Config:
        frozen = False


class OrderBookLevel(BaseModel):
    """订单簿层级"""
    price: float = Field(..., ge=0.0, le=1.0, description="价格")
    size: float = Field(..., ge=0.0, description="数量")


class OrderBookData(BaseModel):
    """订单簿数据"""
    token_id: str = Field(..., description="Token ID")
    bids: List[OrderBookLevel] = Field(default_factory=list, description="买单")
    asks: List[OrderBookLevel] = Field(default_factory=list, description="卖单")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    
    @property
    def best_bid(self) -> Optional[float]:
        """最佳买价"""
        return self.bids[0].price if self.bids else None
    
    @property
    def best_ask(self) -> Optional[float]:
        """最佳卖价"""
        return self.asks[0].price if self.asks else None
    
    @property
    def mid_price(self) -> Optional[float]:
        """中间价"""
        if self.best_bid is not None and self.best_ask is not None:
            return (self.best_bid + self.best_ask) / 2
        return None
    
    @property
    def spread(self) -> Optional[float]:
        """买卖价差"""
        if self.best_bid is not None and self.best_ask is not None:
            return self.best_ask - self.best_bid
        return None
    
    @property
    def bid_depth(self) -> float:
        """买单深度"""
        return sum(level.size for level in self.bids)
    
    @property
    def ask_depth(self) -> float:
        """卖单深度"""
        return sum(level.size for level in self.asks)


class TradeData(BaseModel):
    """交易数据"""
    token_id: str
    price: float
    size: float
    timestamp: datetime
    side: str  # "buy" or "sell"
