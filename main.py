"""
主程序入口
"""

import asyncio
import sys
from pathlib import Path
import yaml
from loguru import logger

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.monitor import PolymarketMonitor
from src.utils.logger import setup_logging
from src.output.console import ConsoleOutput


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"无法加载配置文件 {config_path}: {e}")
        sys.exit(1)


def get_market_url() -> str:
    """获取市场 URL（从命令行参数或交互输入）"""
    if len(sys.argv) > 1:
        return sys.argv[1]
    
    print("\\n请输入 Polymarket 市场 URL:")
    print("示例: https://polymarket.com/event/your-event-slug")
    print("或: https://polymarket.com/market/your-market-slug")
    print()
    
    url = input("URL: ").strip()
    
    if not url:
        ConsoleOutput.print_error("URL 不能为空")
        sys.exit(1)
    
    return url


async def main():
    """主函数"""
    try:
        # 加载配置
        config_dir = Path(__file__).parent / "config"
        config = load_config(config_dir / "config.yaml")
        thresholds = load_config(config_dir / "thresholds.yaml")
        
        # 设置日志
        setup_logging(config['logging'])
        
        logger.info("=" * 60)
        logger.info("Polymarket 实时监控系统启动")
        logger.info("=" * 60)
        
        # 获取市场 URL
        market_url = get_market_url()
        
        # 创建监控器
        monitor = PolymarketMonitor(
            market_url=market_url,
            config=config,
            thresholds=thresholds
        )
        
        # 启动监控
        await monitor.start()
        
        # 输出统计信息
        stats = monitor.get_statistics()
        logger.info("\\n监控统计:")
        logger.info(f"  总轮询次数: {stats['total_polls']}")
        logger.info(f"  总信号数: {stats['total_signals']}")
        logger.info(f"  监控的 outcomes: {stats['outcomes_count']}")
        logger.info(f"  总数据点: {stats['total_data_points']}")
        
    except KeyboardInterrupt:
        ConsoleOutput.print_info("\\n程序被用户中断")
    except Exception as e:
        logger.exception(f"程序异常退出: {e}")
        ConsoleOutput.print_error(f"程序异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
