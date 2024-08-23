from abc import abstractmethod
from typing import Set, Dict, Any, List
from dotenv import set_key

from app.core.config import settings
from app.plugins.mergemessagenotify.channel import Channel
from app.log import logger
from app.schemas.types import MessageChannel, SystemConfigKey, NotificationType
from app.db.systemconfig_oper import SystemConfigOper
from app.schemas.message import NotificationSwitch


class SystemChannel(Channel):
    """
    系统消息通知渠道基类
    """

    # 组件key
    comp_key: str = "system"
    # 组件名称
    comp_name: str = "[系统]"
    # 组件顺序
    comp_order: int = 1

    def init_comp(self):
        """
        初始化组件
        """
        # 当通过页面操作保存配置时
        if self.check_stack_contain_save_config_request():
            config = self.get_config()
            try:
                self.apply_config(config=config)
                logger.info(f"渠道配置应用成功 - {self.comp_name}")
            except Exception as e:
                logger.error(f"渠道配置应用异常 - {self.comp_name}: {str(e)}", exc_info=True)

    def send_message(self, title: str, text: str, type: NotificationType = None, ext_info: dict = {}):
        """
        发送消息
        """
        # 系统渠道不需要实现发送消息
        pass

    def get_settings(self, include: Set[str] = None, exclude: Set[str] = None) -> Dict[str, Any]:
        """
        获取系统配置
        """
        return settings.dict(include=include, exclude=exclude) if settings else {}

    def update_settings(self, config: dict):
        """
        更新系统配置
        """
        config = config or {}
        for k, v in config.items():
            if k == "undefined":
                continue
            if hasattr(settings, k):
                if v == "None":
                    v = None
                setattr(settings, k, v)
                if v is None:
                    v = ''
                else:
                    v = str(v)
                set_key(settings.CONFIG_PATH / "app.env", k, v)

    def get_enable_notify_types(self, channel: MessageChannel) -> List[str]:
        """
        获取指定系统渠道启用的消息类型
        """
        if not channel:
            return []
        switchs = SystemConfigOper().get(SystemConfigKey.NotificationChannels)
        if not switchs:
            return [type.name for type in NotificationType if type]
        value2member_map: Dict[str, NotificationType] = NotificationType._value2member_map_
        mtypes= [value2member_map.get(switch.get("mtype")).name for switch in switchs if switch and switch.get(channel.name.lower()) and value2member_map.get(switch.get("mtype"))]
        return [type.name for type in NotificationType if type and type.name in mtypes]

    def update_enable_notify_types(self, channel: MessageChannel, enable_notify_types: List[str]):
        """
        更新指定系统渠道启用的消息类型
        """
        if not channel:
            return
        channel_key = channel.name.lower()
        enable_notify_types = enable_notify_types or []
        system_config_oper = SystemConfigOper()
        switchs: List[dict] = system_config_oper.get(SystemConfigKey.NotificationChannels) or []
        value2member_map: Dict[str, NotificationType] = NotificationType._value2member_map_
        switchs = [switch for switch in switchs if switch and switch.get("mtype") and value2member_map.get(switch.get("mtype"))]
        mtypes = []
        for switch in switchs:
            mtype = switch.get("mtype")
            mtypes.append(mtype)
            type: NotificationType = value2member_map.get(mtype)
            switch[channel_key] = type.name in enable_notify_types
        for type in NotificationType:
            if type.value in mtypes:
                continue
            switch = NotificationSwitch(mtype=type.value).dict()
            switch[channel_key] = type.name in enable_notify_types
            switchs.append(switch)
        system_config_oper.set(SystemConfigKey.NotificationChannels, switchs)

    @abstractmethod
    def apply_config(self, config: dict):
        """
        应用配置（使系统配置生效）
        """
        pass
