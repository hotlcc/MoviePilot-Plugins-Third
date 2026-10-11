from abc import ABCMeta, abstractmethod
from typing import List

from ..model import Radio


class BaseSource(metaclass=ABCMeta):
    """
    广播源组件基类
    """

    # 组件key：取组件类名去除Source后缀后的小写
    comp_key: str = ""
    # 组件名称
    comp_name: str = ""
    # 组件顺序
    comp_order: int = 0

    @abstractmethod
    async def get_radios(self) -> List[Radio]:
        """
        获取广播信息
        """
        pass
