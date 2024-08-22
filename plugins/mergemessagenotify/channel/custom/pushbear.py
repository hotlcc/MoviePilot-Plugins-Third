from typing import Tuple, List, Dict, Any
from enum import Enum

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger
from app.utils.http import RequestUtils


class PushBearChannel(CustomChannel):
    """
    PushBear推送熊渠道
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.pushbear"
    # 组件名称
    comp_name: str = "PushBear"
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
                        'model': 'token',
                        'label': '用户令牌',
                        'hint': '必填。用户令牌'
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
                        'items': [{
                            'title': sc.value,
                            'value': sc.name
                        } for sc in SendChannel if sc],
                        'hint': '必填。缺省时为微信公众号。'
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

    def send_message(self, title: str, text: str, type: NotificationType = None, ext_info: dict = {}):
        """
        发送消息
        """
        type_str = type.value if type else None
        enable_notify_types: List[str] = self.get_config_item("enable_notify_types")
        if (type and enable_notify_types and type.name not in enable_notify_types):
            logger.warn(f"发送消息中止: channel = {self.comp_name}, type = {type.value}, 消息类型不受支持")
            return
        if not self.__check_config():
            return
        send_url = "http://www.pushplus.plus/send"
        json = {
            "token": self.get_config_item(config_key="token"),
            "title": title,
            "content": text,
            "template": "txt",
            "channel": self.get_config_item(config_key="channel"),
        }
        res = RequestUtils(timeout=60, content_type="application/json").post_res(send_url, json=json)
        if res:
            if res.status_code == 200:
                res_json = res.json() or {}
                code = res_json.get("code")
                message = res_json.get("msg")
                if code == 200:
                    logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
                else:
                    logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, 响应内容为空")
