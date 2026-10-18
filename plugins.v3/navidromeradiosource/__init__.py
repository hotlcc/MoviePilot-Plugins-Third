import asyncio
from datetime import datetime, timedelta
from threading import RLock, Event as ThreadEvent
from typing import Any, List, Dict, Tuple, Type, Optional, OrderedDict

import pytz
from app.foundation.reflection import ModuleHelper
from app.schemas.system import MediaServerConf
from app.schemas.types import MediaServerType
from app.sdk.config import settings
from app.sdk.logging import logger
# noinspection PyProtectedMember
from app.sdk.plugin.base import _PluginBase
from app.sdk.services import MediaServerHelper
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .model import Radio
from .navidrome_client import NavidromeClient
from .source import BaseSource


# noinspection SpellCheckingInspection,DuplicatedCode,PyShadowingNames
class NavidromeRadioSource(_PluginBase):
    # 插件名称
    plugin_name = "Navidrome电台源"
    # 插件描述
    plugin_desc = "自动同步公开电台到Navidrome。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/hotlcc/MoviePilot-Plugins-Third/main/icons/NavidromeRadioSource.png"
    # 插件版本
    plugin_version = "3.0.12"
    # 插件作者
    plugin_author = "hotlcc"
    # 作者主页
    author_url = "https://github.com/hotlcc"
    # 插件配置项ID前缀
    plugin_config_prefix = "com.hotlcc.navidromeradiosource."
    # 加载顺序
    plugin_order = 66
    # 可使用的用户级别
    auth_level = 1

    # 类公共属性
    # 系统组件
    # 媒体服务器
    __media_server_helper = MediaServerHelper()
    # 插件缺省配置
    __config_default: Dict[str, Any] = {
        "cron": "0 3 * * *"
    }

    # 对象私有属性
    # 插件用户配置
    __config: Optional[Dict[str, Any]] = None
    # 注册组件对象
    __comp_objs: Optional[OrderedDict[str, BaseSource]] = None
    # 调度器
    __scheduler: Optional[BackgroundScheduler] = None
    # 任务锁
    __task_lock: Optional[RLock] = None
    # 退出事件
    __exit_event: Optional[ThreadEvent] = None

    def __init__(self):
        super().__init__()
        # 对象私有属性
        self.__comp_objs = OrderedDict[str, BaseSource]()
        self.__task_lock = RLock()
        self.__exit_event = ThreadEvent()

    def init_plugin(self, config: dict = None):
        """
        生效配置信息
        :param config: 配置信息字典
        """
        # 对象私有属性
        self.__config = config or {}
        self.__init_scheduler()
        # 注册组件
        self.__register_comp()
        # 修正配置
        self.__config = self.__fix_config(config=config)
        # 检查配置
        check_config = self.__check_config()
        # 处理运行一次
        if check_config:
            self.__run_once()

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
        navidrome_configs = self.__get_navidrome_configs() or []
        # 建议的配置
        config_suggest = {
            "navidrome_server": navidrome_configs[0].name if navidrome_configs else None,
            "enable_sources": list(self.__comp_objs.keys()),
        }
        # 合并默认配置
        config_suggest.update(self.__config_default)
        # 元素
        elements = [{
            'component': 'VForm',
            'content': [{
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
                }, {
                    'component': 'VCol',
                    'props': {
                        'cols': 12,
                        'xxl': 8, 'xl': 8, 'lg': 8, 'md': 8, 'sm': 6, 'xs': 12
                    },
                    'content': [{
                        'component': 'VSwitch',
                        'props': {
                            'model': 'run_once',
                            'label': '立即运行一次',
                            'hint': '保存插件配置后是否立即触发一次插件任务运行'
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
                            'model': 'navidrome_server',
                            'label': 'Navidrome服务器',
                            'multiple': False,
                            'chips': True,
                            'items': [{
                                'title': config.name,
                                'value': config.name,
                            } for config in navidrome_configs if config],
                            'hint': '选择Navidrome服务器。必选。'
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
                            'model': 'navidrome_username',
                            'label': 'Navidrome用户',
                            'placeholder': "",
                            'hint': "Navidrome用户。缺省时取Navidrome服务器配置的用户，必须确保是管理员用户。"
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
                            'model': 'navidrome_password',
                            'type': 'password',
                            'label': 'Navidrome密码',
                            'placeholder': "",
                            'hint': "Navidrome密码。"
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
                            'model': 'cron',
                            'label': '定时周期',
                            'placeholder': self.__config_default.get("cron"),
                            'hint': f'设置插件任务执行周期。支持5位cron表达式，缺省时为：{self.__config_default.get("cron")}。'
                        }
                    }]
                }, {
                    'component': 'VCol',
                    'props': {
                        'cols': 12,
                        'xxl': 8, 'xl': 8, 'lg': 8, 'md': 8, 'sm': 12, 'xs': 12
                    },
                    'content': [{
                        'component': 'VSelect',
                        'props': {
                            'model': 'enable_sources',
                            'label': '启用的电台源',
                            'multiple': True,
                            'chips': True,
                            'items': [{
                                'title': comp_obj.comp_name,
                                'value': key,
                            } for key, comp_obj in self.__comp_objs.items() if key and comp_obj],
                            'hint': '选择要启用的电台源。必选。'
                        }
                    }]
                }]
            }]
        }]
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
        try:
            cron = self.__get_config_item(config_key='cron')
            if self.get_state() and cron:
                return [{
                    "id": f"{self.__class__.__name__}TimerService",
                    "name": f"{self.plugin_name}定时服务",
                    "trigger": CronTrigger.from_crontab(cron),
                    "func": self.__try_run,
                    "kwargs": {}
                }]
        except Exception as e:
            logger.error(f"注册插件公共服务异常: {str(e)}", exc_info=True)
        return []

    def stop_service(self):
        """
        停止插件
        """
        try:
            logger.info('尝试停止插件服务...')
            self.__exit_event.set()
            self.__stop_scheduler()
            self.__gc()
            logger.info('插件服务停止完成')
        except Exception as e:
            logger.error(f"插件服务停止异常: {str(e)}", exc_info=True)

    @classmethod
    def __fix_config(cls, config: dict) -> Optional[dict]:
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

    def __check_config(self, config: dict = None) -> bool:
        config = config or self.__config or {}
        result = True
        if not config.get("navidrome_server"):
            logger.error("配置检查不通过：Navidrome服务器")
            result = False
        if config.get("navidrome_username") and not config.get("navidrome_password"):
            logger.error("配置检查不通过：配置Navidrome用户时必须配置对应的密码")
            result = False
        if not config.get("enable_sources"):
            logger.error("配置检查不通过：Navidrome服务器")
            result = False
        return result

    @classmethod
    def __check_comp_type(cls, comp_type: type) -> bool:
        """
        检查组件类
        """
        if not comp_type:
            return False
        return issubclass(comp_type, BaseSource) and comp_type is not BaseSource

    @classmethod
    def __extract_comp_key(cls, comp_type: type) -> Optional[str]:
        """
        提取组件key
        """
        if not comp_type:
            return None
        return comp_type.__name__.removesuffix(BaseSource.__name__).lower()

    def __run_once(self):
        """
        执行立即运行一次
        """
        if not self.__get_config_item(config_key='run_once'):
            return
        try:
            self.__async_try_run()
            logger.info(f"立即运行一次成功")
        finally:
            # 关闭一次性开关
            self.__config['run_once'] = False
            self.update_config(self.__config)

    def __register_comp(self):
        """
        注册组件
        """
        # 加载所有组件类
        comp_types: List[Type[BaseSource]] = ModuleHelper.load(
            package_path="app.plugins.navidromeradiosource.source",
            filter_func=lambda _, obj: self.__check_comp_type(comp_type=obj)
        )
        # 数量
        comp_count = len(comp_types) if comp_types else 0
        logger.info(f"总共加载到{comp_count}个电台源组件")
        if not comp_types:
            return
        # 组件key缺省值处理
        for comp_type in comp_types:
            if not comp_type or comp_type.comp_key:
                continue
            comp_type.comp_key = self.__extract_comp_key(comp_type=comp_type)
        # 组件排序，顺序一样时按照key排序
        comp_types = sorted(comp_types, key=lambda comp_type: (comp_type.comp_order, comp_type.comp_key))
        # 依次实例化并注册
        for comp_type in comp_types:
            comp_name = comp_type.comp_name
            try:
                comp_key = comp_type.comp_key
                comp_obj = self.__comp_objs.get(comp_key)
                if comp_obj:
                    continue
                comp_obj = comp_type()
                self.__comp_objs[comp_key] = comp_obj
                logger.info(f"注册电台源组件 - {comp_name} - 成功")
            except Exception as e:
                logger.error(f"注册电台源组件 - {comp_name} - 异常: {str(e)}", exc_info=True)

    def __init_scheduler(self, timezone=None):
        """
        初始化调度器
        :param timezone: 时区
        """
        try:
            if not timezone:
                timezone = settings.TZ
            self.__scheduler = scheduler = BackgroundScheduler(timezone=timezone)
            logger.debug(f"插件服务调度器初始化完成: timezone = {str(timezone)}")
            if not scheduler.running:
                scheduler.start()
                logger.debug(f"插件服务调度器启动成功")
                scheduler.print_jobs()
        except Exception as e:
            logger.error(f"插件服务调度器启动异常: {str(e)}", exc_info=True)

    def __stop_scheduler(self):
        """
        停止调度器
        """
        try:
            logger.info('尝试停止插件服务调度器...')
            scheduler: BackgroundScheduler = self.__scheduler
            if scheduler:
                scheduler.remove_all_jobs()
                if scheduler.running:
                    scheduler.shutdown()
                logger.info('插件服务调度器停止成功')
            else:
                logger.info('插件未启用服务调度器，无须停止')
        except Exception as e:
            logger.error(f"插件服务调度器停止异常: {str(e)}", exc_info=True)

    def __gc(self):
        """
        回收内存
        """
        try:
            logger.info('尝试回收内存...')
            if self.__comp_objs:
                self.__comp_objs.clear()
                self.__comp_objs = None
            if self.__task_lock:
                self.__task_lock = None
            if self.__exit_event:
                self.__exit_event = None
            logger.info('回收内存成功')
        except Exception as e:
            logger.error(f"回收内存异常: {str(e)}", exc_info=True)

    def __try_run(self):
        """
        尝试运行插件任务
        """
        if self.__exit_event.is_set():
            logger.warn(f"运行任务中止: 插件正在退出")
            return
        if not self.__task_lock.acquire(blocking=False):
            logger.info('已有进行中的任务，本次不执行')
            return
        try:
            if self.__exit_event.is_set():
                logger.warn(f"运行任务中止: 插件正在退出")
                return
            self.__run()
        finally:
            self.__task_lock.release()

    def __async_try_run(self):
        """
        异步Try运行
        """
        def __do_task():
            self.__try_run()

        scheduler: BackgroundScheduler = self.__scheduler
        scheduler.add_job(func=__do_task,
                          trigger='date',
                          run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                          name='异步Try运行')

    def __block_run(self):
        """
        阻塞运行插件任务
        """
        if self.__exit_event.is_set():
            logger.warn(f"运行任务中止: 插件正在退出")
            return
        self.__task_lock.acquire()
        try:
            if self.__exit_event.is_set():
                logger.warn(f"运行任务中止: 插件正在退出")
                return
            self.__run()
        finally:
            self.__task_lock.release()

    def __async_block_run(self):
        """
        异步阻塞运行
        """
        def __do_task():
            self.__block_run()

        scheduler: BackgroundScheduler = self.__scheduler
        scheduler.add_job(func=__do_task,
                          trigger='date',
                          run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                          name='异步阻塞运行')

    def __run(self):
        """
        运行任务
        """
        navidrome_server_info = self.__get_navidrome_server_info() or {}
        if not navidrome_server_info:
            return
        navidrome_client = NavidromeClient(
            base_url=navidrome_server_info.get("host"),
            username=navidrome_server_info.get("username"),
            password=navidrome_server_info.get("password"),
        )
        logger.info("刷新电台信息 - 开始")
        try:
            asyncio.run(self.__refresh_radios(navidrome_client=navidrome_client))
        finally:
            logger.info("刷新电台信息 - 完成")

    def __get_navidrome_configs(self) -> Optional[List[MediaServerConf]]:
        config_map = self.__media_server_helper.get_configs(include_disabled=True) or {}
        if not config_map:
            return None
        type_str = MediaServerType.Navidrome.name.lower()
        configs = list(config_map.values()) or []
        return [config for config in configs if config and config.type == type_str]

    def __get_navidrome_config(self, name: str) -> Optional[MediaServerConf]:
        return self.__media_server_helper.get_config(name=name)

    def __get_navidrome_server_info(self) -> Optional[Dict[str, str]]:
        navidrome_server = self.__get_config_item(config_key="navidrome_server")
        if not navidrome_server:
            return None
        navidrome_config = self.__get_navidrome_config(name=navidrome_server)
        if not navidrome_config or not navidrome_config.config:
            logger.warn("选择的Navidrome服务器配置无效")
            return None

        host = navidrome_config.config.get("host")
        username = navidrome_config.config.get("username")
        password = navidrome_config.config.get("password")
        if not host or not username or not password:
            logger.warn("选择的Navidrome服务器配置无效")
            return None

        navidrome_username = self.__get_config_item(config_key="navidrome_username")
        navidrome_password = self.__get_config_item(config_key="navidrome_password")

        return {
            "host": host,
            "username": navidrome_username if navidrome_username else username,
            "password": navidrome_password if navidrome_username else password,
        }

    async def __get_radios(self) -> Optional[List[Radio]]:
        """
        获取电台信息
        """
        enable_sources = self.__get_config_item(config_key="enable_sources") or []
        if not enable_sources:
            logger.warn("请至少选择一个电台源")
            return None
        result: List[Radio] = []
        for enable_source in enable_sources:
            if not enable_source:
                continue
            comp_obj: BaseSource = self.__comp_objs.get(enable_source)
            if not comp_obj:
                continue
            try:
                radios = await comp_obj.get_radios()
            except Exception as e:
                radios = []
                logger.error(f"单个电台源获取电台失败: comp_name = {comp_obj.comp_name}, error = {str(e)}")
            result.extend(radios)
        return result

    async def __refresh_radios(self, navidrome_client: NavidromeClient) -> None:
        if not navidrome_client:
            raise ValueError("参数错误[navidrome_client]")
        if not navidrome_client.is_admin():
            raise ValueError("请配置Navidrome管理员用户")

        # 查询已经存在的全部电台
        exist_list = navidrome_client.radio().list() or []
        exist_name_info_map = {radio.get("name"): radio for radio in exist_list if radio}
        # 第三方电台信息
        radio_infos: List[Radio] = await self.__get_radios() or []
        radio_names = [radio_info.name for radio_info in radio_infos if radio_info and radio_info.name]

        update_count = 0
        add_count = 0
        delete_count = 0
        # 更新、添加
        for radio_info in radio_infos:
            exist_info = exist_name_info_map.get(radio_info.name)
            if not exist_info:
                navidrome_client.radio().add(name=radio_info.name, stream_url=radio_info.stream_url, home_page_url=radio_info.home_page_url)
                add_count += 1
                logger.debug(f"刷新电台 - 添加电台完成: name = {radio_info.name}")
            elif radio_info.stream_url != exist_info.get("streamUrl") or radio_info.home_page_url != exist_info.get("homePageUrl"):
                navidrome_client.radio().update(id=exist_info.get("id"), name=radio_info.name, stream_url=radio_info.stream_url, home_page_url=radio_info.home_page_url)
                update_count += 1
                logger.debug(f"刷新电台 - 更新电台完成: name = {radio_info.name}")
        # 删除无效的
        for radio in exist_list:
            if not radio:
                continue
            id = radio.get("id")
            if not id:
                continue
            name = radio.get("name")
            if not name:
                navidrome_client.radio().delete(id=id)
                delete_count += 1
                logger.debug(f"刷新电台 - 删除电台完成: id = {id}")
            elif name not in radio_names:
                navidrome_client.radio().delete(id=id)
                delete_count += 1
                logger.debug(f"刷新电台 - 删除电台完成: name = {name}")
        logger.info(f"刷新电台 - 成功: 更新数量 = {update_count}, 添加数量 = {add_count}, 删除数量 = {delete_count}")
