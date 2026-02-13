"""
Polymarket API 客户端
处理所有与 Polymarket API 的交互
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional
from loguru import logger
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from .models import OrderBookData, OrderBookLevel, TradeData
from ..utils.rate_limiter import RateLimiter


class PolymarketClient:
    """Polymarket API 客户端"""
    
    def __init__(
        self,
        clob_url: str,
        timeout: int = 10,
        max_retries: int = 3,
        rate_limit_per_minute: int = 100
    ):
        """
        初始化客户端
        
        Args:
            clob_url: CLOB API 基础 URL
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            rate_limit_per_minute: 每分钟最大请求数
        """
        self.clob_url = clob_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter(
            max_requests=rate_limit_per_minute,
            time_window=60
        )
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()
    
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict:
        """
        发送 HTTP 请求（带重试和速率限制）
        
        Args:
            url: 请求 URL
            params: 查询参数
            
        Returns:
            响应 JSON 数据
        """
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with' context manager.")
        
        # 等待速率限制器许可
        await self.rate_limiter.acquire()
        
        try:
            async with self.session.get(url, params=params) as response:
                # 处理速率限制
                if response.status == 429:
                    logger.warning("触发速率限制，等待 5 秒...")
                    await asyncio.sleep(5)
                    raise aiohttp.ClientError("Rate limited")
                
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"请求失败 {url}: {e}")
            raise
    
    async def fetch_orderbook(self, token_id: str) -> OrderBookData:
        """
        获取订单簿数据
        
        Args:
            token_id: Token ID
            
        Returns:
            OrderBookData: 订单簿数据
        """
        url = f"{self.clob_url}/book"
        params = {"token_id": token_id}
        
        logger.debug(f"获取订单簿: token_id={token_id}")
        
        try:
            data = await self._make_request(url, params)
            
            # 解析订单簿数据
            bids = [
                OrderBookLevel(price=float(level.get("price", 0)), size=float(level.get("size", 0)))
                for level in data.get("bids", [])
            ]
            
            asks = [
                OrderBookLevel(price=float(level.get("price", 0)), size=float(level.get("size", 0)))
                for level in data.get("asks", [])
            ]
            
            orderbook = OrderBookData(
                token_id=token_id,
                bids=bids,
                asks=asks
            )
            
            logger.debug(
                f"订单簿获取成功: bid={orderbook.best_bid}, ask={orderbook.best_ask}, "
                f"spread={orderbook.spread}"
            )
            
            return orderbook
            
        except Exception as e:
            logger.error(f"获取订单簿失败 {token_id}: {e}")
            # 返回空订单簿而不是抛出异常
            return OrderBookData(token_id=token_id, bids=[], asks=[])
    
    async def fetch_orderbooks_batch(self, token_ids: List[str]) -> Dict[str, OrderBookData]:
        """
        批量获取多个 token 的订单簿
        
        Args:
            token_ids: Token ID 列表
            
        Returns:
            Dict[str, OrderBookData]: token_id -> OrderBookData 的映射
        """
        logger.debug(f"批量获取 {len(token_ids)} 个订单簿")
        
        # 并发请求所有订单簿
        tasks = [self.fetch_orderbook(token_id) for token_id in token_ids]
        orderbooks = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 构建结果字典
        result = {}
        for token_id, orderbook in zip(token_ids, orderbooks):
            if isinstance(orderbook, Exception):
                logger.error(f"获取订单簿失败 {token_id}: {orderbook}")
                result[token_id] = OrderBookData(token_id=token_id, bids=[], asks=[])
            else:
                result[token_id] = orderbook
        
        return result
    
    async def fetch_trades(
        self,
        token_id: str,
        limit: int = 100
    ) -> List[TradeData]:
        """
        获取最近的交易记录
        
        Args:
            token_id: Token ID
            limit: 返回记录数量
            
        Returns:
            List[TradeData]: 交易记录列表
        """
        url = f"{self.clob_url}/trades"
        params = {
            "token_id": token_id,
            "limit": limit
        }
        
        logger.debug(f"获取交易记录: token_id={token_id}, limit={limit}")
        
        try:
            data = await self._make_request(url, params)
            
            trades = []
            for trade in data:
                trades.append(TradeData(
                    token_id=token_id,
                    price=float(trade.get("price", 0)),
                    size=float(trade.get("size", 0)),
                    timestamp=trade.get("timestamp"),
                    side=trade.get("side", "unknown")
                ))
            
            logger.debug(f"获取到 {len(trades)} 条交易记录")
            return trades
            
        except Exception as e:
            logger.error(f"获取交易记录失败 {token_id}: {e}")
            return []
    
    def get_rate_limit_status(self) -> Dict[str, int]:
        """
        获取速率限制状态
        
        Returns:
            Dict: 包含当前使用情况的字典
        """
        current = self.rate_limiter.get_current_usage()
        return {
            "current": current,
            "max": self.rate_limiter.max_requests,
            "remaining": self.rate_limiter.max_requests - current
        }
