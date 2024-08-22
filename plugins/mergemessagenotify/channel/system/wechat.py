from typing import Tuple, Dict, Any, List

from app.plugins.mergemessagenotify.channel.system import SystemChannel
from app.schemas.types import MessageChannel


class WechatChannel(SystemChannel):
    """
    微信渠道
    """

    # 组件key
    comp_key: str = f"{SystemChannel.comp_key}.{MessageChannel.Wechat.name.lower()}"
    # 组件名称
    comp_name: str = f"{SystemChannel.comp_name} {MessageChannel.Wechat.value}"
    # 组件顺序
    comp_order: int = SystemChannel.comp_order * 100 + 1

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {
        "WECHAT_PROXY": "https://qyapi.weixin.qq.com"
    }
    # 全部配置键
    __config_keys = {
        "WECHAT_CORPID",
        "WECHAT_APP_ID",
        "WECHAT_APP_SECRET",
        "WECHAT_PROXY",
        "WECHAT_TOKEN",
        "WECHAT_ENCODING_AESKEY",
        "WECHAT_ADMINS",
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
                        'model': 'WECHAT_CORPID',
                        'label': '企业ID',
                        'hint': '企业微信后台企业信息中的企业ID'
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
                        'model': 'WECHAT_APP_ID',
                        'label': '应用 AgentId',
                        'hint': '企业微信自建应用的AgentId'
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
                        'model': 'WECHAT_APP_SECRET',
                        'label': '应用Secret',
                        'hint': '企业微信自建应用的Secret'
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
                        'model': 'WECHAT_PROXY',
                        'label': '代理地址',
                        'hint': '微信消息的转发代理地址，2022年6月20日后创建的自建应用才需要，不使用代理时需要保留默认值'
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
                        'model': 'WECHAT_TOKEN',
                        'label': 'Token',
                        'hint': '微信企业自建应用->API接收消息配置中的Token'
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
                        'model': 'WECHAT_ENCODING_AESKEY',
                        'label': 'EncodingAESKey',
                        'hint': '微信企业自建应用->API接收消息配置中的EncodingAESKey'
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
                        'model': 'WECHAT_ADMINS',
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
        # 处理缺省配置
        self.save_default_config()
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
        enable_notify_types = self.get_enable_notify_types(channel=MessageChannel.Wechat)
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
        self.update_enable_notify_types(channel=MessageChannel.Wechat, enable_notify_types=enable_notify_types)
