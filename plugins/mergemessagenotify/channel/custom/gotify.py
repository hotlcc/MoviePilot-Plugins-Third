from typing import Tuple, List, Dict, Any
import requests

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger
from app.core.config import settings


class GotifyChannel(CustomChannel):
    """
    Gotify渠道 https://gotify.net/
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.gotify"
    # 组件名称
    comp_name: str = "Gotify"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 8

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
                        'model': 'server_url',
                        'label': '服务器地址',
                        'placeholder': 'http://127.0.0.1:8080',
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
                    'component': 'VTextField',
                    'props': {
                        'model': 'token',
                        'label': 'Token',
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
        if not self.get_config_item(config_key="token"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, Token无效")
            return False
        return True

    def __build_url(self) -> str:
        """
        构造url
        """
        server_url: str = self.get_config_item(config_key="server_url")
        server_url = server_url.rstrip("/")
        token = self.get_config_item(config_key="token")
        return f"{server_url}/message?token={token}"

    def __build_json(self, title: str, text: str, ext_info: dict = {}) -> dict:
        """
        构造请求json
        """
        title = title or ""
        text = text or ""
        ext_info = ext_info or {}
        # image
        image = ext_info.get("image")
        # message
        message = f"{text}\n![]({image})" if image else text
        # contnetType
        contentType = "text/markdown" if image else "text/plain"
        # client::notification
        notification = {}
        # link
        link = ext_info.get("link")
        if link:
            notification.update({
                "click": {
                    "url": link
                }
            })
        if image:
            notification.update({
                "bigImageUrl": image
            })
        # extras
        extras = {
            "client::display": {
                "contentType": contentType
            },
            "client::notification": notification
        }
        # json
        json = {
            "title": title,
            "message": message,
            "priority": 2,
            "extras": extras
        }
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
        send_url = self.__build_url()
        json = self.__build_json(title=title, text=text)
        proxies = settings.PROXY if self.get_config_item(config_key="enable_proxy") else None
        res = requests.post(url=send_url, json=json, proxies=proxies)
        res_json = res.json() or {}
        if res.ok or res_json:
            code = res_json.get("errorCode")
            message = res_json.get("errorDescription")
            if not code:
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
                return True
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
                return False
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
            return False
