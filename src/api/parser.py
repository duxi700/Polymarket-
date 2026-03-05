"""
Polymarket URL 解析器
从 URL 中提取市场信息
"""

import re
import json
import aiohttp
from typing import Dict, List, Optional
from loguru import logger

from .models import MarketInfo, OutcomeInfo


class MarketParser:
    """Polymarket 市场 URL 解析器"""
    
    def __init__(self, session: aiohttp.ClientSession, gamma_url: str):
        """
        初始化解析器
        
        Args:
            session: aiohttp 会话
            gamma_url: Gamma API 基础 URL
        """
        self.session = session
        self.gamma_url = gamma_url
    
    async def parse_market_url(self, url: str) -> MarketInfo:
        """
        解析 Polymarket URL 并获取市场信息
        
        支持的 URL 格式:
        - https://polymarket.com/event/slug
        - https://polymarket.com/market/slug
        - https://polymarket.com/sports/slug
        
        Args:
            url: Polymarket 市场 URL
            
        Returns:
            MarketInfo: 市场信息对象
            
        Raises:
            ValueError: URL 格式无效或市场不存在
        """
        # 提取 slug
        match = re.search(r'polymarket\.com/(event|market|sports)/(.*)', url)
        if not match:
            raise ValueError(f"无效的 Polymarket URL: {url}")
        
        url_type, slug = match.groups()
        # 移除查询参数和片段
        slug = slug.split('?')[0].split('#')[0]
        
        # 对于 sports URL，提取最后一个路径部分作为 slug
        if url_type == "sports":
            slug = slug.split('/')[-1]
        
        logger.info(f"解析 URL: type={url_type}, slug={slug}")
        
        # 根据类型调用不同的解析方法
        if url_type in ("event", "sports"):
            return await self._fetch_event(slug)
        else:
            return await self._fetch_market(slug)
    
    async def _fetch_event(self, slug: str) -> MarketInfo:
        """
        获取事件信息
        
        Args:
            slug: 事件 slug
            
        Returns:
            MarketInfo: 市场信息
        """
        url = f"{self.gamma_url}/events?slug={slug}"
        logger.debug(f"请求事件信息: {url}")
        
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()
                
                if not data:
                    raise ValueError(f"事件不存在: {slug}")
                
                event = data[0]
                markets = event.get("markets", [])
                
                if not markets:
                    raise ValueError(f"事件没有关联的市场: {slug}")
                
                # 通常事件包含多个市场，这里取第一个
                # 如果需要支持多市场，可以返回列表
                market = markets[0]
                
                return self._parse_market_data(market, event.get("title", ""))
                
        except aiohttp.ClientError as e:
            logger.error(f"请求事件信息失败: {e}")
            raise ValueError(f"无法获取事件信息: {e}")
    
    async def _fetch_market(self, slug: str) -> MarketInfo:
        """
        获取市场信息
        
        Args:
            slug: 市场 slug
            
        Returns:
            MarketInfo: 市场信息
        """
        url = f"{self.gamma_url}/markets?slug={slug}"
        logger.debug(f"请求市场信息: {url}")
        
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()
                
                if not data:
                    raise ValueError(f"市场不存在: {slug}")
                
                market = data[0]
                event_title = market.get("groupItemTitle", market.get("question", ""))
                
                return self._parse_market_data(market, event_title)
                
        except aiohttp.ClientError as e:
            logger.error(f"请求市场信息失败: {e}")
            raise ValueError(f"无法获取市场信息: {e}")
    
    def _parse_market_data(self, market: Dict, event_name: str) -> MarketInfo:
        """
        解析市场数据
        
        Args:
            market: 市场数据字典
            event_name: 事件名称
            
        Returns:
            MarketInfo: 解析后的市场信息
        """
        condition_id = market.get("conditionId") or market.get("condition_id", "")
        question = market.get("question", "")
        
        # 解析 outcomes（兼容旧字段 tokens 和新字段 outcomes/clobTokenIds）
        outcomes = []
        tokens = market.get("tokens", [])
        
        for token in tokens:
            outcome = OutcomeInfo(
                name=token.get("outcome", "Unknown"),
                token_id=token.get("token_id", ""),
                outcome_id=token.get("outcome_id", token.get("token_id", "")),
                price=float(token.get("price", 0.0))
            )
            outcomes.append(outcome)

        if not outcomes:
            raw_outcomes = market.get("outcomes")
            raw_prices = market.get("outcomePrices")
            raw_token_ids = market.get("clobTokenIds")

            try:
                parsed_outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else (raw_outcomes or [])
            except json.JSONDecodeError:
                parsed_outcomes = []

            try:
                parsed_prices = json.loads(raw_prices) if isinstance(raw_prices, str) else (raw_prices or [])
            except json.JSONDecodeError:
                parsed_prices = []

            try:
                parsed_token_ids = json.loads(raw_token_ids) if isinstance(raw_token_ids, str) else (raw_token_ids or [])
            except json.JSONDecodeError:
                parsed_token_ids = []

            for i, outcome_name in enumerate(parsed_outcomes):
                token_id = str(parsed_token_ids[i]) if i < len(parsed_token_ids) else ""
                price = 0.0
                if i < len(parsed_prices):
                    try:
                        price = float(parsed_prices[i])
                    except (TypeError, ValueError):
                        price = 0.0

                outcomes.append(
                    OutcomeInfo(
                        name=str(outcome_name),
                        token_id=token_id,
                        outcome_id=token_id,
                        price=price
                    )
                )
        
        market_info = MarketInfo(
            market_id=condition_id,
            event_name=event_name or question,
            question=question,
            outcomes=outcomes
        )
        
        logger.info(f"市场解析完成: {market_info.event_name}")
        logger.info(f"包含 {len(outcomes)} 个 outcomes: {[o.name for o in outcomes]}")
        
        return market_info
