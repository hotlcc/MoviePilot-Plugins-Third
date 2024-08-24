from typing import Tuple, List, Dict, Any
from urllib.parse import quote
import base64
import requests

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger
from app.core.config import settings


class NtfyChannel(CustomChannel):
    """
    Ntfy渠道 https://ntfy.sh
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.ntfy"
    # 组件名称
    comp_name: str = "Ntfy"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 4

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {
        "server_url": "https://ntfy.sh",
        "topic": "MoviePilot",
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
                        'model': 'server_url',
                        'label': '服务器地址',
                        'placeholder': 'https://ntfy.sh',
                        'hint': '必填。缺省时为官方地址：https://ntfy.sh'
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
                        'label': '主题',
                        'placeholder': 'MoviePilot',
                        'hint': '必填。消息主题，缺省时为：MoviePilot'
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
                        'model': 'token',
                        'label': '访问令牌',
                        'placeholder': 'tk_xxxxxx',
                        'hint': '选填。访问令牌和用户名密码二选一，访问令牌更安全，优先使用访问令牌。'
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
                        'model': 'username',
                        'label': '用户名',
                        'hint': '选填。用户名密码和访问令牌二选一，访问令牌更安全，优先使用访问令牌。'
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
                        'model': 'password',
                        'label': '密码',
                        'type': 'password',
                        'hint': '选填。用户名密码和访问令牌二选一，访问令牌更安全，优先使用访问令牌。'
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
        if not self.get_config_item(config_key="topic"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 主题无效")
            return False
        token = self.get_config_item(config_key="token")
        username = self.get_config_item(config_key="username")
        password = self.get_config_item(config_key="password")
        if not token and (not username or not password):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 访问令牌或用户名密码无效")
            return False
        return True

    def __build_url(self) -> str:
        """
        构造url
        """
        server_url: str = self.get_config_item(config_key="server_url")
        server_url = server_url.rstrip("/")
        topic = self.get_config_item(config_key="topic")
        topic = quote(topic)
        return f"{server_url}/{topic}"

    @classmethod
    def __base64_encode(cls, raw_str: str) -> str:
        """
        base64编码字符串
        """
        return str(base64.b64encode(raw_str.encode("utf-8")), 'utf-8') if raw_str else None

    def __build_basic_auth_value(cls, username: str, password: str) -> str:
        """
        构造Basic认证值
        """
        raw_str = f"{username or ''}:{password or ''}"
        return cls.__base64_encode(raw_str=raw_str)

    def __build_headers(self, title: str, type: NotificationType) -> dict:
        """
        构造headers
        """
        # headers
        headers = {
            "X-Markdown": "true"
        }
        # X-Title
        if title:
            headers["X-Title"] = title.encode(encoding="utf-8")
        # X-Tags
        if type:
            headers["X-Tags"] = type.value.encode(encoding="utf-8")
        # Authorization
        token = self.get_config_item(config_key="token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        else:
            username = self.get_config_item(config_key="username")
            password = self.get_config_item(config_key="password")
            if username and password:
                basic_auth_value = self.__build_basic_auth_value(username=username, password=password)
                headers["Authorization"] = f"Basic {basic_auth_value}"
        return headers

    def __build_data(self, title: str, text: str, ext_info: dict = {}) -> bytes:
        """
        构造请求数据
        """
        ext_info = ext_info or {}
        data = text or title
        image = ext_info.get("image")
        if image:
            data += f"\n\n![]({image})"
        return data.encode(encoding="utf-8")

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
        headers = self.__build_headers(title=title, type=type)
        data = self.__build_data(title=title, text=text, ext_info=ext_info)
        proxies = settings.PROXY if self.get_config_item(config_key="enable_proxy") else None
        res = requests.post(url=send_url, headers=headers, data=data, proxies=proxies)
        res_json = res.json() or {}
        if res.ok or res_json:
            code = res_json.get("code")
            message = res_json.get("error")
            if not code:
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
                return True
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
                return False
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
            return False
