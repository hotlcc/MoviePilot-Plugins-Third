from typing import Tuple, List, Dict, Any
from urllib.parse import urlencode
import requests

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger
from app.core.config import settings


class PushDeerChannel(CustomChannel):
    """
    PushDeer渠道 http://www.pushdeer.com
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.pushdeer"
    # 组件名称
    comp_name: str = "PushDeer"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 5

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {
        "server_url": "https://api2.pushdeer.com",
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
                    'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'server_url',
                        'label': '服务器地址',
                        'placeholder': 'https://api2.pushdeer.com',
                        'hint': '必填。缺省时为官方地址：https://api2.pushdeer.com'
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
                        'model': 'push_key',
                        'label': '推送密钥',
                        'placeholder': 'PDUxxx',
                        'hint': '必填。推送密钥'
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
        # 处理缺省配置
        self.save_default_config()
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
        if not self.get_config_item(config_key="push_key"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 推送密钥无效")
            return False
        return True

    def __build_url(self) -> str:
        """
        构造url
        """
        server_url: str = self.get_config_item(config_key="server_url")
        server_url = server_url.rstrip("/")
        return f"{server_url}/message/push"

    def __build_json(self, title: str, text: str, ext_info: dict = {}) -> dict:
        """
        构造请求json
        """
        ext_info = ext_info or {}
        # json
        json = {
            "pushkey": self.get_config_item(config_key="push_key"),
            "text": title,
            "type": "markdown"
        }
        # desp
        desp = text or title
        image = ext_info.get("image")
        if image:
            desp += f"\n\n![]({image})"
        json["desp"] = desp
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
        if not title:
            logger.warn(f"发送消息中止: channel = {self.comp_name}, type = {type_str}, 消息标题为空")
            return
        if not self.__check_config():
            return
        send_url = self.__build_url()
        json = self.__build_json(title=title, text=text, ext_info=ext_info)
        proxies = settings.PROXY if self.get_config_item(config_key="enable_proxy") else None
        res = requests.post(url=send_url, json=json, proxies=proxies)
        res_json = res.json() or {}
        if res.ok or res_json:
            code = res_json.get("code")
            message = res_json.get("error")
            if code == 0:
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
