from typing import OrderedDict, Dict, Any, List, Tuple, Type

from app.core.event import eventmanager, Event
from app.helper.module import ModuleHelper
from app.log import logger
from app.plugins import _PluginBase
from app.plugins.mergemessagenotify.channel import Channel
from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.plugins.mergemessagenotify.module import ChannelStrategy
from app.schemas.types import EventType, NotificationType


class MergeMessageNotify(_PluginBase):
    # 插件名称
    plugin_name = "聚合消息通知"
    # 插件描述
    plugin_desc = "消息通知，一个插件就够了。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/hotlcc/MoviePilot-Plugins-Third/main/icons/MergeMessageNotify_121.png"
    # 插件版本
    plugin_version = "1.17"
    # 插件作者
    plugin_author = "hotlcc"
    # 作者主页
    author_url = "https://github.com/hotlcc"
    # 插件配置项ID前缀
    plugin_config_prefix = "com.hotlcc.mergemessagenotify."
    # 加载顺序
    plugin_order = 66
    # 可使用的用户级别
    auth_level = 1

    # 注册组件
    # 注册组件对象
    __comp_objs: OrderedDict[str, Channel] = OrderedDict()

    # 配置相关
    # 插件缺省配置
    __config_default: Dict[str, Any] = {
        "channel_strategy": "ALL_SELECTED"
    }
    # 插件用户配置
    __config: Dict[str, Any] = {}

    def init_plugin(self, config: dict = None):
        """
        生效配置信息
        :param config: 配置信息字典
        """
        # 加载插件配置
        self.__config = config
        # 修正配置
        config = self.__fix_config(config=config)
        # 重新加载插件配置
        self.__config = config
        # 注册组件
        self.__register_comp()

    def get_state(self) -> bool:
        """
        获取插件运行状态
        """
        return True if self.__get_config_item("enable") else False

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """
        注册插件远程命令
        [{
            "cmd": "/xx",
            "event": EventType.xx,
            "desc": "名称",
            "category": "分类，需要注册到Wechat时必须有分类",
            "data": {}
        }]
        """
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """
        注册插件API
        [{
            "path": "/xx",
            "endpoint": self.xxx,
            "methods": ["GET", "POST"],
            "summary": "API名称",
            "description": "API说明"
        }]
        """
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        插件配置页面使用Vuetify组件拼装，参考：https://vuetifyjs.com/
        """
        # 建议的配置
        config_suggest = {}
        # 合并默认配置
        config_suggest.update(self.__config_default)
        # 合并组件的表单建议配置
        for _, comp_obj in self.__comp_objs.items():
            comp_form_data = self.__get_comp_form_data(comp_obj=comp_obj)
            if comp_form_data:
                config_suggest.update(comp_form_data)
        # 通知渠道下拉数据
        channel_select_items = [{
            "title": comp_obj.comp_name,
            "value": comp_obj.comp_key
        } for _, comp_obj in self.__comp_objs.items() if comp_obj and comp_obj.comp_key and comp_obj.comp_name]
        # 头部元素
        channel_strategy_hint_desc = "；".join([item.name_ + "-" + item.desc for item in ChannelStrategy])
        header_elements = [{
            'component': 'VRow',
            'content': [{
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSwitch',
                    'props': {
                        'model': 'enable',
                        'label': '启用插件',
                        'hint': '插件总开关'
                    }
                }]
            }]
        }, {
            'component': 'VRow',
            'content': [{
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 8, 'xl': 8, 'lg': 8, 'md': 8, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSelect',
                    'props': {
                        'model': 'enable_channels',
                        'label': '当前使用通知渠道',
                        'multiple': True,
                        'chips': True,
                        'clearable': True,
                        'items': channel_select_items,
                        'hint': '选填。只有选择的渠道才会发送消息。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSelect',
                    'props': {
                        'model': 'channel_strategy',
                        'label': '渠道策略',
                        'items': [{
                            'title': item.name_,
                            'value': item.name
                        } for item in ChannelStrategy],
                        'hint': f'选填。【当前使用通知渠道】选择的渠道以何种策略运行：{channel_strategy_hint_desc}。缺省时为“{ChannelStrategy.ALL_SELECTED.name_}”。'
                    }
                }]
            }]
        }]
        # 尾部元素
        foot_elements = []
        # 组件的元素
        comp_elements = [self.__build_comp_form_element()]
        # 元素
        elements = [{
            'component': 'VForm',
            'content': header_elements + comp_elements + foot_elements
        }]
        # 处理缺省配置
        self.__save_default_config()
        return elements, config_suggest

    def get_page(self) -> List[dict]:
        """
        拼装插件详情页面，需要返回页面配置，同时附带数据
        插件详情页面使用Vuetify组件拼装，参考：https://vuetifyjs.com/
        """
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        [{
            "id": "服务ID",
            "name": "服务名称",
            "trigger": "触发器：cron/interval/date/CronTrigger.from_crontab()",
            "func": self.xxx,
            "kwargs": {} # 定时器参数
        }]
        """
        pass

    def stop_service(self):
        """
        停止插件
        """
        try:
            logger.info('尝试停止插件服务...')
            self.__gc()
            logger.info('插件服务停止完成')
        except Exception as e:
            logger.error(f"插件服务停止异常: {str(e)}", exc_info=True)

    def __fix_config(self, config: dict) -> dict:
        """
        修正配置
        """
        if not config:
            return None
        # 忽略主程序在reset时赋予的内容
        reset_config = {
            "enabled": False,
            "enable": False
        }
        if config == reset_config:
            return None
        # 修正内容
        config_copy = config.copy()
        # 移除无效的key
        #config_copy.pop("_tabs", None)
        #config_copy.pop("undefined", None)
        # 保存更新
        if config != config_copy:
            self.update_config(config=config_copy)
        return config_copy

    def __get_config_item(self, config_key: str, use_default: bool = True) -> Any:
        """
        获取插件配置项
        :param config_key: 配置键
        :param use_default: 是否使用缺省值
        :return: 配置值
        """
        if not config_key:
            return None
        config = self.__config or {}
        config_default = self.__config_default or {}
        config_value = config.get(config_key)
        if config_value is None and use_default:
            config_value = config_default.get(config_key)
        return config_value

    def get_comp_config(self, comp_key: str) -> Dict[str, Any]:
        """
        获取组件配置
        """
        comp_config = {}
        if not comp_key:
            return comp_config
        if not self.__config:
            return comp_config
        key_prefix = f"{comp_key}."
        for key, value in self.__config.items():
            if not key or not key.startswith(key_prefix):
                continue
            comp_config_key = key.removeprefix(key_prefix)
            comp_config[comp_config_key] = value
        return comp_config

    def update_comp_config(self, comp_key: str, comp_config: dict) -> bool:
        """"
        更新组件配置
        """
        if not comp_key:
            return False
        config = self.__config or {}
        if not config and not comp_config:
            return False
        key_prefix = f"{comp_key}."
        config = dict(filter(lambda item: item and not item[0].startswith(key_prefix), config.items()))
        if comp_config:
            for comp_config_key, value in comp_config.items():
                if not comp_config_key:
                    continue
                key = key_prefix + comp_config_key
                config[key] = value
        result = self.update_config(config=config)
        self.__config = config
        return result

    def __filter_comp_type(self, comp_type: type) -> bool:
        """
        过滤组件类
        """
        if not comp_type:
            return False
        return issubclass(comp_type, Channel) \
           and comp_type.__name__ != Channel.__name__ \
           and comp_type.__name__ != CustomChannel.__name__

    def __register_comp(self):
        """
        注册组件
        """
        # 加载所有组件类
        comp_types: List[Type[Channel]] = ModuleHelper.load(
            package_path="app.plugins.mergemessagenotify.channel",
            filter_func=lambda _, obj: self.__filter_comp_type(comp_type=obj)
        ) + ModuleHelper.load(
            package_path="app.plugins.mergemessagenotify.channel.custom",
            filter_func=lambda _, obj: self.__filter_comp_type(comp_type=obj)
        )
        # 去重
        comp_types = list(set(comp_types))
        # 数量
        comp_count = len(comp_types) if comp_types else 0
        logger.info(f"总共加载到{comp_count}个组件")
        if not comp_types:
            return
        # 组件排序，顺序一样时按照key排序
        comp_types = sorted(comp_types, key=lambda comp_type: (comp_type.comp_order, comp_type.comp_key))
        # 依次实例化并注册
        for comp_type in comp_types:
            #comp_name = comp_type.comp_name
            try:
                comp_key = comp_type.comp_key
                comp_obj = self.__comp_objs.pop(key=comp_key, default=None)
                if not comp_obj:
                    # 实例化组件
                    comp_obj = comp_type(plugin=self)
                # 初始化组件
                comp_obj.init_comp()
                # 注册组件
                self.__comp_objs[comp_key] = comp_obj
                logger.info(f"注册组件 - {comp_type.__name__} - 成功")
            except Exception as e:
                logger.error(f"注册组件 - {comp_type.__name__} - 异常: {str(e)}", exc_info=True)

    def __wrapper_comp_form_model(self, comp_key: str, model: str) -> str:
        """
        包装组件表单model
        """
        if not comp_key or not model:
            return None
        return f"{comp_key}.{model}"

    def __get_comp_form_data(self, comp_obj: Channel) -> Dict[str, Any]:
        """
        获取组件的表单数据
        """
        if not comp_obj:
            return None
        form = comp_obj.get_form()
        if not form:
            return None
        _, data = form
        if not data:
            return {}
        result = {}
        comp_key = comp_obj.comp_key
        for key, value in data.items():
            if not key or not value:
                continue
            key = self.__wrapper_comp_form_model(comp_key=comp_key, model=key)
            result[key] = value
        return result

    def __build_comp_form_element(self) -> dict:
        """
        构建组件表单元素
        """
        return {
            'component': 'VRow',
            'content': [{
                'component': 'VCol',
                'props': {
                    'cols': 12
                },
                'content': [
                    self.__build_comp_form_tabs_element(),
                    self.__build_comp_form_window_element(),
                ]
            }]
        }

    def __build_comp_form_tab_value(self, key: str) -> str:
        """
        构造组件表单tab的value
        :param key: 组件的key
        """
        return f'_tab.{key}'

    def __build_comp_form_tabs_element(self) -> dict:
        """
        构建组件表单tabs元素
        """
        return {
            'component': 'VTabs',
            'props': {
                'model': '_tabs',
                'height': 72,
                'style': {
                    'margin-top-': '20px',
                    'margin-bottom-': '20px',
                }
            },
            'content': [{
                'component': 'VTab',
                'props': {
                    'value': self.__build_comp_form_tab_value(key=key)
                },
                'text': obj.comp_name
            } for key, obj in self.__comp_objs.items() if key and obj]
        }

    def __build_comp_form_window_element(self) -> dict:
        """
        构建组件表单window元素
        """
        return {
            'component': 'VWindow',
            'props': {
                'model': '_tabs',
            },
            'content': [{
                'component': 'VWindowItem',
                'props': {
                    'style': {
                        'margin-top': '20px',
                    },
                    'value': self.__build_comp_form_tab_value(key=key)
                },
                'content': self.__get_comp_form_elements(comp_obj=obj)
            } for key, obj in self.__comp_objs.items() if key and obj]
        }

    def __get_comp_form_elements(self, comp_obj: Channel) -> List[dict]:
        """
        获取组件的表单元素
        """
        if not comp_obj:
            return None
        form = comp_obj.get_form()
        if not form:
            return None
        elements, _ = form
        comp_key = comp_obj.comp_key
        self.__wrapper_comp_form_elements(comp_key=comp_key, comp_elements=elements)
        return elements

    def __wrapper_comp_form_elements(self, comp_key: str, comp_elements: List[dict]):
        """
        包装组件的表单元素
        """
        if not comp_key or not comp_elements:
            return
        for comp_element in comp_elements:
            if not comp_element:
                continue
            # 处理自身
            props = comp_element.get("props")
            if props:
                model = props.get("model")
                if model:
                    props["model"] = self.__wrapper_comp_form_model(comp_key=comp_key, model=model)
            # 递归处理下级
            content = comp_element.get("content")
            if content:
                self.__wrapper_comp_form_elements(comp_key=comp_key, comp_elements=content)

    def __gc(self):
        """
        回收内存
        """
        try:
            logger.info('尝试回收内存...')
            if self.__comp_objs:
                self.__comp_objs.clear()
            logger.info('回收内存成功')
        except Exception as e:
            logger.error(f"回收内存异常: {str(e)}", exc_info=True)

    def __save_default_config(self):
        """
        （缺省时）保存默认配置到组件配置中
        """
        config_default = self.__config_default or {}
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

    @eventmanager.register(EventType.NoticeMessage)
    def listen_notice_message_event(self, event: Event = None):
        """
        监听发送消息通知事件
        """
        if not self.get_state():
            return
        if not event or not event.event_data:
            return
        try:
            logger.info('监听到发送消息通知事件')
            enable_channels: List[str] = self.__get_config_item("enable_channels") or []
            if not enable_channels:
                logger.warn('发送消息通知事件监听任务执行中止: 没有启用任何渠道')
                return
            message_info = event.event_data
            if message_info.get("channel"):
                logger.warn('发送消息通知事件监听任务执行中止: 忽略系统渠道的消息')
                return
            title: str = message_info.get("title")
            text: str = message_info.get("text")
            if not title and not text:
                logger.warn('发送消息通知事件监听任务执行中止: 标题和内容不允许同时为空')
                return
            # 消息类型在MPv1中是type，在MPv2中是mtype
            type: NotificationType = message_info.get("type") or message_info.get("mtype")
            # 渠道策略
            channel_strategy = self.__get_config_item(config_key="channel_strategy")
            is_order_success_one: bool = (ChannelStrategy.ORDER_SUCCESS_ONE.name == channel_strategy)
            # 成功失败数
            success_count = 0
            fail_count = 0
            for enable_channel in enable_channels:
                # 处理【顺序优先，成功即止】策略
                if is_order_success_one and success_count > 0:
                    break
                if not enable_channel:
                    continue
                comp_key = enable_channel
                comp_obj = self.__comp_objs.get(comp_key)
                if not comp_obj:
                    continue
                try:
                    success = comp_obj.send_message(title=title, text=text, type=type, ext_info=message_info)
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                    logger.info(f"消息发送执行完成: 渠道 = {comp_obj.comp_name} success = {success}")
                except Exception as e:
                    fail_count += 1
                    logger.error(f"消息发送执行异常: 渠道 = {comp_obj.comp_name}", exc_info=True)
            logger.info(f'发送消息通知事件监听任务执行成功: 成功渠道数 = {success_count}, 失败渠道数 = {fail_count}')
        except Exception as e:
            logger.error(f'发送消息通知事件监听任务执行异常: {str(e)}', exc_info=True)
