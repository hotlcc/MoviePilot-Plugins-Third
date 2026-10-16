"""
断言工具
"""
from typing import Any


def is_true(value: bool, message_template: str = None, *args, **kwargs) -> None:
    """
    断言为true
    """
    if value is True:
        return
    message_template = message_template or "断言失败"
    msg = message_template.format(*args, **kwargs)
    raise ValueError(msg)


def is_valid(value: Any, message_template: str = None, *args, **kwargs):
    """
    断言值有效
    """
    is_true(True if value else False, message_template=message_template, *args, **kwargs)
