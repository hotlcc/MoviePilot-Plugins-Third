from abc import abstractmethod
from typing import Set, Dict, Any, List
from dotenv import set_key

from app.core.config import settings
from app.plugins.mergemessagenotify.channel import Channel
from app.log import logger
from app.schemas.types import MessageChannel, SystemConfigKey, NotificationType
from app.db.systemconfig_oper import SystemConfigOper
from app.schemas.message import NotificationSwitch
from app.core.module import ModuleManager
from app.plugins.mergemessagenotify.util import ThreadLocalUtil


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

    def send_message(self, title: str, text: str, type: NotificationType = None, ext_info: dict = {}) -> bool:
        """
        发送消息
        """
        # 系统渠道不需要实现发送消息
        return False

    def get_settings(self, include: Set[str] = None, exclude: Set[str] = None) -> Dict[str, Any]:
        """
        获取系统配置
        """
        return settings.dict(include=include, exclude=exclude) if settings else {}

    def __update_setting(self, key: str, value: any) -> bool:
        """
        更新系统配置项
        :return: 是否更新（更新前后是否有变化）
        """
        if key == "undefined":
            return False
        if not hasattr(settings, key):
            return False
        if value == "None":
            value = None
        # 更新前的运行时配置值
        old_runtime_value = getattr(settings, key)
        # 更新运行时值和环境变量文件值
        setattr(settings, key, value)
        value = str(value) if value is not None else ""
        set_key(settings.CONFIG_PATH / "app.env", key, value)
        # 是否有更新
        has_change = (value != old_runtime_value)
        return has_change

    def update_settings(self, config: dict) -> bool:
        """
        更新系统配置
        :return: 是否更新（更新前后是否有变化）
        """
        config = config or {}
        change_count = 0
        for k, v in config.items():
            has_change = self.__update_setting(k, v)
            if has_change:
                change_count += 1
        has_change =  change_count > 0
        # 如果有变化就标记需要重载系统模块
        if has_change:
            self.mark_need_reload_system_modules()
        return has_change

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

    def get_system_module_instance(self, module_id: str) -> Any:
        """
        根据模块id获取系统模块实例
        """
        return ModuleManager().get_running_module(module_id=module_id)

    def init_system_module_instance(self, module_id: str):
        """
        根据模块id初始化系统模块实例
        """
        try:
            system_module_instance = self.get_system_module_instance(module_id=module_id)
            if not system_module_instance:
                return
            if not hasattr(system_module_instance, "init_module"):
                return
            system_module_instance.init_module()
            logger.info(f"系统模块实例初始化成功: comp_name = {self.comp_name}, module_id = {module_id}")
        except Exception as e:
            logger.error(f"系统模块实例初始化异常: comp_name = {self.comp_name}, module_id = {module_id}, {str(e)}", exc_info=True)

    def mark_need_reload_system_modules(self):
        """
        标记需要重载系统模块
        """
        try:
            ThreadLocalUtil.set("need_reload_system_modules", True)
        except Exception:
            pass

    @abstractmethod
    def apply_config(self, config: dict):
        """
        应用配置（使系统配置生效）
        """
        pass
