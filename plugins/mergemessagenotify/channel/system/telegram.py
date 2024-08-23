from typing import Tuple, Dict, Any, List

from app.plugins.mergemessagenotify.channel.system import SystemChannel
from app.schemas.types import MessageChannel


class TelegramChannel(SystemChannel):
    """
    Telegram渠道
    """

    # 组件key
    comp_key: str = f"{SystemChannel.comp_key}.{MessageChannel.Telegram.name.lower()}"
    # 组件名称
    comp_name: str = f"{SystemChannel.comp_name} {MessageChannel.Telegram.value}"
    # 组件顺序
    comp_order: int = SystemChannel.comp_order * 100 + 2

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {}
    # 全部配置键
    __config_keys = {
        "TELEGRAM_TOKEN",
        "TELEGRAM_CHAT_ID",
        "TELEGRAM_USERS",
        "TELEGRAM_ADMINS",
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
                        'model': 'TELEGRAM_TOKEN',
                        'label': 'Bot Token',
                        'hint': 'Telegram机器人token，格式：123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'
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
                        'model': 'TELEGRAM_CHAT_ID',
                        'label': 'Chat ID',
                        'hint': '接受消息通知的用户、群组或频道Chat ID'
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
                        'model': 'TELEGRAM_USERS',
                        'label': '用户白名单',
                        'placeholder': '多个用,分隔',
                        'hint': '可使用Telegram机器人的用户ID清单，多个用户用,分隔，不填写则所有用户都能使用'
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
                        'model': 'TELEGRAM_ADMINS',
                        'label': '管理员白名单',
                        'placeholder': '多个用,分隔',
                        'hint': '可使用管理菜单及命令的用户ID列表，多个ID使用,分隔'
                    }
                }]
            }]
        }
        row2 = self.build_notify_type_select_row_element()
        elements = [row1, row2]
        # 处理初始配置：从系统配置中加载组件配置
        self.save_system_config()
        return elements, config_suggest

    def save_system_config(self):
        """
        从系统配置中加载组件配置
        """
        config = {}
        settings = self.get_settings(include=self.__config_keys) or {}
        for key, value in settings.items():
            if value != None and value != '':
                config[key] = value
        enable_notify_types = self.get_enable_notify_types(channel=MessageChannel.Telegram)
        if enable_notify_types:
            config["enable_notify_types"] = enable_notify_types
        if config:
            self.update_config(config=config)

    def apply_config(self, config: dict):
        """
        应用配置（使系统配置生效）
        """
        config = config or {}
        # 渠道配置
        self.update_settings(config=config)
        # 消息类型开关配置
        enable_notify_types = config.get("enable_notify_types")
        self.update_enable_notify_types(channel=MessageChannel.Telegram, enable_notify_types=enable_notify_types)
