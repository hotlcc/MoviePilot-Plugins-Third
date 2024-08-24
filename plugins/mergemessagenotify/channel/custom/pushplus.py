from typing import Tuple, List, Dict, Any
from enum import Enum
import requests

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger


class SendChannel(Enum):
    """
    发送渠道枚举
    """

    wechat = "微信公众号"
    webhook = "第三方webhook"
    cp = "企业微信应用"
    mail = "邮件"
    sms = "短信"


class PushPlusChannel(CustomChannel):
    """
    PushPlus渠道 http://www.pushplus.plus
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.pushplus"
    # 组件名称
    comp_name: str = "PushPlus"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 6

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {
        "channel": SendChannel.wechat.name
    }

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        获取组件的配置表单
        :return: 配置表单, 建议的配置
        """
        # 建议的配置
        config_suggest = {}
        # 合并默认配置
        config_suggest.update(self.config_default)
        # elements
        row1 = {
            'component': 'VRow',
            'content': [{
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'token',
                        'label': '用户令牌',
                        'hint': '必填。用户令牌'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSelect',
                    'props': {
                        'model': 'channel',
                        'label': '发送渠道',
                        'items': [{
                            'title': sc.value,
                            'value': sc.name
                        } for sc in SendChannel if sc],
                        'hint': '必填。缺省时为微信公众号。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'topic',
                        'label': '群组编码',
                        'hint': '选填。缺省时仅发送给自己，发送渠道为第三方webhook时无效。'
                    }
                }]
            }]
        }
        row2 = self.build_notify_type_select_row_element()
        row3 = self.build_test_once_switch_row_element()
        elements = [row1, row2, row3]
        # 处理缺省配置
        self.save_default_config()
        return elements, config_suggest

    def __check_config(self) -> bool:
        """
        检查配置
        """
        if not self.get_config_item(config_key="token"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 用户令牌无效")
            return False
        return True

    def __build_json(self, title: str, text: str, ext_info: dict = {}) -> dict:
        """
        构造请求json
        """
        ext_info = ext_info or {}
        # json
        json = {
            "token": self.get_config_item(config_key="token"),
            "title": title,
            "topic": self.get_config_item(config_key="topic"),
            "template": "markdown",
            "channel": self.get_config_item(config_key="channel"),
        }
        # content
        content = text or title
        image = ext_info.get("image")
        if image:
            content += f"\n\n![]({image})"
        json["content"] = content
        return json

    def send_message(self, title: str, text: str, type: NotificationType = None, ext_info: dict = {}) -> bool:
        """
        发送消息
        """
        type_str = type.value if type else None
        enable_notify_types: List[str] = self.get_config_item("enable_notify_types")
        if (type and enable_notify_types and type.name not in enable_notify_types):
            logger.warn(f"发送消息中止: channel = {self.comp_name}, type = {type_str}, 消息类型不受支持")
            return False
        if not self.__check_config():
            return False
        send_url = "http://www.pushplus.plus/send"
        json = self.__build_json(title=title, text=text, ext_info=ext_info)
        res = requests.post(url=send_url, json=json)
        res_json = res.json() or {}
        if res.ok or res_json:
            code = res_json.get("code")
            message = res_json.get("msg")
            if code == 200:
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
                return True
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
                return False
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
            return False
