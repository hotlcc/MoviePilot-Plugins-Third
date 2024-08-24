from typing import Tuple, List, Dict, Any
from urllib.parse import urlencode
import requests
import time
import hmac
import hashlib
import base64

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger


class FeishuBotChannel(CustomChannel):
    """
    飞书机器人渠道 https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.feishubot"
    # 组件名称
    comp_name: str = "飞书机器人"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 10

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
                        'placeholder': 'xxx',
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
                        'hint': '选填。自定义机器人的安全设置使用的是签名校验时需要配置该项。'
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
                        'model': 'at_user_ids',
                        'label': '@UserId',
                        'placeholder': 'ou_xxx1,ou_xxx2',
                        'hint': '选填。被@的群成员OpenID或UserID，多个用英文逗号,分隔。'
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
                        'model': 'at_all',
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
    def __sign(cls, timestamp: str, secret: str) -> str:
        """
        构造签名字符串
        """
        string_to_sign = f"{timestamp}\n{secret}"
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return sign

    def __build_url(self) -> str:
        """
        构造url
        """
        access_token = self.get_config_item(config_key="access_token")
        return f"https://open.feishu.cn/open-apis/bot/v2/hook/{access_token}"

    @classmethod
    def __build_text_at_user(cls, user_id: str, user_name: str = "") -> str:
        """
        构造文本消息的@用户字符串
        """
        if not user_id:
            return ""
        user_name = user_name or ""
        return f'<at user_id="{user_id}">{user_name}</at>'

    @classmethod
    def __build_text_at_all(cls) -> str:
        """
        构造文本消息的@所有人字符串
        """
        return cls.__build_text_at_user(user_id="all", user_name="所有人")

    def __build_message(self, title: str, text: str, ext_info: dict = {}) -> Tuple[str, dict]:
        """
        构造消息
        """
        ext_info = ext_info or {}
        link = ext_info.get("link")
        at_user_ids = self.__split_multstr(raw_str=self.get_config_item(config_key="at_user_ids"))
        at_all = self.get_config_item(config_key="at_all")
        # 文本消息
        if not title and text and not link:
            if at_user_ids:
                text += f"\n{' '.join([self.__build_text_at_user(user_id=user_id) for user_id in at_user_ids if user_id])}"
            if at_all:
                text += f"\n{self.__build_text_at_all()}"
            return "text", {
                "text": text
            }
        # 富文本消息
        content = [[{
            "tag": "text",
            "text": text
        }]]
        if link:
            content.append([{
                "tag": "a",
                "text": ">>点此查看详情<<",
                "href": link
            }])
        at_paragraph = []
        if at_user_ids:
            for user_id in at_user_ids:
                at_paragraph.append({
                    "tag": "at",
                    "user_id": user_id
                })
        if at_all:
            at_paragraph.append({
                "tag": "at",
                "user_id": "all",
                "user_name": "所有人"
            })
        if at_paragraph:
            content.append(at_paragraph)
        return "post", {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": content
                }
            }
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
            "msg_type": msgtype,
            "content": msg
        }
        # 签名
        secret = self.get_config_item(config_key="secret")
        if secret:
            timestamp = str(round(time.time()))
            json["timestamp"] = timestamp
            json["sign"] = self.__sign(timestamp=timestamp, secret=secret)
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
            return False
        send_url = self.__build_url()
        json = self.__build_json(title=title, text=text, ext_info=ext_info)
        res = requests.post(url=send_url, json=json)
        res_json = res.json() or {}
        if res.ok or res_json:
            code = res_json.get("code")
            message = res_json.get("msg")
            if code == 0:
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
                return True
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
                return False
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
            return False
