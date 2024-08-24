from typing import Tuple, List, Dict, Any
from urllib.parse import urlencode, quote_plus
import requests
import time
import hmac
import hashlib
import base64

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger


class QiyeWeixinBotChannel(CustomChannel):
    """
    企业微信机器人渠道
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.qiyeweixinbot"
    # 组件名称
    comp_name: str = "企业微信机器人"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 9

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
                        'model': 'key',
                        'label': '密钥',
                        'placeholder': 'xxx',
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
                        'model': 'mentioned_mobile_list',
                        'label': '@手机号',
                        'placeholder': '15xxx,18xxx',
                        'hint': '选填。被@的群成员手机号，多个用英文逗号,分隔。'
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
                        'model': 'mentioned_list',
                        'label': '@UserId',
                        'placeholder': 'user001,user002',
                        'hint': '选填。被@的群成员userId，多个用英文逗号,分隔。'
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
                        'model': 'isAtAll',
                        'label': '@所有人',
                        'hint': '是否@所有人。'
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
        if not self.get_config_item(config_key="key"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 密钥无效")
            return False
        return True

    def __build_url(self) -> str:
        """
        构造url
        """
        key = self.get_config_item(config_key="key")
        return f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"

    def __build_message_content(self, title: str, text: str, ext_info: dict = {}) -> Tuple[str, dict]:
        """
        构造消息内容
        """
        ext_info = ext_info or {}
        image = ext_info.get("image")
        # 文本类型
        if not title and text and not image:
            return "text", text
        # Markdown类型
        markdown = ""
        if title:
            markdown += f"# {title}\n\n"
        if text:
            markdown += f"> {text}\n\n"
        if image:
            markdown += f"![]({image})\n\n"
        return "markdown", markdown

    def __build_message(self, title: str, text: str, ext_info: dict = {}) -> Tuple[str, dict]:
        """
        构造消息
        """
        msgtype, content = self.__build_message_content(title=title, text=text, ext_info=ext_info)
        mentioned_mobile_list = self.__split_multstr(raw_str=self.get_config_item(config_key="mentioned_mobile_list"))
        mentioned_list = self.__split_multstr(raw_str=self.get_config_item(config_key="mentioned_list"))
        if self.get_config_item(config_key="isAtAll"):
            mentioned_mobile_list.append("@all")
        return msgtype, {
            "content": content,
            "mentioned_mobile_list": mentioned_mobile_list,
            "mentioned_list": mentioned_list
        }

    @classmethod
    def __split_multstr(cls, raw_str: str) -> List[str]:
        """
        分割复合字符串
        """
        return list(set([item.strip() for item in raw_str.split(",") if item and item.strip()])) if raw_str else []

    def __build_json(self, title: str, text: str, ext_info: dict = {}) -> dict:
        """
        构造请求json
        """
        msgtype, msg = self.__build_message(title=title, text=text, ext_info=ext_info)
        # json
        json = {
            "msgtype": msgtype,
            msgtype: msg
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
        if not text:
            logger.warn(f"发送消息中止: channel = {self.comp_name}, type = {type_str}, 消息内容为空")
            return False
        if not self.__check_config():
            return
        send_url = self.__build_url()
        json = self.__build_json(title=title, text=text, ext_info=ext_info)
        res = requests.post(url=send_url, json=json)
        res_json = res.json() or {}
        if res.ok or res_json:
            code = res_json.get("errcode")
            message = res_json.get("errmsg")
            if code == 0:
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
                return True
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
                return False
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
            return False
