from abc import ABCMeta, abstractmethod
from typing import List

from ..model import Radio


class BaseSource(metaclass=ABCMeta):
    """
    电台源组件基类
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
        获取电台信息
        """
        pass

    def build_radio_display_name(self, raw_name: str) -> str:
        """
        构造电台显示名称
        """
        return f"[{self.comp_name}] {raw_name}"
