from enum import Enum
from typing import Tuple, List, Dict, Any

import requests
from app.core.config import settings
from app.log import logger
from app.schemas.types import NotificationType

from . import CustomChannel


class ApiKeyType(Enum):
    """
    Api Key 类型枚举
    """
    push_key = "接口密钥"
    temp_key = "临时密钥"


class MessageTopic(Enum):
    """
    消息主题枚举
    """
    info = ("[i]", "⬜️ 信息")
    success = ("[s]", "🟩 成功")
    warning = ("[w]", "🟨 警告")
    failure = ("[f]", "🟥 失败")

    def __init__(self, symbol: str, desc: str):
        self.symbol = symbol
        self.desc = desc


# noinspection DuplicatedCode
class PushMeChannel(CustomChannel):
    """
    PushMe渠道 https://push.i-i.me/
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.pushme"
    # 组件名称
    comp_name: str = "PushMe"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 9

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {}

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        获取组件的配置表单
        :return: 配置表单, 建议的配置
        """
        # 建议的配置
        config_suggest = {
            "key_type": ApiKeyType.push_key.name,
        }
        # 合并默认配置
        config_suggest.update(self.config_default)
        # elements
        row1 = {
            'component': 'VRow',
            'content': [{
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'server_url',
                        'label': '服务器地址',
                        'placeholder': 'http://127.0.0.1:3010',
                        'hint': '必填。或者使用官方地址：https://push.i-i.me'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 2, 'xl': 2, 'lg': 2, 'md': 2, 'sm': 2, 'xs': 4
                },
                'content': [{
                    'component': 'VSelect',
                    'props': {
                        'model': 'key_type',
                        'label': '密钥类型',
                        'items': [{
                            'title': kt.value,
                            'value': kt.name
                        } for kt in ApiKeyType if kt],
                        'hint': '必填。请根据实际使用的密钥类型选择。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 4, 'xs': 8
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'key',
                        'label': '密钥',
                        'hint': '必填。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSelect',
                    'props': {
                        'model': 'message_topic',
                        'label': '消息主题',
                        'clearable': True,
                        'items': [{
                            'title': mt.desc,
                            'value': mt.name
                        } for mt in MessageTopic if mt],
                        'hint': '选填。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'message_channel',
                        'label': '消息通道',
                        'hint': '选填。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSwitch',
                    'props': {
                        'model': 'enable_proxy',
                        'label': '使用代理',
                        'hint': '推送消息时是否使用网络代理。'
                    }
                }]
            }]
        }
        row2 = self.build_notify_type_select_row_element()
        row3 = self.build_test_once_switch_row_element()
        elements = [row1, row2, row3]
        return elements, config_suggest

    def __check_config(self) -> bool:
        """
        检查配置
        """
        server_url: str = self.get_config_item(config_key="server_url")
        server_url = server_url.rstrip("/") if server_url else None
        if not server_url:
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 服务器地址无效")
            return False
        if not self.get_config_item(config_key="key_type"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 密钥类型无效")
            return False
        if not self.get_config_item(config_key="key"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 密钥无效")
            return False
        return True

    def __build_data(self, title: str, text: str, ext_info: dict = None) -> dict:
        """
        构造表单数据
        """
        ext_info = ext_info or {}
        data = {}
        # 密钥
        key_type = self.get_config_item(config_key="key_type")
        key = self.get_config_item(config_key="key")
        if key_type == ApiKeyType.push_key.name:
            data["push_key"] = key
        elif key_type == ApiKeyType.temp_key.name:
            data["temp_key"] = key
        # 标题
        if title:
            message_topic: str = self.get_config_item(config_key="message_topic")
            if message_topic:
                topic: MessageTopic = MessageTopic.__members__.get(message_topic)
                if topic:
                    title = f"{topic.symbol} {title}"
            message_channel: str = self.get_config_item(config_key="message_channel")
            if message_channel:
                title = f"{title} [~{message_channel}]"
            data["title"] = title
        # 消息类型和内容
        content = text
        data["type"] = "text"
        image = ext_info.get("image")
        if image:
            data["type"] = "markdown"
            content += f"\n\n![]({image})"
        data["content"] = content
        return data

    def send_message(self, title: str, text: str, type: NotificationType = None, ext_info: dict = None) -> bool:
        """
        发送消息
        """
        type_str = type.value if type else None
        ext_info = ext_info or {}
        enable_notify_types: List[str] = self.get_config_item("enable_notify_types")
        if type and enable_notify_types and type.name not in enable_notify_types:
            logger.warn(f"发送消息中止: channel = {self.comp_name}, type = {type_str}, 消息类型不受支持")
            return False
        if not self.__check_config():
            return False
        server_url: str = self.get_config_item(config_key="server_url")
        send_url = server_url
        data = self.__build_data(title=title, text=text, ext_info=ext_info)
        proxies = settings.PROXY if self.get_config_item(config_key="enable_proxy") else None
        res = requests.post(url=send_url, data=data, proxies=proxies)
        res_text = res.text
        if res_text == 'success':
            logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
            return True
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, reason = {res_text}")
            return False
