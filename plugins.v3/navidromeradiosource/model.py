from dataclasses import dataclass
from typing import Optional


@dataclass
class Radio:
    """
    广播信息
    """

    name: str  # 名称
    stream_url: str  # 推流URL
    home_page_url: Optional[str] = None  # 主页URL
