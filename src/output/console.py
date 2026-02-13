"""
终端输出格式化
按照需求文档规定的格式输出信号
"""

from datetime import datetime
from typing import Optional

from ..detection.signals import EdgeSignal, SignalLevel


class ConsoleOutput:
    """终端输出格式化器"""
    
    # ANSI 颜色代码
    RESET = "\\033[0m"
    RED = "\\033[91m"
    YELLOW = "\\033[93m"
    GREEN = "\\033[92m"
    CYAN = "\\033[96m"
    BOLD = "\\033[1m"
    
    @staticmethod
    def print_signal(signal: EdgeSignal, market_name: str = ""):
        """
        打印 Edge 信号
        
        Args:
            signal: Edge 信号对象
            market_name: 市场名称
        """
        if signal.level == SignalLevel.HIGH_EV_EDGE:
            ConsoleOutput._print_level3_signal(signal, market_name)
        elif signal.level == SignalLevel.POTENTIAL_EDGE:
            ConsoleOutput._print_level2_signal(signal, market_name)
    
    @staticmethod
    def _print_level3_signal(signal: EdgeSignal, market_name: str):
        """打印 Level 3 信号（高 EV 错配）"""
        separator = "=" * 60
        
        # 计算价格变化方向和幅度
        direction_symbol = "📈" if signal.change_pct > 0 else "📉"
        change_str = f"{signal.change_pct:+.1%}" if signal.change_pct else "N/A"
        
        # 格式化 bid/ask/spread
        bid_str = f"{signal.best_bid:.4f}" if signal.best_bid is not None else "N/A"
        ask_str = f"{signal.best_ask:.4f}" if signal.best_ask is not None else "N/A"
        spread_str = f"{signal.spread_pct:.2%}" if signal.spread_pct is not None else "N/A"
        volume_spike_str = "YES" if signal.volume_spike else "NO"
        volume_spike_color = ConsoleOutput.GREEN if signal.volume_spike else ConsoleOutput.YELLOW
        
        # 构建输出
        output = f"""
{ConsoleOutput.RED}{ConsoleOutput.BOLD}{separator}
🚨 EDGE SIGNAL (Level 3 - High EV)
{separator}{ConsoleOutput.RESET}

{ConsoleOutput.CYAN}Market:{ConsoleOutput.RESET} {market_name}
{ConsoleOutput.CYAN}Outcome:{ConsoleOutput.RESET} {signal.outcome_name}
{ConsoleOutput.CYAN}Timestamp:{ConsoleOutput.RESET} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{ConsoleOutput.BOLD}Price Movement:{ConsoleOutput.RESET}
  {signal.previous_price:.4f} → {signal.current_price:.4f} {direction_symbol}
  Change: {change_str} in {signal.time_window_minutes:.0f} min

{ConsoleOutput.BOLD}Market State:{ConsoleOutput.RESET}
  Best Bid: {bid_str}
  Best Ask: {ask_str}
  Spread: {spread_str}
  Volume Spike: {volume_spike_color}{volume_spike_str}{ConsoleOutput.RESET}
  Volatility: {signal.volatility:.4f}

{ConsoleOutput.BOLD}Edge Indicators:{ConsoleOutput.RESET}"""
        
        # 添加原因列表
        for i, reason in enumerate(signal.reasons, 1):
            output += f"\\n  {i}. {reason}"
        
        output += f"""

{ConsoleOutput.YELLOW}{ConsoleOutput.BOLD}⚠️  Note:{ConsoleOutput.RESET}
{ConsoleOutput.YELLOW}This is a market signal only, not a trade instruction.
Always verify market conditions before taking action.{ConsoleOutput.RESET}

{ConsoleOutput.RED}{separator}{ConsoleOutput.RESET}
"""
        
        print(output)
    
    @staticmethod
    def _print_level2_signal(signal: EdgeSignal, market_name: str):
        """打印 Level 2 信号（潜在 Edge）"""
        separator = "-" * 60
        
        change_str = f"{signal.change_pct:+.1%}" if signal.change_pct else "N/A"
        
        output = f"""
{ConsoleOutput.YELLOW}{separator}
⚡ Potential Edge Signal (Level 2)
{separator}{ConsoleOutput.RESET}

Market: {market_name}
Outcome: {signal.outcome_name}
Price: {signal.current_price:.4f} ({change_str})
Reasons: {', '.join(signal.reasons)}

{separator}
"""
        
        print(output)
    
    @staticmethod
    def print_startup_banner(market_url: str, poll_interval: int):
        """打印启动横幅"""
        banner = f"""
{ConsoleOutput.CYAN}{ConsoleOutput.BOLD}
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║        Polymarket 实时 Edge 监控系统 v1.0                 ║
║        Real-time Market Sentiment Monitor                  ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
{ConsoleOutput.RESET}

{ConsoleOutput.GREEN}🚀 系统启动中...{ConsoleOutput.RESET}

{ConsoleOutput.CYAN}监控市场:{ConsoleOutput.RESET} {market_url}
{ConsoleOutput.CYAN}轮询间隔:{ConsoleOutput.RESET} {poll_interval} 秒
{ConsoleOutput.CYAN}时间:{ConsoleOutput.RESET} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{ConsoleOutput.YELLOW}系统说明:{ConsoleOutput.RESET}
  • 本系统监控市场情绪驱动的价格错配
  • 仅在出现高 EV 机会时输出信号
  • 信号非交易指令，需人工判断

{ConsoleOutput.GREEN}✓ 准备就绪，开始监控...{ConsoleOutput.RESET}
{ConsoleOutput.CYAN}{'=' * 60}{ConsoleOutput.RESET}
"""
        print(banner)
    
    @staticmethod
    def print_status_update(
        outcomes_count: int,
        data_points: int,
        rate_limit_status: dict
    ):
        """打印状态更新（简洁版）"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        rate_str = f"{rate_limit_status.get('current', 0)}/{rate_limit_status.get('max', 100)}"
        
        print(
            f"{ConsoleOutput.CYAN}[{timestamp}]{ConsoleOutput.RESET} "
            f"监控中 | Outcomes: {outcomes_count} | "
            f"数据点: {data_points} | "
            f"API 使用: {rate_str}",
            end="\\r"
        )
    
    @staticmethod
    def print_error(message: str):
        """打印错误信息"""
        print(f"{ConsoleOutput.RED}❌ 错误: {message}{ConsoleOutput.RESET}")
    
    @staticmethod
    def print_warning(message: str):
        """打印警告信息"""
        print(f"{ConsoleOutput.YELLOW}⚠️  警告: {message}{ConsoleOutput.RESET}")
    
    @staticmethod
    def print_info(message: str):
        """打印信息"""
        print(f"{ConsoleOutput.CYAN}ℹ️  {message}{ConsoleOutput.RESET}")
    
    @staticmethod
    def print_success(message: str):
        """打印成功信息"""
        print(f"{ConsoleOutput.GREEN}✓ {message}{ConsoleOutput.RESET}")
