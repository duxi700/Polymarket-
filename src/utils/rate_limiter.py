"""
速率限制器
防止API请求过于频繁
"""

import asyncio
from collections import deque
from datetime import datetime, timedelta
from typing import Deque


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_requests: int, time_window: int):
        """
        初始化速率限制器
        
        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口大小（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Deque[datetime] = deque()
    
    async def acquire(self):
        """获取请求许可（会阻塞直到可以发送请求）"""
        now = datetime.now()
        
        # 清理过期的请求记录
        cutoff = now - timedelta(seconds=self.time_window)
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        # 如果达到限制，等待
        if len(self.requests) >= self.max_requests:
            # 计算需要等待的时间
            oldest_request = self.requests[0]
            wait_until = oldest_request + timedelta(seconds=self.time_window)
            sleep_time = (wait_until - now).total_seconds()
            
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                # 递归调用以重新检查
                return await self.acquire()
        
        # 记录本次请求
        self.requests.append(now)
    
    def get_current_usage(self) -> int:
        """获取当前时间窗口内的请求数"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.time_window)
        
        # 清理过期记录
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        return len(self.requests)
