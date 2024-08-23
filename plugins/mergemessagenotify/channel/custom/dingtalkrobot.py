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


class DingtalkRobotChannel(CustomChannel):
    """
    钉钉机器人渠道 https://open.dingtalk.com/document/orgapp/custom-robots-send-group-messages
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.dingtalkrobot"
    # 组件名称
    comp_name: str = "钉钉机器人"
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
                        'model': 'access_token',
                        'label': 'Access Token',
                        'placeholder': 'BE3xxx',
                        'hint': '必填。自定义机器人调用接口的凭证。'
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
                        'model': 'secret',
                        'label': '加签密钥',
                        'placeholder': 'SECxxx',
                        'hint': '选填。自定义机器人的安全设置使用的是加签方式时需要配置该项。'
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
                        'model': 'atMobiles',
                        'label': '@手机号',
                        'placeholder': '15xxx,18xxx',
                        'hint': '选填。被@的群成员手机号，多个用英文逗号,分隔。'
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
                        'model': 'atUserIds',
                        'label': '@UserId',
                        'placeholder': 'user001,user002',
                        'hint': '选填。被@的群成员userId，多个用英文逗号,分隔。'
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
        if not self.get_config_item(config_key="access_token"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, Access Token 无效")
            return False
        return True

    @classmethod
    def __sign(cls, timestamp: int, secret: str) -> str:
        """
        构造签名字符串
        """
        secret_enc = secret.encode('utf-8')
        string_to_sign = f"{timestamp}\n{secret}"
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc,digestmod=hashlib.sha256).digest()
        sign = quote_plus(base64.b64encode(hmac_code))
        return sign

    def __build_query(self) -> str:
        """
        构造请求query
        """
        # query
        query = {
            'access_token': self.get_config_item(config_key="access_token"),
        }
        # 签名相关
        secret = self.get_config_item(config_key="access_token")
        if secret:
            timestamp = round(time.time() * 1000)
            sign = self.__sign(timestamp, secret)
            query["timestamp"] = timestamp
            query["sign"] = sign
        return urlencode(query)

    def __build_url(self) -> str:
        """
        构造url
        """
        query = self.__build_query()
        return f"https://oapi.dingtalk.com/robot/send?{query}"

    def __build_message(self, title: str, text: str, ext_info: dict = {}) -> Tuple[str, dict]:
        """
        构造消息
        """
        ext_info = ext_info or {}
        link = ext_info.get("link")
        image = ext_info.get("image")
        # 链接类型
        if (link and image):
            return "link", {
                "title": title,
                "text": text,
                "picUrl": image,
                "messageUrl": link,
            }
        # Markdown 类型
        if image or title:
            markdown = f"{text}\n\n![]({image})" if image else text
            return "markdown", {
                "title": title,
                "text": markdown,
            }
        # 文本消息
        return "text", {
            "content": text,
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
            msgtype: msg,
            "at": {
                "atMobiles": self.__split_multstr(raw_str=self.get_config_item(config_key="atMobiles")),
                "atUserIds": self.__split_multstr(raw_str=self.get_config_item(config_key="atUserIds")),
                "isAtAll": True if self.get_config_item(config_key="isAtAll") else False,
            }
        }
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
        if not text:
            logger.warn(f"发送消息中止: channel = {self.comp_name}, type = {type_str}, 消息内容为空")
            return
        if not self.__check_config():
            return
        send_url = self.__build_url()
        json = self.__build_json(title=title, text=text, ext_info=ext_info)
        res = requests.post(url=send_url, json=json)
        res_json = res.json() or {}
        if res.ok or res_json:
            code = res_json.get("errcode")
            message = res_json.get("errmsg")
            if code == "0":
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
