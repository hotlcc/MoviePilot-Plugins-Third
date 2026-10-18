from datetime import datetime, timedelta
from threading import RLock, Event as ThreadEvent
from typing import Any, List, Dict, Tuple, Optional

import pytz
from app.schemas.system import MediaServerConf
from app.schemas.types import MediaServerType
from app.sdk.config import settings
from app.sdk.logging import logger
# noinspection PyProtectedMember
from app.sdk.plugin.base import _PluginBase
from app.sdk.services import MediaServerHelper
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .model import SyncScope


# noinspection SpellCheckingInspection,DuplicatedCode,PyShadowingNames
class NavidromeUserSync(_PluginBase):
    # 插件名称
    plugin_name = "Navidrome用户同步"
    # 插件描述
    plugin_desc = "多用户间自动同步收藏与歌单。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/hotlcc/MoviePilot-Plugins-Third/main/icons/NavidromeRadioSource.png"
    # 插件版本
    plugin_version = "3.0.2"
    # 插件作者
    plugin_author = "hotlcc"
    # 作者主页
    author_url = "https://github.com/hotlcc"
    # 插件配置项ID前缀
    plugin_config_prefix = "com.hotlcc.navidromeusersync."
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
        "cron": "0 4 * * *"
    }

    # 对象私有属性
    # 任务锁
    __task_lock: Optional[RLock] = None
    # 退出事件
    __exit_event: Optional[ThreadEvent] = None
    # 插件用户配置
    __config: Optional[Dict[str, Any]] = None
    # 调度器
    __scheduler: Optional[BackgroundScheduler] = None

    def __init__(self):
        super().__init__()
        # 对象私有属性
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
                        'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                    },
                    'content': [{
                        'component': 'VSwitch',
                        'props': {
                            'model': 'real_time_listen',
                            'label': '实时监听',
                            'hint': '监听Navidrome的事件并实时处理。'
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
                            'model': 'sync_scopes',
                            'label': '同步范围',
                            'multiple': True,
                            'chips': True,
                            'items': [{
                                'title': scope.value,
                                'value': scope.name,
                            } for scope in SyncScope if scope],
                            'hint': '选择要同步的范围。必选。'
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
                            'model': '_config_group_account_dialog_closed',
                            'label': '配置分组账户',
                            'hint': '点击展开分组账户配置窗口。'
                        }
                    }]
                }]
            }, {
                    'component': 'VDialog',
                    'props': {
                        'model': '_config_group_account_dialog_closed',
                        'max-width': '40rem'
                    },
                    'content': [{
                        'component': 'VCard',
                        'props': {
                            'title': '配置分组账户',
                            'style': {
                                'padding': '0 20px 20px 20px'
                            }
                        },
                        'content': [{
                            'component': 'VDialogCloseBtn',
                            'props': {
                                'model': '_config_group_account_dialog_closed'
                            }
                        }, {
                            'component': 'VRow',
                            'content': [{
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [{
                                    'component': 'VAceEditor',
                                    'props': {
                                        'model': 'group_account_yml',
                                        'lang': 'yml',
                                        'theme': 'monokai',
                                        'placeholder': '分组账户配置',
                                        'options': {
                                            'showGutter': True,
                                            'showLineNumbers': True,
                                        }
                                    }
                                }]
                            }]
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
        pass

    def __get_navidrome_configs(self) -> Optional[List[MediaServerConf]]:
        config_map = self.__media_server_helper.get_configs(include_disabled=True) or {}
        if not config_map:
            return None
        type_str = MediaServerType.Navidrome.name.lower()
        configs = list(config_map.values()) or []
        return [config for config in configs if config and config.type == type_str]

    def __get_navidrome_config(self, name: str) -> Optional[MediaServerConf]:
        return self.__media_server_helper.get_config(name=name)
