from abc import abstractmethod, ABC
from typing import Dict, Any, Tuple, List
import inspect
import os

from app.plugins import _PluginBase
from app.schemas.types import NotificationType


class Channel(ABC):
    """
    消息通知渠道基类
    """

    # 组件key
    comp_key: str = ""
    # 组件名称
    comp_name: str = ""
    # 组件顺序
    comp_order: int = 0

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {}

    def __init__(self, plugin: _PluginBase):
        """
        :param plugin: 插件对象
        """
        if not plugin:
            raise Exception("组件实例化错误")
        self.__plugin = plugin

    def get_config(self) -> dict:
        """
        获取组件配置
        """
        get_comp_config = getattr(self.__plugin, "get_comp_config")
        if not get_comp_config:
            raise Exception("插件方法不存在[get_comp_config]")
        comp_config = get_comp_config(comp_key=self.comp_key)
        return comp_config

    def update_config(self, config: dict) -> bool:
        """"
        更新组件配置
        """
        update_comp_config = getattr(self.__plugin, "update_comp_config")
        if not update_comp_config:
            raise Exception("插件方法不存在[update_comp_config]")
        return update_comp_config(comp_key=self.comp_key, comp_config=config)

    def get_config_item(self, config_key: str, use_default: bool = True) -> Any:
        """
        获取组件配置项
        :param config_key: 配置键
        :param use_default: 是否使用缺省值
        :return: 配置值
        """
        if not config_key:
            return None
        config = self.get_config() or {}
        config_default = self.config_default or {}
        config_value = config.get(config_key)
        if config_value is None and use_default:
            config_value = config_default.get(config_key)
        return config_value

    def __build_notify_type_select_element(self) -> dict:
        """
        构造消息类型下拉选择元素
        """
        select_items = [{
            "title": type.value,
            "value": type.name
        } for type in NotificationType if type]
        return {
            'component': 'VSelect',
            'props': {
                'model': 'enable_notify_types',
                'label': '消息类型',
                'multiple': True,
                'chips': True,
                'clearable': True,
                'items': select_items,
                'hint': '选择哪些类型的消息需要通过此渠道发送，缺省时不限制类型。'
            }
        }

    def __build_notify_type_select_col_element(self) -> dict:
        """
        构造消息类型下拉选择Col元素
        """
        return {
            'component': 'VCol',
            'props': {
                'cols': 12,
                'xxl': 12, 'xl': 12, 'lg': 12, 'md': 12, 'sm': 12, 'xs': 12
            },
            'content': [self.__build_notify_type_select_element()]
        }

    def build_notify_type_select_row_element(self) -> dict:
        """
        构造消息类型下拉选择行元素
        """
        return {
            'component': 'VRow',
            'content': [self.__build_notify_type_select_col_element()]
        }

    def check_stack_contain_method(self, package_name: str, function_name: str) -> bool:
        """
        判断调用栈是否包含指定的方法
        """
        if not package_name or not function_name:
            return False
        package_path = package_name.replace('.', os.sep)
        for stack in inspect.stack():
            if not stack or not stack.filename:
                continue
            if stack.function != function_name:
                continue
            if stack.filename.endswith(f"{package_path}.py") or stack.filename.endswith(f"{package_path}{os.sep}__init__.py"):
                return True
        return False

    def check_stack_contain_save_config_request(self) -> bool:
        """
        判断调用栈是否包含“插件配置保存”接口
        """
        return self.check_stack_contain_method('app.api.endpoints.plugin', 'set_plugin_config')

    def save_default_config(self):
        """
        （缺省时）保存默认配置到组件配置中
        """
        config_default = self.config_default or {}
        if not config_default:
            return
        config = self.get_config() or {}
        config_copy = config.copy()
        for key, value in config_default.items():
            if not key or key in config_copy.keys():
                continue
            config_copy[key] = value
        if config_copy != config:
            self.update_config(config=config_copy)

    @abstractmethod
    def init_comp(self):
        """
        初始化组件
        """
        pass

    @abstractmethod
    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        获取组件的配置表单
        :return: 配置表单, 建议的配置
        """
        pass

    @abstractmethod
    def send_message(self, title: str, text: str, type: NotificationType = None, ext_info: dict = {}):
        """
        发送消息
        """
        pass
