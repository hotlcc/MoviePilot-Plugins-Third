from enum import Enum


class ChannelStrategy(Enum):
    """
    渠道策略枚举
    """

    ALL_SELECTED = ("全部所选", "选择的渠道都会发送消息")
    ORDER_SUCCESS_ONE = ("顺序优先，成功即止", "按选择的渠道顺序依次发送，成功后不再继续后续渠道")

    def __init__(self, name_: str, desc: str):
        self.name_ = name_
        self.desc = desc
