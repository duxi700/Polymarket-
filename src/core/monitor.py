"""
主监控器
协调所有模块，执行监控循环
"""

import asyncio
import aiohttp
from typing import Dict, Optional
from loguru import logger
from datetime import datetime

from ..api import MarketParser, PolymarketClient, MarketInfo
from ..core.state import OutcomeState
from ..detection import EdgeDetectionEngine
from ..output import ConsoleOutput


class PolymarketMonitor:
    """Polymarket 实时监控器"""
    
    def __init__(
        self,
        market_url: str,
        config: Dict,
        thresholds: Dict
    ):
        """
        初始化监控器
        
        Args:
            market_url: Polymarket 市场 URL
            config: 系统配置
            thresholds: 检测阈值配置
        """
        self.market_url = market_url
        self.config = config
        self.thresholds = thresholds
        
        # 轮询配置
        self.poll_interval = config['polling']['live_market_interval']
        
        # API 配置
        self.clob_url = config['api']['clob_url']
        self.gamma_url = config['api']['gamma_url']
        
        # 市场信息和状态
        self.market_info: Optional[MarketInfo] = None
        self.outcome_states: Dict[str, OutcomeState] = {}
        
        # 组件
        self.client: Optional[PolymarketClient] = None
        self.parser: Optional[MarketParser] = None
        self.detection_engine: Optional[EdgeDetectionEngine] = None
        
        # 统计
        self.total_polls = 0
        self.total_signals = 0
        
    async def start(self):
        """启动监控"""
        # 打印启动横幅
        ConsoleOutput.print_startup_banner(self.market_url, self.poll_interval)
        
        try:
            # 创建 HTTP 会话
            async with aiohttp.ClientSession() as session:
                # 初始化组件
                self.client = PolymarketClient(
                    clob_url=self.clob_url,
                    timeout=self.config['api']['timeout'],
                    max_retries=self.config['api']['max_retries'],
                    rate_limit_per_minute=self.config['rate_limit']['max_requests_per_minute']
                )
                
                # 进入 client 上下文
                async with self.client:
                    self.parser = MarketParser(session, self.gamma_url)
                    self.detection_engine = EdgeDetectionEngine(self.thresholds)
                    
                    # 解析市场
                    ConsoleOutput.print_info("正在解析市场信息...")
                    self.market_info = await self.parser.parse_market_url(self.market_url)
                    
                    # 初始化 outcome 状态
                    self._initialize_outcome_states()
                    
                    ConsoleOutput.print_success(
                        f"市场解析完成: {self.market_info.event_name} "
                        f"({len(self.market_info.outcomes)} outcomes)"
                    )
                    
                    # 开始监控循环
                    await self._monitoring_loop()
                    
        except KeyboardInterrupt:
            logger.info("\\n用户中断监控")
            ConsoleOutput.print_info("\\n监控已停止")
        except Exception as e:
            logger.exception(f"监控过程中发生错误: {e}")
            ConsoleOutput.print_error(f"监控失败: {e}")
    
    def _initialize_outcome_states(self):
        """初始化所有 outcome 的状态"""
        for outcome in self.market_info.outcomes:
            state = OutcomeState(
                outcome_name=outcome.name,
                token_id=outcome.token_id,
                signal_cooldown_minutes=self.thresholds['level3']['signal_cooldown_minutes']
            )
            self.outcome_states[outcome.token_id] = state
            logger.info(f"初始化状态: {outcome.name} (token_id: {outcome.token_id})")
    
    async def _monitoring_loop(self):
        """主监控循环"""
        logger.info("开始监控循环")
        
        while True:
            try:
                await self._poll_cycle()
                self.total_polls += 1
                
                # 等待下一个轮询周期
                await asyncio.sleep(self.poll_interval)
                
            except asyncio.CancelledError:
                logger.info("监控循环被取消")
                break
            except Exception as e:
                logger.error(f"轮询周期错误: {e}")
                ConsoleOutput.print_warning(f"轮询出错，5秒后重试: {e}")
                await asyncio.sleep(5)
    
    async def _poll_cycle(self):
        """单次轮询周期"""
        try:
            # 获取所有 token 的订单簿数据
            token_ids = [outcome.token_id for outcome in self.market_info.outcomes]
            orderbooks = await self.client.fetch_orderbooks_batch(token_ids)
            
            # 更新每个 outcome 的状态
            for token_id, orderbook in orderbooks.items():
                state = self.outcome_states.get(token_id)
                if not state:
                    continue
                
                # 使用中间价作为当前价格
                current_price = orderbook.mid_price or orderbook.best_bid or orderbook.best_ask
                if current_price is None:
                    logger.warning(f"无法获取 {state.outcome_name} 的价格")
                    continue
                
                # 更新状态
                state.add_price_point(
                    price=current_price,
                    volume=0.0,  # 暂时不追踪成交量
                    bid=orderbook.best_bid,
                    ask=orderbook.best_ask
                )
                
                # 执行 edge 检测
                signal = self.detection_engine.detect(state)
                
                if signal:
                    self.total_signals += 1
                    # 输出信号
                    ConsoleOutput.print_signal(signal, self.market_info.event_name)
            
            # 打印状态更新
            total_data_points = sum(len(s.price_history) for s in self.outcome_states.values())
            rate_status = self.client.get_rate_limit_status()
            
            ConsoleOutput.print_status_update(
                outcomes_count=len(self.outcome_states),
                data_points=total_data_points,
                rate_limit_status=rate_status
            )
            
        except Exception as e:
            logger.error(f"轮询周期执行失败: {e}")
            raise
    
    def get_statistics(self) -> Dict:
        """获取监控统计信息"""
        return {
            "total_polls": self.total_polls,
            "total_signals": self.total_signals,
            "outcomes_count": len(self.outcome_states),
            "total_data_points": sum(len(s.price_history) for s in self.outcome_states.values())
        }
