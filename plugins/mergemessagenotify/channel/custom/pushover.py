import base64
import json as json_lib
from enum import Enum
from typing import Tuple, List, Dict, Any, Optional

import requests

from app.core.config import settings
from app.log import logger
from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType


# noinspection SpellCheckingInspection
class Sound(Enum):
    """
    铃声枚举
    """

    pushover = ("pushover", "Pushover(default)")
    bike = ("bike", "Bike")
    bugle = ("bugle", "Bugle")
    cashregister = ("cashregister", "Cash Register")
    classical = ("classical", "Classical")
    cosmic = ("cosmic", "Cosmic")
    falling = ("falling", "Falling")
    gamelan = ("gamelan", "Gamelan")
    incoming = ("incoming", "Incoming")
    intermission = ("intermission", "Intermission")
    magic = ("magic", "Magic")
    mechanical = ("mechanical", "Mechanical")
    pianobar = ("pianobar", "Piano Bar")
    siren = ("siren", "Siren")
    spacealarm = ("spacealarm", "Space Alarm")
    tugboat = ("tugboat", "Tug Boat")
    alien = ("alien", "Alien Alarm(long)")
    climb = ("climb", "Climb(long)")
    persistent = ("persistent", "Persistent(long)")
    echo = ("echo", "Pushover Echo(long)")
    updown = ("updown", "Up Down(long)")
    vibrate = ("vibrate", "Vibrate Only")
    none = ("none", "None(silent)")

    def __init__(self, code: str, title: str):
        self.code = code
        self.title = title


class Priority(Enum):
    """
    优先级枚举
    """

    Lowest = (-2, "最低")
    Low = (-1, "低")
    Normal = (0, "一般")
    High = (1, "高")
    Emergency = (2, "紧急")

    def __init__(self, code: int, title: str):
        self.code = code
        self.title = title


class PushoverChannel(CustomChannel):
    """
    Pushover渠道
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.pushover"
    # 组件名称
    comp_name: str = "Pushover"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 10

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {
        "server_url": "https://api.pushover.net",
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
        config_default_server_url = self.config_default.get("server_url")
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
                        'placeholder': config_default_server_url,
                        'hint': f'必填。缺省时为：{config_default_server_url}'
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
                        'model': 'user_key',
                        'label': '用户Key',
                        'hint': '必填。用户Key'
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
                        'model': 'api_token',
                        'label': 'API Token',
                        'hint': '必填。API Token'
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
                        'model': 'sound',
                        'label': '推送铃声',
                        'clearable': True,
                        'items': [{
                            "title": sound.title,
                            "value": sound.code
                        } for sound in Sound if sound],
                        'hint': '选填。可以为推送设置不同的铃声。'
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
                        'model': 'priority',
                        'label': '消息优先级',
                        'clearable': True,
                        'items': [{
                            "title": priority.title,
                            "value": priority.code
                        } for priority in Priority if priority],
                        'hint': '选填。可以为消息设置不同的优先级。'
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
        if not self.get_config_item(config_key="user_key"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 用户Key无效")
            return False
        if not self.get_config_item(config_key="api_token"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, API Token 无效")
            return False
        return True

    def __build_url(self) -> str:
        """
        构造url
        """
        server_url: str = self.get_config_item(config_key="server_url")
        server_url = server_url.rstrip("/")
        return f"{server_url}/1/messages.json"

    def __build_json(self, title: str, text: str, ext_info: dict = None) -> dict:
        """
        构造请求json
        """
        ext_info = ext_info or {}

        # json
        json = {
            "user": self.get_config_item(config_key="user_key"),
            "token": self.get_config_item(config_key="api_token"),
        }
        # 标题和内容
        json.update({
            "title": title,
            "message": text or title
        })
        # sound
        sound = self.get_config_item(config_key="sound")
        if sound:
            json["sound"] = sound
        # priority
        priority = self.get_config_item(config_key="priority")
        if priority is not None:
            json["priority"] = priority
            if priority == Priority.Emergency.code:
                json.update({
                    "retry": 60,
                    "expire": 1800,
                })
        # image
        image = ext_info.get("image")
        if image:
            json["attachment_base64"] = self.__download_image_to_base64(image_url=image)
        # url
        link = ext_info.get("link")
        if link:
            json.update({
                "url": link,
                "url_title": link,
            })

        return json

    def __download_image_to_base64(self, image_url) -> Optional[str]:
        try:
            res = requests.get(url=image_url, stream=True, timeout=5)
            res.raise_for_status()
            return base64.b64encode(res.content).decode("utf-8").strip()
        except Exception as e:
            logger.warn("下载图片数据并转Base64异常")
            return None

    def send_message(self, title: str, text: str, type: NotificationType = None, ext_info: dict = None) -> bool:
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
        url = self.__build_url()
        json = self.__build_json(title=title, text=text, ext_info=ext_info)
        proxies = settings.PROXY if self.get_config_item(config_key="enable_proxy") else None
        res = requests.post(url=url, json=json, proxies=proxies)
        res_json: dict = res.json() or {}
        request_id = res_json.get("request")
        if res_json.get("status") == 1:
            logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}, request_id = {request_id}")
            return True
        else:
            errors = res_json.get("errors")
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, request_id = {request_id}, errors = {json_lib.dumps(errors)}")
            return False
