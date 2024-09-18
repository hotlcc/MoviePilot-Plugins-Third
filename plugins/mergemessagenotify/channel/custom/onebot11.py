from typing import Dict, Any, Tuple, List, Union
import requests

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger
from app.core.config import settings


class OneBot11Channel(CustomChannel):
    """
    OneBot-11 通用聊天机器人规范渠道 https://github.com/botuniverse/onebot-11
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.onebot-11"
    # 组件名称
    comp_name: str = "OneBot-11"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 11

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
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'server_url',
                        'label': '服务器地址',
                        'placeholder': 'http://192.168.1.11:1111',
                        'hint': '必填。实现OneBot-11规范的服务器基础地址，如：go-cqhttp。'
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
                        'model': 'user_ids',
                        'label': '目标用户',
                        'placeholder': '123456,654321',
                        'hint': '选填。对方用户号，多个用英文逗号,分隔；与【目标群组】不允许同时为空。'
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
                        'model': 'group_ids',
                        'label': '目标群组',
                        'placeholder': '1234567,7654321',
                        'hint': '选填。对方群组号，多个用英文逗号,分隔；与【目标用户】不允许同时为空。'
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
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 8, 'xl': 8, 'lg': 8, 'md': 8, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VAlert',
                    'props': {
                        'type': 'info',
                        'variant': 'tonal'
                    },
                    'content': [{
                        'component': 'a',
                        'props': {
                            'href': 'https://github.com/botuniverse/onebot-11',
                            'target': '_blank'
                        },
                        'text': '点击这里了解什么是 OneBot-11？'
                    }]
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
        if not self.get_config_item(config_key="user_ids") and not self.get_config_item(config_key="group_ids"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 目标用户与目标群组不允许同时为空")
            return False
        return True

    def __build_url(self) -> str:
        """
        构造url
        """
        server_url: str = self.get_config_item(config_key="server_url")
        server_url = server_url.rstrip("/")
        return f"{server_url}/send_msg"

    @classmethod
    def __split_multstr(cls, raw_str: str) -> List[str]:
        """
        分割复合字符串
        """
        return list(set([item.strip() for item in raw_str.split(",") if item and item.strip()])) if raw_str else []

    def __build_json(self, user_id: Union[int, str],
                           group_id: Union[int, str],
                           message: str) -> dict:
        """
        构造请求json
        """
        json = {
            "message": message
        }
        if user_id:
            json["user_id"] = user_id
        if group_id:
            json["group_id"] = group_id
        return json

    def __send_msg(self, url: str,
                         user_id: Union[int, str],
                         group_id: Union[int, str],
                         message: str,
                         type: NotificationType = None,
                         proxies: bool = False) -> bool:
        """
        发送OneBot-11规范消息
        """
        type_str = type.value if type else None
        json = self.__build_json(user_id=user_id, group_id=group_id, message=message)
        res = requests.post(url=url, json=json, proxies=proxies)
        res_json = res.json() or {}
        if res.ok:
            code = res_json.get("retcode")
            message = res_json.get("msg")
            if code == 0 or code == 1:
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}, user_id = {user_id}, group_id = {group_id}")
                return True
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, user_id = {user_id}, group_id = {group_id}, code = {code}, message = {message}")
                return False
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, user_id = {user_id}, group_id = {group_id}, status_code = {res.status_code}, reason = {res.reason}")
            return False

    def __build_message(self, title: str, text: str, ext_info: dict = {}) -> str:
        """
        构造消息
        """
        message = ""
        if title:
            message += f"【{title}】\n\n"
        if text:
            message += f"{text}\n\n"
        image = ext_info.get("image")
        if image:
            message += f"[CQ:image,file={image}]\n\n"
        return message

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
        message = self.__build_message(title=title, text=text, ext_info=ext_info)
        proxies = settings.PROXY if self.get_config_item(config_key="enable_proxy") else None
        # 成功失败数
        success_count = 0
        fail_count = 0
        # 发送私聊信息
        user_ids = self.get_config_item("user_ids")
        user_ids = self.__split_multstr(raw_str=user_ids)
        for user_id in user_ids:
            success = self.__send_msg(url=send_url, user_id=user_id, group_id=None, message=message, type=type, proxies=proxies)
            if success:
                success_count += 1
            else:
                fail_count += 1
        # 发送群聊信息
        group_ids = self.get_config_item("group_ids")
        group_ids = self.__split_multstr(raw_str=group_ids)
        for group_id in group_ids:
            success = self.__send_msg(url=send_url, user_id=None, group_id=group_id, message=message, type=type, proxies=proxies)
            if success:
                success_count += 1
            else:
                fail_count += 1
        return fail_count == 0
