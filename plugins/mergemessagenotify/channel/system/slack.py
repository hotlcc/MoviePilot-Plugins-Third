from typing import Tuple, Dict, Any, List

from app.plugins.mergemessagenotify.channel.system import SystemChannel
from app.schemas.types import MessageChannel


class SlackChannel(SystemChannel):
    """
    Slack渠道
    """

    # 组件key
    comp_key: str = f"{SystemChannel.comp_key}.{MessageChannel.Slack.name.lower()}"
    # 组件名称
    comp_name: str = f"{SystemChannel.comp_name} {MessageChannel.Slack.value}"
    # 组件顺序
    comp_order: int = SystemChannel.comp_order * 100 + 3

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {}
    # 全部配置键
    __config_keys = {
        "SLACK_OAUTH_TOKEN",
        "SLACK_APP_TOKEN",
        "SLACK_CHANNEL",
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
                        'model': 'SLACK_OAUTH_TOKEN',
                        'label': 'Slack Bot User OAuth Token',
                        'placeholder': 'xoxb-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx',
                        'hint': 'Slack应用`OAuth & Permissions`页面中的`Bot User OAuth Token`'
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
                        'model': 'SLACK_APP_TOKEN',
                        'label': 'Slack App-Level Token',
                        'placeholder': 'xapp-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx',
                        'hint': 'Slack应用`OAuth & Permissions`页面中的`App-Level Token`'
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
                        'model': 'SLACK_CHANNEL',
                        'label': '频道名称',
                        'placeholder': '全体',
                        'hint': '消息发送频道，默认`全体`'
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
        enable_notify_types = self.get_enable_notify_types(channel=MessageChannel.Slack)
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
        self.update_enable_notify_types(channel=MessageChannel.Slack, enable_notify_types=enable_notify_types)
