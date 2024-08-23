from typing import Tuple, List, Dict, Any
import requests

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger


class ChanifyChannel(CustomChannel):
    """
    Chanify渠道
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.chanify"
    # 组件名称
    comp_name: str = "Chanify"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 3

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
                    'xxl': 12, 'xl': 12, 'lg': 12, 'md': 12, 'sm': 12, 'xs': 12
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'token',
                        'label': '推送令牌',
                        'hint': '必填。'
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
                        'model': 'sound',
                        'label': '启用铃声',
                        'hint': '收到消息时是否响铃。'
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
        if not self.get_config_item(config_key="token"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 推送令牌无效")
            return False
        return True

    def __build_url(self) -> str:
        """
        构造url
        """
        token = self.get_config_item(config_key="token")
        return f"https://api.chanify.net/v1/sender/{token}"

    def __build_json(self, title: str, text: str) -> dict:
        """
        构造请求json
        """
        # json
        json = {
            "title": title,
            "text": text,
        }
        # sound
        if self.get_config_item(config_key="sound"):
            json["sound"] = 1
        return json

    def send_message(self, title: str, text: str, type: NotificationType = None, ext_info: dict = {}):
        """
        发送消息
        """
        type_str = type.value if type else None
        enable_notify_types: List[str] = self.get_config_item("enable_notify_types")
        if (type and enable_notify_types and type.name not in enable_notify_types):
            logger.warn(f"发送消息中止: channel = {self.comp_name}, type = {type_str}, 消息类型不受支持")
            return
        if not self.__check_config():
            return
        send_url = self.__build_url()
        json = self.__build_json(title=title, text=text)
        res = requests.post(url=send_url, json=json)
        res_json = res.json() or {}
        if res.ok or res_json:
            code = res_json.get("res")
            message = res_json.get("msg")
            if not code:
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
