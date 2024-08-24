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

    c_18 = (18, "PushDeer")
    c_9 = (9, "方糖服务号")
    c_98 = (98, "官方Android版·β")
    c_68 = (68, "企业微信应用消息")
    c_1 = (1, "企业微信群机器人")
    c_2 = (2, "钉钉群机器人")
    c_3 = (3, "飞书群机器人")
    c_8 = (8, "Bark iOS")
    c_0 = (0, "测试号")
    c_88 = (88, "自定义")

    def __init__(self, code: int, name_: str):
        self.code = code
        self.name_ = name_


class ServerChanChannel(CustomChannel):
    """
    Server酱渠道 https://sct.ftqq.com
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.serverchan"
    # 组件名称
    comp_name: str = "Server酱"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 7

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {}

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
                    'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'send_key',
                        'label': 'SendKey',
                        'hint': '必填。推送秘钥。'
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
                        'model': 'channel',
                        'label': '发送渠道',
                        'multiple': True,
                        'chips': True,
                        'clearable': True,
                        'items': [{
                            'title': sc.name_,
                            'value': sc.code
                        } for sc in SendChannel if sc],
                        'hint': '选填。最多可选两个，超出无效。缺省时使用网站消息通道页面设置的通道。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSwitch',
                    'props': {
                        'model': 'noip',
                        'label': '隐藏调用IP',
                        'hint': '是否隐藏消息详情中的调用IP。'
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
        if not self.get_config_item(config_key="send_key"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, SendKey无效")
            return False
        return True

    def __build_url(self) -> str:
        """
        构造url
        """
        send_key = self.get_config_item(config_key="send_key")
        return f"https://sctapi.ftqq.com/{send_key}.send"

    def __build_json(self, title: str, text: str, ext_info: dict = {}) -> dict:
        """
        构造请求json
        """
        ext_info = ext_info or {}
        # json
        json = {
            "title": title,
            "noip": self.get_config_item(config_key="noip") or False
        }
        # desp
        desp = text or title
        image = ext_info.get("image")
        if image:
            desp += f"\n\n![]({image})"
        json["desp"] = desp
        # channel
        channels = self.get_config_item(config_key="channel")
        if channels:
            channels = channels[0:2]
            channels = [str(channel) for channel in channels]
            channel = "|".join(channels)
            json["channel"] = channel
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
        if not title:
            logger.warn(f"发送消息中止: channel = {self.comp_name}, type = {type_str}, 消息标题为空")
            return False
        if not self.__check_config():
            return
        send_url = self.__build_url()
        json = self.__build_json(title=title, text=text, ext_info=ext_info)
        res = requests.post(url=send_url, json=json)
        res_json = res.json() or {}
        if res.ok or res_json:
            code = res_json.get("code")
            message = res_json.get("message")
            if code == 0:
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
                return True
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
                return False
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
            return False
