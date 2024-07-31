from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from threading import RLock, Event as ThreadEvent
from typing import Any, List, Dict, Tuple, OrderedDict, Type, Optional, Union
from datetime import datetime, timedelta
import pytz
from cachetools import TTLCache

from app.core.config import settings
from app.core.context import MediaInfo
from app.core.event import eventmanager, Event
from app.db.models.mediaserver import MediaServerItem
from app.db.models.subscribe import Subscribe
from app.db.models.subscribehistory import SubscribeHistory
from app.db.subscribe_oper import SubscribeOper
from app.helper.module import ModuleHelper
from app.log import logger
from app.plugins import _PluginBase
from app.plugins.mediacollecthelper.favorites import Favorites
from app.plugins.mediacollecthelper.module import MediaDataSource, MediaDigest, AtomicCache
from app.schemas.types import MediaType, EventType, NotificationType


class MediaCollectHelper(_PluginBase):
    # 插件名称
    plugin_name = "影视收藏助手"
    # 插件描述
    plugin_desc = "自动收藏MP中的影视信息到其它介质。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/hotlcc/MoviePilot-Plugins-Third/main/icons/Favorites_A.png"
    # 插件版本
    plugin_version = "1.9"
    # 插件作者
    plugin_author = "hotlcc"
    # 作者主页
    author_url = "https://github.com/hotlcc"
    # 插件配置项ID前缀
    plugin_config_prefix = "com.hotlcc.mediacollecthelper."
    # 加载顺序
    plugin_order = 66
    # 可使用的用户级别
    auth_level = 1

    # 注册组件
    # 注册组件对象
    __comp_objs: OrderedDict[str, Favorites] = OrderedDict()

    # 私有属性
    # 调度器
    __scheduler: Optional[BackgroundScheduler] = None
    # 任务锁
    __task_lock: RLock = RLock()
    # 退出事件
    __exit_event: ThreadEvent = ThreadEvent()
    # 订阅数据操作
    __subscribe_oper: SubscribeOper = SubscribeOper()
    # 原子缓存操作，用于处理短期内事件媒体相同的清空去重
    __atomic_cache: AtomicCache = AtomicCache(cache=TTLCache(maxsize=1000, ttl=60 * 5))

    # 配置相关
    # 插件缺省配置
    __config_default: Dict[str, Any] = {
        "cron": "0 3 * * *"
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
        # 注册收藏夹组件
        self.__register_comp()
        # 修正配置
        config = self.__fix_config(config=config)
        # 重新加载插件配置
        self.__config = config
        # 处理运行一次
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
        # 建议的配置
        config_suggest = {
            "enable_favorites": ["linkding"],
            # 全部影视数据来源
            "media_data_sources": [mds.name for mds in MediaDataSource if mds],
            # 全部影视类型
            "collect_media_types": [mt.name for mt in MediaType if mt],
        }
        # 合并默认配置
        config_suggest.update(self.__config_default)
        # 合并组件的默认配置
        for _, comp_obj in self.__comp_objs.items():
            comp_form_data = self.__get_comp_form_data(comp_obj=comp_obj)
            if comp_form_data:
                config_suggest.update(comp_form_data)
        # 头部元素
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
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSwitch',
                    'props': {
                        'model': 'enable_notify',
                        'label': '发送通知',
                        'hint': '执行插件任务后是否发送通知'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSwitch',
                    'props': {
                        'model': 'run_once',
                        'label': '立即运行一次',
                        'hint': '保存插件配置后是否立即触发一次插件任务运行'
                    }
                }]
            }]
        }, {
            'component': 'VRow',
            'content': [{
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSelect',
                    'props': {
                        'model': 'enable_favorites',
                        'label': '启用的收藏夹',
                        'multiple': True,
                        'items': [{
                            'title': comp_obj.comp_name,
                            'value': key,
                        } for key, comp_obj in self.__comp_objs.items() if key and comp_obj],
                        'hint': '选择要启用的收藏夹，目前只支持Linkding。'
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
                        'model': 'media_data_sources',
                        'label': '影视数据来源',
                        'multiple': True,
                        'items': [{
                            'title': mds.value,
                            'value': mds.name,
                        } for mds in MediaDataSource if mds],
                        'hint': '选择影视数据来源。'
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
                        'model': 'collect_media_types',
                        'label': '收藏的影视类型',
                        'multiple': True,
                        'items': [{
                            'title': mt.value,
                            'value': mt.name,
                        } for mt in MediaType if mt],
                        'hint': '选择要收藏的影视类型。'
                    }
                }]
            }]
        }]
        # 尾部元素
        foot_elements = []
        # 收藏组件元素
        comp_elements = [self.__build_comp_form_element()]
        # 元素
        elements = [{
            'component': 'VForm',
            'content': header_elements + comp_elements + foot_elements
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
            self.__stop_comp_service()
            self.__stop_scheduler()
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
        # 启用的收藏夹
        enable_favorites = config.get("enable_favorites")
        if enable_favorites:
            comp_keys = self.__comp_objs.keys()
            enable_favorites = list(filter(lambda enable_favorite : enable_favorite and comp_keys and enable_favorite in comp_keys, enable_favorites))
            config["enable_favorites"] = enable_favorites
        # 影视数据来源
        media_data_sources = config.get("media_data_sources")
        if media_data_sources:
            mds_names = [mds.name for mds in MediaDataSource if mds]
            media_data_sources = list(filter(lambda media_data_source : media_data_source and mds_names and media_data_source in mds_names, media_data_sources))
            config["media_data_sources"] = media_data_sources
        # 收藏的影视类型
        collect_media_types = config.get("collect_media_types")
        if collect_media_types:
            mt_names = [mt.name for mt in MediaType if mt]
            collect_media_types = list(filter(lambda collect_media_type : collect_media_type and mt_names and collect_media_type in mt_names, collect_media_types))
            config["collect_media_types"] = collect_media_types
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

    def __get_collect_media_types_as_enum(self) -> List[MediaType]:
        """
        获取收藏的媒体类型枚举
        """
        collect_media_types = self.__get_config_item(config_key="collect_media_types")
        if not collect_media_types:
            return []
        media_type_map = MediaType._member_map_
        if not media_type_map:
            return []
        media_type_map_keys = media_type_map.keys()
        return [media_type_map.get(collect_media_type) for collect_media_type in collect_media_types if collect_media_type and collect_media_type in media_type_map_keys]

    def __get_collect_media_types_as_enum_value(self) -> List[str]:
        """
        获取收藏的媒体类型枚举value集合
        """
        enums = self.__get_collect_media_types_as_enum()
        if not enums:
            return []
        return [e.value for e in enums if e and e.value]

    def __check_comp_type(self, comp_type: type) -> bool:
        """
        检查组件类
        """
        if not comp_type:
            return False
        return issubclass(comp_type, Favorites) and comp_type is not Favorites

    def __extract_comp_key(self, comp_type: type) -> str:
        """
        提取组件key
        """
        if not comp_type:
            return None
        return comp_type.__name__.removesuffix(Favorites.__name__).lower()

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
        comp_types: List[Type[Favorites]] = ModuleHelper.load(
            package_path="app.plugins.mediacollecthelper.favorites",
            filter_func=lambda _, obj: self.__check_comp_type(comp_type=obj)
        )
        # 数量
        comp_count = len(comp_types) if comp_types else 0
        logger.info(f"总共加载到{comp_count}个收藏夹组件")
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
                comp_obj = comp_type(plugin=self)
                comp_obj.init_comp()
                self.__comp_objs[comp_key] = comp_obj
                logger.info(f"注册收藏夹组件 - {comp_name} - 成功")
            except Exception as e:
                logger.error(f"注册收藏夹组件 - {comp_name} - 异常: {str(e)}", exc_info=True)

    def __start_scheduler(self, timezone=None):
        """
        启动调度器
        :param timezone: 时区
        """
        try:
            if not self.__scheduler:
                if not timezone:
                    timezone = settings.TZ
                self.__scheduler = BackgroundScheduler(timezone=timezone)
                logger.debug(f"插件服务调度器初始化完成: timezone = {str(timezone)}")
            if not self.__scheduler.running:
                self.__scheduler.start()
                logger.debug(f"插件服务调度器启动成功")
                self.__scheduler.print_jobs()
        except Exception as e:
            logger.error(f"插件服务调度器启动异常: {str(e)}", exc_info=True)

    def __stop_scheduler(self):
        """
        停止调度器
        """
        try:
            logger.info('尝试停止插件服务调度器...')
            if self.__scheduler:
                self.__scheduler.remove_all_jobs()
                if self.__scheduler.running:
                    self.__scheduler.shutdown()
                self.__scheduler = None
                logger.info('插件服务调度器停止成功')
            else:
                logger.info('插件未启用服务调度器，无须停止')
        except Exception as e:
            logger.error(f"插件服务调度器停止异常: {str(e)}", exc_info=True)

    def __stop_comp_service(self):
        """
        停止所有组件的服务
        """
        try:
            logger.info('尝试停止所有组件...')
            if self.__comp_objs:
                for _, comp_obj in self.__comp_objs.items():
                    try:
                        comp_obj.stop_service()
                        logger.info(f'组件停止成功: {comp_obj.comp_name}')
                    except Exception as e:
                        logger.error(f'组件停止失败: {comp_obj.comp_name}, {str(e)}', exc_info=True)
                logger.info('所有组件停止成功')
            else:
                logger.info('插件未注册任何组件，无须处理')
        except Exception as e:
            logger.error(f"组件停止异常: {str(e)}", exc_info=True)

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
            if self.__subscribe_oper:
                self.__subscribe_oper = None
            if self.__exit_event:
                self.__exit_event = None
            if self.__atomic_cache:
                self.__atomic_cache.clear()
                self.__atomic_cache = None
            logger.info('回收内存成功')
        except Exception as e:
            logger.error(f"回收内存异常: {str(e)}", exc_info=True)

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
        return f'_tab_{key}'

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

    def __get_comp_form_elements(self, comp_obj: Favorites) -> List[dict]:
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

    def __wrapper_comp_form_model(self, comp_key: str, model: str) -> str:
        """
        包装组件表单model
        """
        if not comp_key or not model:
            return None
        return f"{comp_key}.{model}"

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

    def __get_comp_form_data(self, comp_obj: Favorites) -> Dict[str, Any]:
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

    def __try_run(self, media_data: List[MediaDigest] = None):
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
            self.__run(media_data=media_data)
        finally:
            self.__task_lock.release()

    def __async_try_run(self, media_data: List[MediaDigest] = None):
        """
        异步Try运行
        """
        self.__start_scheduler()
        def __do_task():
            self.__try_run(media_data=media_data)
        self.__scheduler.add_job(func=__do_task,
                                    trigger='date',
                                    run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                                    name='异步Try运行')

    def __block_run(self, media_data: List[MediaDigest] = None):
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
            self.__run(media_data=media_data)
        finally:
            self.__task_lock.release()

    def __async_block_run(self, media_data: List[MediaDigest] = None):
        """
        异步阻塞运行
        """
        self.__start_scheduler()
        def __do_task():
            self.__block_run(media_data=media_data)
        self.__scheduler.add_job(func=__do_task,
                                    trigger='date',
                                    run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                                    name='异步阻塞运行')

    def __run(self, media_data: List[MediaDigest] = None):
        """
        运行任务
        """
        run_results: List[Tuple[bool, str, Favorites, List[MediaDigest]]] = []
        try:
            if self.__exit_event.is_set():
                logger.warn(f"运行任务中止: 插件正在退出")
                return
            enable_favorites = self.__get_config_item(config_key="enable_favorites")
            if not enable_favorites:
                logger.warn("运行任务中止: 您未启用任何收藏夹")
                return
            if self.__exit_event.is_set():
                logger.warn(f"运行任务中止: 插件正在退出")
                return
            if not media_data:
                media_data = self.__get_media_data()
            if not media_data:
                logger.warn("没有找到符合条件的影视信息，请检查配置是否有误")
                return
            if self.__exit_event.is_set():
                logger.warn(f"运行任务中止: 插件正在退出")
                return
            for comp_key, comp_obj in self.__comp_objs.items():
                try:
                    if self.__exit_event.is_set():
                        logger.warn(f"运行任务中止: 插件正在退出, comp_key = {comp_key}")
                        break
                    result = self.__run_single(comp_obj=comp_obj, media_data=media_data)
                    run_results.append((True, comp_key, comp_obj, result))
                    logger.info(f"收藏夹[{comp_obj.comp_name}]任务执行完成, 共收藏了{len(result)}个")
                except Exception as e:
                    logger.error(f"收藏夹[{comp_obj.comp_name}]任务执行异常: {str(e)}", exc_info=True)
                    run_results.append((False, comp_key, comp_obj, None))
        except Exception as e:
            logger.error(f"运行插件任务异常: {str(e)}", exc_info=True)
        finally:
            self.__send_notify(run_results=run_results)

    def __send_notify(self, run_results: List[Tuple[bool, str, Favorites, List[MediaDigest]]]):
        """
        发送通知
        :param run_results: List[Tuple[是否成功, comp_key, comp_obj, result]]
        """
        if not run_results or not self.__get_config_item('enable_notify'):
            return
        text = self.__build_notify_message(run_results=run_results)
        if not text:
            return
        self.post_message(title=f'{self.plugin_name}任务执行结果', text=text, mtype=NotificationType.Plugin)

    @staticmethod
    def __build_notify_message(run_results: List[Tuple[bool, str, Favorites, List[MediaDigest]]]) -> str:
        """
        构建通知消息内容
        """
        text = ''
        if not run_results:
            return text
        for run_result in run_results:
            if not run_result:
                continue
            success, comp_key, comp_obj, result = run_result
            if not success:
                text += f'{comp_obj.comp_name}: 失败\n'
            else:
                if not comp_key or not comp_obj or not result:
                    continue
                text += f'{comp_obj.comp_name}: 收藏了{len(result)}条\n'
        return text

    def __run_single(self, comp_obj: Favorites, media_data: List[MediaDigest]) -> List[MediaDigest]:
        """
        针对单个收藏夹运行
        :return: 本次收藏的媒体集合
        """
        if not comp_obj or not media_data:
            return []
        try:
            if self.__exit_event.is_set():
                logger.warn(f"运行任务中止: 插件正在退出")
                return []
            return comp_obj.collect(media_data=media_data)
        except Exception as e:
            logger.error(f"运行单个收藏夹[{comp_obj.comp_name}]任务异常: {str(e)}", exc_info=True)
            raise e

    def __get_media_data_from_media_library(self) -> List[MediaDigest]:
        """
        从MP媒体库中获取媒体数据
        """
        return self.__get_media_data_from_media_library_db()

    def __get_media_data_from_media_library_db(self) -> List[MediaDigest]:
        """
        从MP媒体库数据库中获取媒体数据
        """
        media_data_sources = self.__get_config_item(config_key="media_data_sources")
        if not media_data_sources or MediaDataSource.MEDIA_LIBRARY.name not in media_data_sources:
            return []
        collect_media_types_as_enum_value = self.__get_collect_media_types_as_enum_value()
        if not collect_media_types_as_enum_value:
            return []
        msi_list: List[MediaServerItem] = MediaServerItem.list()
        if not msi_list:
            return []
        return [self.__convert_media_server_item_to_media_digest(msi=msi) for msi in msi_list if msi and msi.item_type and msi.item_type in collect_media_types_as_enum_value]

    @classmethod
    def __convert_media_server_item_to_media_digest(cls, msi: MediaServerItem) -> MediaDigest:
        """
        把MediaServerItem转换为MediaDigest
        """
        if not msi or not msi.tmdbid:
            return None
        return MediaDigest(title=msi.title, year=msi.year, type=MediaType(msi.item_type), tmdb_id=msi.tmdbid, imdb_id=msi.imdbid, tvdb_id=msi.tvdbid)

    def __get_media_data_from_subscribe(self) -> List[MediaDigest]:
        """
        从MP订阅中获取媒体数据
        """
        media_data_sources = self.__get_config_item(config_key="media_data_sources")
        if not media_data_sources or MediaDataSource.SUBSCRIBE.name not in media_data_sources:
            return []
        collect_media_types_as_enum_value = self.__get_collect_media_types_as_enum_value()
        if not collect_media_types_as_enum_value:
            return []
        sub_list: List[Subscribe] = self.__subscribe_oper.list()
        if not sub_list:
            return []
        return [self.__convert_subscribe_to_media_digest(sub=sub) for sub in sub_list if sub and sub.type and sub.type in collect_media_types_as_enum_value]

    @classmethod
    def __convert_subscribe_to_media_digest(cls, sub: Subscribe) -> MediaDigest:
        """
        把Subscribe转换为MediaDigest
        """
        if not sub or not sub.tmdbid:
            return None
        return MediaDigest(title=sub.name, year=sub.year, type=MediaType(sub.type), tmdb_id=sub.tmdbid, imdb_id=sub.imdbid, tvdb_id=sub.tvdbid)

    def __get_media_data_from_subscribe_history(self) -> List[MediaDigest]:
        """
        从MP订阅历史中获取媒体数据
        """
        media_data_sources = self.__get_config_item(config_key="media_data_sources")
        if not media_data_sources or MediaDataSource.SUBSCRIBE_HISTORY.name not in media_data_sources:
            return []
        collect_media_types_as_enum_value = self.__get_collect_media_types_as_enum_value()
        if not collect_media_types_as_enum_value:
            return []
        sub_his_list: List[SubscribeHistory] = SubscribeHistory.list()
        if not sub_his_list:
            return []
        return [self.__convert_subscribe_history_to_media_digest(sub_his=sub_his) for sub_his in sub_his_list if sub_his and sub_his.type and sub_his.type in collect_media_types_as_enum_value]

    @classmethod
    def __convert_subscribe_history_to_media_digest(cls, sub_his: SubscribeHistory) -> MediaDigest:
        """
        把SubscribeHistory转换为MediaDigest
        """
        if not sub_his or not sub_his.tmdbid:
            return None
        return MediaDigest(title=sub_his.name, year=sub_his.year, type=MediaType(sub_his.type), tmdb_id=sub_his.tmdbid, imdb_id=sub_his.imdbid, tvdb_id=sub_his.tvdbid)

    def __get_media_data(self) -> List[MediaDigest]:
        """
        获取媒体数据
        """
        data: List[MediaDigest] = self.__get_media_data_from_media_library() \
                                + self.__get_media_data_from_subscribe() \
                                + self.__get_media_data_from_subscribe_history()
        result: List[MediaDigest] = []
        if not data:
            return result
        tmdb_ids = set()
        for md in data:
            if not md or not md.tmdb_id or md.tmdb_id in tmdb_ids:
                continue
            result.append(md)
            tmdb_ids.add(md.tmdb_id)
        return result

    def __check_event_and_get_mediainfo(self, event: Optional[Event]) -> Tuple[bool, Union[MediaInfo, dict]]:
        """
        检查事件对象并返回媒体信息
        """
        if not event or not event.event_data:
            logger.warn('事件信息无效，忽略事件')
            return False, None
        mediainfo = event.event_data.get("mediainfo")
        if not mediainfo:
            logger.warn('事件信息无效，忽略事件')
            return False, mediainfo
        if not self.get_state():
            logger.warn('插件状态无效，忽略事件')
            return False, mediainfo
        enable_favorites = self.__get_config_item(config_key="enable_favorites")
        if not enable_favorites:
            logger.warn("未启用任何收藏夹，忽略事件")
            return False, mediainfo
        if self.__exit_event.is_set():
            logger.warn('插件服务正在退出，忽略事件')
            return False, mediainfo
        return True, mediainfo

    @eventmanager.register(EventType.TransferComplete)
    def listen_transfer_complete_event(self, event: Event = None):
        """
        监听转移完成事件
        """
        logger.info('监听到转移完成事件')
        try:
            success, mediainfo = self.__check_event_and_get_mediainfo(event=event)
            if not success:
                return
            media_data_sources = self.__get_config_item("media_data_sources")
            if not media_data_sources or MediaDataSource.MEDIA_LIBRARY.name not in media_data_sources:
                logger.warn(f"未启用{MediaDataSource.MEDIA_LIBRARY.value}的数据来源，忽略事件")
                return
            collect_media_types = self.__get_config_item("collect_media_types")
            if not collect_media_types or mediainfo.type.name not in collect_media_types:
                logger.warn(f"未启用{mediainfo.type.value}类型，忽略事件")
                return
            if self.__exit_event.is_set():
                logger.warn('插件服务正在退出，忽略事件')
                return
            atomic_cache_key = f"tmdb:{mediainfo.type.name.lower()}:{mediainfo.tmdb_id}"
            if self.__atomic_cache.get_and_set(key=atomic_cache_key, value=True):
                logger.warn(f'短期内已经处理过该媒体，忽略事件: title = {mediainfo.title}, year = {mediainfo.year}, type = {mediainfo.type}, tmdb_id = {mediainfo.tmdb_id}')
                return
            logger.info('转移完成事件监听任务执行开始...')
            md = MediaDigest(title=mediainfo.title, year=mediainfo.year, type=mediainfo.type, tmdb_id=mediainfo.tmdb_id, imdb_id=mediainfo.imdb_id, tvdb_id=mediainfo.tvdb_id)
            self.__async_block_run(media_data=[md])
            logger.info('转移完成事件监听任务执行成功')
        except Exception as e:
            logger.error(f'转移完成事件监听任务执行异常: {str(e)}', exc_info=True)

    @eventmanager.register(EventType.SubscribeAdded)
    def listen_subscribe_added_event(self, event: Event = None):
        """
        监听订阅已添加事件
        """
        logger.info('监听到订阅已添加事件')
        try:
            success, mediainfo = self.__check_event_and_get_mediainfo(event=event)
            if not success:
                return
            media_data_sources = self.__get_config_item("media_data_sources")
            if not media_data_sources or MediaDataSource.SUBSCRIBE.name not in media_data_sources:
                logger.warn(f"未启用{MediaDataSource.SUBSCRIBE.value}的数据来源，忽略事件")
                return
            media_type: str = mediainfo.get("type")
            media_type: MediaType = MediaType(media_type)
            collect_media_types = self.__get_config_item("collect_media_types")
            if not collect_media_types or media_type.name not in collect_media_types:
                logger.warn(f"未启用{media_type.value}类型，忽略事件")
                return
            if self.__exit_event.is_set():
                logger.warn('插件服务正在退出，忽略事件')
                return
            logger.info('订阅已添加事件监听任务执行开始...')
            md = MediaDigest(title=mediainfo.get("title"), year=mediainfo.get("year"), type=media_type, tmdb_id=mediainfo.get("tmdb_id"), imdb_id=mediainfo.get("imdb_id"), tvdb_id=mediainfo.get("tvdb_id"))
            self.__async_block_run(media_data=[md])
            logger.info('订阅已添加事件监听任务执行成功')
        except Exception as e:
            logger.error(f'订阅已添加事件监听任务执行异常: {str(e)}', exc_info=True)
