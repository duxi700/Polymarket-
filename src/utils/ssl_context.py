"""
SSL 上下文工具
优先使用 certifi 证书链，降低系统证书缺失导致的 HTTPS 失败概率。
"""

import ssl


def create_ssl_context() -> ssl.SSLContext:
    """创建 HTTPS SSL 上下文。"""
    context = ssl.create_default_context()
    try:
        import certifi

        context.load_verify_locations(cafile=certifi.where())
    except Exception:
        # certifi 不可用时回退到系统默认证书
        pass
    return context
