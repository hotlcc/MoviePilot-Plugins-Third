from typing import Tuple, List, Dict, Any
from enum import Enum
import requests

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger
from app.core.config import settings


class Sound(Enum):
    """
    铃声枚举
    """

    alarm = (2)
    anticipate = (4.5)
    bell = (1.4)
    birdsong = (0.67)
    bloom = (1.6)
    calypso = (0.9)
    chime = (4.5)
    choo = (2.2)
    descent = (1.9)
    electronic = (1.5)
    fanfare = (1.5)
    glass = (1.7)
    gotosleep = (3)
    healthnotification = (1.8)
    horn = (1.5)
    ladder = (1.3)
    mailsent = (1.5)
    minuet = (7)
    multiwayinvitation = (2.2)
    newmail = (1.5)
    newsflash = (2.9)
    noir = (1.9)
    paymentsuccess = (1.4)
    shake = (0.6)
    sherwoodforest = (4.7)
    silence = (0.5)
    spell = (2.9)
    suspense = (4.2)
    telegraph = (1.2)
    tiptoes = (1.5)
    typewriters = (2.6)
    update = (4.5)

    def __init__(self, second: float):
        """
        :param second: 时长
        """
        self.second = second

class BarkChannel(CustomChannel):
    """
    Bark渠道
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.bark"
    # 组件名称
    comp_name: str = "Bark"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 2

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {
        "server_url": "https://api.day.app",
        "group": "MoviePilot",
        "level": "active",
        "isArchive": True,
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
                        'placeholder': 'https://api.day.app',
                        'hint': '必填。缺省时为官方地址：https://api.day.app'
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
                        'model': 'push_key',
                        'label': '推送密钥',
                        'hint': '必填。推送密钥'
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
                        'model': 'ciphertext',
                        'label': '推送加密',
                        'type': 'password',
                        'hint': '选填。在发送推送时，对推送内容进行加密。这样，推送内容在传输过程中就不会被 Bark 服务器和苹果 APNs 服务器获取或泄露，从而保护你的隐私。'
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
                        'model': 'group',
                        'label': '消息分组',
                        'hint': '选填。对消息进行分组，推送将按分组显示在通知中心中。也可在历史消息列表中选择查看不同的分组。'
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
                            "title": f"{sound.name} ({sound.second}秒)",
                            "value": sound.name
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
                        'model': 'level',
                        'label': '通知级别',
                        'clearable': True,
                        'items': [
                            {"title": "立即亮屏显示通知", "value": "active"},
                            {"title": "时效性通知，可在专注状态显示", "value": "timeSensitive"},
                            {"title": "仅添加到通知列表而不亮屏提醒", "value": "passive"},
                        ],
                        'hint': '选填。可以为推送设置不同的铃声。缺省时为“立即亮屏显示通知”。'
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
                        'model': 'isArchive',
                        'label': '自动保存',
                        'hint': '是否自动保存推送消息。'
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
                        'model': 'autoCopy',
                        'label': '自动拷贝',
                        'hint': '是否自动拷贝消息内容到剪贴板。'
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
        push_key = self.get_config_item(config_key="push_key")
        return f"{server_url}/{push_key}"

    def __build_json(self, title: str, text: str, ext_info: dict = {}) -> dict:
        """
        构造请求json
        """
        ext_info = ext_info or {}
        # json
        json = {
            "title": title,
            "body": text or title
        }
        # sound
        sound = self.get_config_item(config_key="sound")
        if sound:
            json["sound"] = sound
        # icon
        image = ext_info.get("image")
        if image:
            json["icon"] = image
        # group
        group = self.get_config_item(config_key="group")
        if group:
            json["group"] = group
        # url
        link = ext_info.get("link")
        if link:
            json["url"] = link
        # level
        level = self.get_config_item(config_key="level")
        if level:
            json["level"] = level
        # isArchive
        isArchive = self.get_config_item(config_key="isArchive")
        if isArchive:
            json["isArchive"] = 1
        # autoCopy
        autoCopy = self.get_config_item(config_key="autoCopy")
        if autoCopy:
            json["autoCopy"] = 1
        # ciphertext
        ciphertext = self.get_config_item(config_key="ciphertext")
        if ciphertext:
            json["ciphertext"] = ciphertext
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
        json = self.__build_json(title=title, text=text, ext_info=ext_info)
        proxies = settings.PROXY if self.get_config_item(config_key="enable_proxy") else None
        res = requests.post(url=send_url, json=json, proxies=proxies)
        res_json = res.json() or {}
        if res.ok or res_json:
            code = res_json.get("code")
            message = res_json.get("message")
            if code == 200:
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
