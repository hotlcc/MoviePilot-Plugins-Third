from typing import Tuple, List, Dict, Any
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger


class EmailChannel(CustomChannel):
    """
    邮件渠道
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.email"
    # 组件名称
    comp_name: str = "邮件"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 61

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {
        "from_name": "MoviePilot"
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
                        'model': 'smtp_host',
                        'label': 'SMTP主机',
                        'placeholder': 'smtp.exmail.qq.com',
                        'hint': '必填。SMTP邮件服务器的IP或域名。'
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
                        'model': 'smtp_port',
                        'label': 'SMTP端口',
                        'type': 'number',
                        'placeholder': '587',
                        'hint': '必填。SMTP邮件服务器的端口。'
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
                        'label': '邮箱账户',
                        'type': 'email',
                        'placeholder': 'xxx@qq.com',
                        'hint': '必填。邮箱账户。'
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
                        'label': '邮箱密码',
                        'type': 'password',
                        'hint': '必填。邮箱密码。'
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
                        'model': 'from_name',
                        'label': '发件人署名',
                        'placeholder': 'MoviePilot',
                        'hint': '选填。发件人署名，缺省时为MoviePilot。'
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
                        'model': 'to_addrs',
                        'label': '收件人',
                        'placeholder': 'xxx@qq.com,xxx@qq.com',
                        'hint': '必填。收件人邮箱，多个用英文逗号,分隔。'
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
        if not self.get_config_item(config_key="smtp_host"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, SMTP主机无效")
            return False
        if not self.get_config_item(config_key="smtp_port"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, SMTP端口无效")
            return False
        if not self.get_config_item(config_key="username"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 邮箱账户无效")
            return False
        if not self.get_config_item(config_key="password"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 邮箱密码无效")
            return False
        to_addrs= self.__split_multstr(self.get_config_item(config_key="to_addrs"))
        if not to_addrs:
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 收件人无效")
            return False
        return True

    def __build_message(self, title: str, text: str, to_addrs: List[str], ext_info: dict = {}) -> MIMEText:
        """
        构造消息对象
        """
        ext_info = ext_info or {}
        image = ext_info.get("image")
        if image:
            html = f'<div>{text}</div><br><img src="{image}"></img>'
            message = MIMEText(html, "html", "utf-8")
        else:
            message = MIMEText(text, "plain", "utf-8")
        from_name = self.get_config_item(config_key="from_name")
        username = self.get_config_item(config_key="username")
        message["From"] = formataddr(pair=(from_name, username))
        message["To"] = ",".join(to_addrs) if to_addrs else ""
        message["Subject"] = Header(title, "utf-8")
        return message

    @classmethod
    def __split_multstr(cls, raw_str: str) -> List[str]:
        """
        分割复合字符串
        """
        return list(set([item.strip() for item in raw_str.split(",") if item and item.strip()])) if raw_str else []

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
        # 发送邮件
        smtp_host= self.get_config_item(config_key="smtp_host")
        smtp_port= self.get_config_item(config_key="smtp_port")
        username= self.get_config_item(config_key="username")
        password= self.get_config_item(config_key="password")
        to_addrs= self.__split_multstr(self.get_config_item(config_key="to_addrs"))
        message = self.__build_message(title=title, text=text, to_addrs=to_addrs, ext_info=ext_info)
        try:
            smtp = smtplib.SMTP_SSL(host=smtp_host, port=smtp_port, timeout=60)
            smtp.login(user=username, password=password)
            smtp.sendmail(from_addr=username, to_addrs=to_addrs, msg=message.as_string())
            logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
            return True
        except Exception as e:
            logger.error(f"发送消息失败: channel = {self.comp_name}, type = {type_str}", exc_info=True)
            return False
        finally:
            if smtp:
                smtp.quit()
