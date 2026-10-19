import asyncio
from datetime import datetime, timedelta
from threading import RLock, Event as ThreadEvent
from typing import Any, List, Dict, Tuple, Optional

import pytz
import yaml
from app.schemas.system import MediaServerConf
from app.schemas.types import MediaServerType
from app.sdk.config import settings
from app.sdk.logging import logger
# noinspection PyProtectedMember
from app.sdk.plugin.base import _PluginBase
from app.sdk.services import MediaServerHelper
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .model import SyncScope, StarredDTO
from .navidrome_client import NavidromeClient
from .navidrome_client.action import events


# noinspection SpellCheckingInspection,DuplicatedCode,PyShadowingNames
class NavidromeUserSync(_PluginBase):
    # 插件名称
    plugin_name = "Navidrome用户同步"
    # 插件描述
    plugin_desc = "多用户间自动同步收藏与歌单。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/hotlcc/MoviePilot-Plugins-Third/main/icons/NavidromeRadioSource.png"
    # 插件版本
    plugin_version = "3.0.9"
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
    __group_account_map: Optional[Dict[str, Any]] = None
    # Navidrome客户端
    __navidrome_clients: Optional[Dict[str, NavidromeClient]] = None
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
        # 配置
        self.__config = self.__fix_config(config=config)
        # 检查配置
        check_config = self.__check_config()
        if not check_config:
            return
        # 初始化客户端
        self.__init_navidrome_clients()
        # 启动客户端
        asyncio.run(self.__start_navidrome_clients())
        self.__init_scheduler()
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
                                'component': 'VTextarea',
                                'props': {
                                    'model': 'group_accounts',
                                    'label': '分组账户',
                                    'placeholder': 'YML格式内容。支持配置1到N个分组，每个分组下至少配置2个账户，分组下的全部账户间相互同步。\n'
                                                   '例如：\n'
                                                   'groups:\n'
                                                   '  - name: 分组1\n'
                                                   '    accounts:\n'
                                                   '      - username: 用户名11\n'
                                                   '        password: 密码11\n'
                                                   '      - username: 用户名12\n'
                                                   '        password: 密码12\n'
                                                   '  - name: 分组2\n'
                                                   '    accounts:\n'
                                                   '      - username: 用户名21\n'
                                                   '        password: 密码21\n'
                                                   '      - username: 用户名22\n'
                                                   '        password: 密码22\n'
                                                   '',
                                    'hint': '分组账户。'
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
            asyncio.run(self.__stop_navidrome_clients())
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

    def __check_config(self) -> bool:
        result = True
        if not self.__get_config_item("navidrome_server"):
            logger.error("配置检查不通过：Navidrome服务器")
            result = False
        if not self.__get_config_item("sync_scopes"):
            logger.error("配置检查不通过：同步范围")
            result = False
        if not self.__check_group_accounts():
            result = False
        return result

    def __check_group_accounts(self) -> bool:
        group_accounts = self.__get_config_item("group_accounts") or ""
        group_accounts_obj = yaml.safe_load(stream=group_accounts) or {}
        if not group_accounts_obj:
            logger.error("配置检查不通过：分组账户")
            return False
        groups = group_accounts_obj.get("groups") or []
        if not groups:
            logger.error("配置检查不通过：分组账户[groups]")
            return False
        result = True
        self.__group_account_map = group_account_map = {}
        for group_index, group in enumerate(groups):
            group_path = f"groups[{group_index}]"
            if not group:
                logger.error(f"配置检查不通过：分组账户.{group_path}")
                result = False
                continue
            name = group.get("name")
            account_map = {}
            if not name:
                logger.error(f"配置检查不通过：分组账户.{group_path}.name")
                result = False
            elif name in group_account_map.keys():
                logger.error(f"配置检查不通过：分组账户.{group_path}.name重复")
                result = False
            else:
                group_account_map[name] = account_map
            accounts = group.get("accounts") or []
            if not accounts:
                logger.error(f"配置检查不通过：分组账户.{group_path}.accounts")
                result = False
            else:
                for account_index, account in enumerate(accounts):
                    account_path = f"{group_path}.accounts[{account_index}]"
                    if not account:
                        logger.error(f"配置检查不通过：分组账户.{account_path}")
                        result = False
                        continue
                    username = account.get("username")
                    if not username:
                        logger.error(f"配置检查不通过：分组账户.{account_path}.username")
                        result = False
                    elif username in account_map.keys():
                        logger.error(f"配置检查不通过：分组账户.{account_path}.username重复")
                        result = False
                    else:
                        account_map[username] = account
                    password = account.get("password")
                    if not password:
                        logger.error(f"配置检查不通过：分组账户.{account_path}.password")
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

    def __init_navidrome_clients(self) -> None:
        navidrome_server_info = self.__get_navidrome_server_info() or {}
        if not navidrome_server_info:
            raise Exception("Navidrome服务器配置无效")
        host = navidrome_server_info.get("host")

        navidrome_clients: Dict[str, NavidromeClient] = {}
        group_account_map: Dict[str, Dict[str, Dict[str, Any]]] = self.__group_account_map or {}
        for group_name, account_map in group_account_map.items():
            if not group_name or not account_map:
                continue
            for username, account in account_map.items():
                if not username or not account:
                    continue
                password = account.get("password")
                if not password:
                    continue
                navidrome_client = NavidromeClient(base_url=host, username=username, password=password)
                navidrome_clients[username] = navidrome_client
        self.__navidrome_clients = navidrome_clients

    async def __start_navidrome_clients(self) -> None:
        if not self.__get_config_item(config_key='real_time_listen'):
            return
        navidrome_clients: Dict[str, NavidromeClient] = self.__navidrome_clients or {}
        if not navidrome_clients:
            return
        for username, navidrome_client in navidrome_clients.items():
            if not username or not navidrome_client:
                continue
            navidrome_client.events().add_handler(
                event_type=events.EventType.RefreshResource,
                handler=lambda event_type, event_data: self.__on_refresh_resource_event(username=username, event_data=event_data),
            )
            await navidrome_client.events().start_listen()

    async def __stop_navidrome_clients(self) -> None:
        if not self.__get_config_item(config_key='real_time_listen'):
            return
        navidrome_clients: Dict[str, NavidromeClient] = self.__navidrome_clients or {}
        if not navidrome_clients:
            return
        for username, navidrome_client in navidrome_clients.items():
            if not username or not navidrome_client:
                continue
            await navidrome_client.events().stop_listen()

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
        group_account_map: Dict[str, Dict[str, Dict[str, Any]]] = self.__group_account_map or {}
        if not group_account_map:
            return
        for group_name, account_map in group_account_map.items():
            if not group_name or not account_map:
                continue
            usernames = list(account_map.keys())
            try:
                logger.info(f"用户同步 - 单个分组 - 开始: group_name = {group_name}")
                self.__sync_data(usernames=usernames)
                logger.info(f"用户同步 - 单个分组 - 成功: group_name = {group_name}")
            except Exception as e:
                logger.error(f"用户同步 - 单个分组 - 失败: group_name = {group_name}, error = {e}")

    def __on_refresh_resource_event(self, username: str, event_data: Dict[str, Any]) -> None:
        if not username or not event_data:
            return
        if not self.__get_config_item(config_key='real_time_listen'):
            return

    @classmethod
    def __convert_dict_to_starred_dto(cls, data: Dict[str, Any]) -> Optional[StarredDTO]:
        if not data:
            return None
        id = data.get("id")
        if not id:
            return None
        return StarredDTO(id=id, starred=data.get("starred"), starredAt=data.get("starredAt"))

    @classmethod
    def __convert_dict_list_to_starred_dto_list(cls, data_list: List[Dict[str, Any]]) -> Optional[List[StarredDTO]]:
        if not data_list:
            return None
        result = []
        for data in data_list:
            starred_dto = cls.__convert_dict_to_starred_dto(data)
            if not starred_dto:
                continue
            result.append(starred_dto)
        return result

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
        if not host:
            logger.warn("选择的Navidrome服务器配置无效")
            return None

        return {
            "host": host,
        }

    def __sync_data(self, usernames: List[str]):
        if not usernames:
            return
        usernames_str = ",".join(usernames)
        logger.info(f"分组同步 - 开始: usernames = {usernames_str}")

        try:
            logger.info(f"分组同步 - 歌曲收藏 - 开始: usernames = {usernames_str}")
            self.__sync_song_star(usernames=usernames)
            logger.info(f"分组同步 - 歌曲收藏 - 完成: usernames = {usernames_str}")
        except Exception as e:
            logger.error(f"分组同步 - 歌曲收藏 - 失败: usernames = {usernames_str}, error = {e}")

        try:
            logger.info(f"分组同步 - 专辑收藏 - 开始: usernames = {usernames_str}")
            self.__sync_album_star(usernames=usernames)
            logger.info(f"分组同步 - 专辑收藏 - 完成: usernames = {usernames_str}")
        except Exception as e:
            logger.error(f"分组同步 - 专辑收藏 - 失败: usernames = {usernames_str}, error = {e}")

        try:
            logger.info(f"分组同步 - 艺人收藏 - 开始: usernames = {usernames_str}")
            self.__sync_artist_star(usernames=usernames)
            logger.info(f"分组同步 - 艺人收藏 - 完成: usernames = {usernames_str}")
        except Exception as e:
            logger.error(f"分组同步 - 艺人收藏 - 失败: usernames = {usernames_str}, error = {e}")

        try:
            logger.info(f"分组同步 - 公开歌单收藏 - 开始: usernames = {usernames_str}")
            self.__sync_public_playlist_star(usernames=usernames)
            logger.info(f"分组同步 - 公开歌单收藏 - 完成: usernames = {usernames_str}")
        except Exception as e:
            logger.error(f"分组同步 - 公开歌单收藏 - 失败: usernames = {usernames_str}, error = {e}")

        logger.info(f"分组同步 - 完成: usernames = {usernames_str}")

    @classmethod
    def __merge_latest_version(cls, user_data_map: Dict[str, List[StarredDTO]]) -> Dict[str, StarredDTO]:
        latest_version_map: Dict[str, StarredDTO] = {}
        if not user_data_map:
            return latest_version_map
        for dto_list in user_data_map.values():
            if not dto_list:
                continue
            for dto in dto_list:
                if not dto or not dto.id:
                    continue
                existing_dto = latest_version_map.get(dto.id)
                if not existing_dto:
                    latest_version_map[dto.id] = dto
                else:
                    latest_version_map[dto.id] = dto.marge_latest_version(other=existing_dto)
        return latest_version_map

    def __batch_update_star_for_user(self,
                                     sync_scope: SyncScope,
                                     username: str,
                                     user_data_map: Dict[str, List[StarredDTO]],
                                     latest_version_map: Dict[str, StarredDTO]) -> None:
        if not sync_scope or not username or not user_data_map or not latest_version_map:
            return
        logger.info(f"分组同步 - {sync_scope.value} - 执行同步 - 单个用户 - 开始: username = {username}")
        user_dto_list = user_data_map.get(username)
        if not user_dto_list:
            logger.warn(f"分组同步 - {sync_scope.value} - 执行同步 - 单个用户 - 终止: username = {username}, 原因 = 用户无数据")
            return
        navidrome_client = self.__navidrome_clients.get(username)
        if not navidrome_client:
            logger.warn(f"分组同步 - {sync_scope.value} - 执行同步 - 单个用户 - 终止: username = {username}, 原因 = 用户客户端不存在")
            return
        for user_dto in user_dto_list:
            if not user_dto or not user_dto.id:
                continue
            latest_version_dto = latest_version_map.get(user_dto.id)
            if not latest_version_dto:
                continue
            if (user_dto.starred or False) == (latest_version_dto.starred or False):
                continue
            if latest_version_dto.starred:
                navidrome_client.rest().star(id=user_dto.id)
                logger.debug(f"分组同步 - {sync_scope.value} - 执行同步 - 单个用户 - 添加收藏: username = {username}, id = {user_dto.id}")
            else:
                navidrome_client.rest().unstar(id=user_dto.id)
                logger.debug(f"分组同步 - {sync_scope.value} - 执行同步 - 单个用户 - 取消收藏: username = {username}, id = {user_dto.id}")
        logger.info(f"分组同步 - {sync_scope.value} - 执行同步 - 单个用户 - 完成: username = {username}")

    def __sync_song_star(self, usernames: List[str]):
        """
        同步歌曲收藏
        """
        if not usernames:
            return
        usernames_str = ",".join(usernames)

        sync_scope = SyncScope.SongStar
        sync_scopes = self.__get_config_item(config_key='sync_scopes') or []
        if not sync_scopes or sync_scope.name not in sync_scopes:
            logger.warn(f"分组同步 - {sync_scope.value} - 终止: usernames = {usernames_str}, 原因 = 不含该同步范围")
            return

        logger.info(f"分组同步 - {sync_scope.value} - 获取用户数据 - 开始: usernames = {usernames_str}")
        user_data_map: Dict[str, List[StarredDTO]] = {}
        for username in usernames:
            if not username:
                continue
            navidrome_client = self.__navidrome_clients.get(username)
            if not navidrome_client:
                continue
            user_data_list = self.__convert_dict_list_to_starred_dto_list(data_list=navidrome_client.song().list()) or []
            user_data_map[username] = user_data_list
            logger.info(f"分组同步 - {sync_scope.value} - 获取用户数据 - 单个用户完成: username = {username}, num = {len(user_data_list)}")
        logger.info(f"分组同步 - {sync_scope.value} - 获取用户数据 - 完成: usernames = {usernames_str}")

        logger.info(f"分组同步 - {sync_scope.value} - 合并最终版本 - 开始: usernames = {usernames_str}")
        latest_version_map: Dict[str, StarredDTO] = self.__merge_latest_version(user_data_map=user_data_map)
        logger.info(f"分组同步 - {sync_scope.value} - 合并最终版本 - 完成: usernames = {usernames_str}, num = {len(latest_version_map)}")

        logger.info(f"分组同步 - {sync_scope.value} - 执行同步 - 开始: usernames = {usernames_str}")
        for username in usernames:
            self.__batch_update_star_for_user(sync_scope=sync_scope, username=username, user_data_map=user_data_map, latest_version_map=latest_version_map)
        logger.info(f"分组同步 - {sync_scope.value} - 执行同步 - 完成: usernames = {usernames_str}")

    def __sync_album_star(self, usernames: List[str]):
        """
        同步专辑收藏
        """
        if not usernames:
            return
        usernames_str = ",".join(usernames)

        sync_scope = SyncScope.AlbumStar
        sync_scopes = self.__get_config_item(config_key='sync_scopes') or []
        if not sync_scopes or sync_scope.name not in sync_scopes:
            logger.warn(f"分组同步 - {sync_scope.value} - 终止: usernames = {usernames_str}, 原因 = 不含该同步范围")
            return

        logger.info(f"分组同步 - {sync_scope.value} - 获取用户数据 - 开始: usernames = {usernames_str}")
        user_data_map: Dict[str, List[StarredDTO]] = {}
        for username in usernames:
            if not username:
                continue
            navidrome_client = self.__navidrome_clients.get(username)
            if not navidrome_client:
                continue
            user_data_list = self.__convert_dict_list_to_starred_dto_list(data_list=navidrome_client.album().list()) or []
            user_data_map[username] = user_data_list
            logger.info(f"分组同步 - {sync_scope.value} - 获取用户数据 - 单个用户完成: username = {username}, num = {len(user_data_list)}")
        logger.info(f"分组同步 - {sync_scope.value} - 获取用户数据 - 完成: usernames = {usernames_str}")

        logger.info(f"分组同步 - {sync_scope.value} - 合并最终版本 - 开始: usernames = {usernames_str}")
        latest_version_map: Dict[str, StarredDTO] = self.__merge_latest_version(user_data_map=user_data_map)
        logger.info(f"分组同步 - {sync_scope.value} - 合并最终版本 - 完成: usernames = {usernames_str}, num = {len(latest_version_map)}")

        logger.info(f"分组同步 - {sync_scope.value} - 执行同步 - 开始: usernames = {usernames_str}")
        for username in usernames:
            self.__batch_update_star_for_user(sync_scope=sync_scope, username=username, user_data_map=user_data_map, latest_version_map=latest_version_map)
        logger.info(f"分组同步 - {sync_scope.value} - 执行同步 - 完成: usernames = {usernames_str}")

    def __sync_artist_star(self, usernames: List[str]):
        """
        同步艺人收藏
        """
        if not usernames:
            return
        usernames_str = ",".join(usernames)

        sync_scope = SyncScope.ArtistStar
        sync_scopes = self.__get_config_item(config_key='sync_scopes') or []
        if not sync_scopes or sync_scope.name not in sync_scopes:
            logger.warn(f"分组同步 - {sync_scope.value} - 终止: usernames = {usernames_str}, 原因 = 不含该同步范围")
            return

        logger.info(f"分组同步 - {sync_scope.value} - 获取用户数据 - 开始: usernames = {usernames_str}")
        user_data_map: Dict[str, List[StarredDTO]] = {}
        for username in usernames:
            if not username:
                continue
            navidrome_client = self.__navidrome_clients.get(username)
            if not navidrome_client:
                continue
            user_data_list = self.__convert_dict_list_to_starred_dto_list(data_list=navidrome_client.artist().list()) or []
            user_data_map[username] = user_data_list
            logger.info(f"分组同步 - {sync_scope.value} - 获取用户数据 - 单个用户完成: username = {username}, num = {len(user_data_list)}")
        logger.info(f"分组同步 - {sync_scope.value} - 获取用户数据 - 完成: usernames = {usernames_str}")

        logger.info(f"分组同步 - {sync_scope.value} - 合并最终版本 - 开始: usernames = {usernames_str}")
        latest_version_map: Dict[str, StarredDTO] = self.__merge_latest_version(user_data_map=user_data_map)
        logger.info(f"分组同步 - {sync_scope.value} - 合并最终版本 - 完成: usernames = {usernames_str}, num = {len(latest_version_map)}")

        logger.info(f"分组同步 - {sync_scope.value} - 执行同步 - 开始: usernames = {usernames_str}")
        for username in usernames:
            self.__batch_update_star_for_user(sync_scope=sync_scope, username=username, user_data_map=user_data_map, latest_version_map=latest_version_map)
        logger.info(f"分组同步 - {sync_scope.value} - 执行同步 - 完成: usernames = {usernames_str}")

    def __sync_public_playlist_star(self, usernames: List[str]):
        """
        同步公开歌单收藏
        """
        if not usernames:
            return
        usernames_str = ",".join(usernames)

        sync_scope = SyncScope.PublicPlaylistStar
        sync_scopes = self.__get_config_item(config_key='sync_scopes') or []
        if not sync_scopes or sync_scope.name not in sync_scopes:
            logger.warn(f"分组同步 - {sync_scope.value} - 终止: usernames = {usernames_str}, 原因 = 不含该同步范围")
            return

        logger.info(f"分组同步 - {sync_scope.value} - 获取用户数据 - 开始: usernames = {usernames_str}")
        user_data_map: Dict[str, List[StarredDTO]] = {}
        for username in usernames:
            if not username:
                continue
            navidrome_client = self.__navidrome_clients.get(username)
            if not navidrome_client:
                continue
            user_data_list = self.__convert_dict_list_to_starred_dto_list(data_list=navidrome_client.playlist().list(public=True)) or []
            user_data_map[username] = user_data_list
            logger.info(f"分组同步 - {sync_scope.value} - 获取用户数据 - 单个用户完成: username = {username}, num = {len(user_data_list)}")
        logger.info(f"分组同步 - {sync_scope.value} - 获取用户数据 - 完成: usernames = {usernames_str}")

        logger.info(f"分组同步 - {sync_scope.value} - 合并最终版本 - 开始: usernames = {usernames_str}")
        latest_version_map: Dict[str, StarredDTO] = self.__merge_latest_version(user_data_map=user_data_map)
        logger.info(f"分组同步 - {sync_scope.value} - 合并最终版本 - 完成: usernames = {usernames_str}, num = {len(latest_version_map)}")

        logger.info(f"分组同步 - {sync_scope.value} - 执行同步 - 开始: usernames = {usernames_str}")
        for username in usernames:
            self.__batch_update_star_for_user(sync_scope=sync_scope, username=username, user_data_map=user_data_map, latest_version_map=latest_version_map)
        logger.info(f"分组同步 - {sync_scope.value} - 执行同步 - 完成: usernames = {usernames_str}")
