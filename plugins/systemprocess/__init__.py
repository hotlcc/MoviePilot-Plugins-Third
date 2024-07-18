from typing import Any, List, Dict, Tuple, Optional

from app.plugins import _PluginBase
from app.schemas.dashboard import ProcessInfo
from app.utils.string import StringUtils
from app.utils.system import SystemUtils


class SystemProcess(_PluginBase):
    # 插件名称
    plugin_name = "系统进程"
    # 插件描述
    plugin_desc = "查看系统进程，支持仪表板"
    # 插件图标
    plugin_icon = "Dsfinder_A.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "hotlcc"
    # 作者主页
    author_url = "https://github.com/hotlcc"
    # 插件配置项ID前缀
    plugin_config_prefix = "com.hotlcc.systemprocess."
    # 加载顺序
    plugin_order = 66
    # 可使用的用户级别
    auth_level = 1

    # 配置相关
    # 插件缺省配置
    __config_default: Dict[str, Any] = {
        'dashboard_widget_size': 8
    }
    # 插件用户配置
    __config: Dict[str, Any] = {}

    def init_plugin(self, config: dict = None):
        """
        生效配置信息
        :param config: 配置信息字典
        """
        # 停止现有服务
        self.stop_service()

        # 修正配置
        config = self.__fix_config(config=config)
        # 加载插件配置
        self.__config = config

    def get_state(self) -> bool:
        """
        获取插件运行状态
        """
        return True if self.__get_config_item(config_key='enable') else False

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
            'dashboard_widget_refresh': 5
        }
        # 合并默认配置
        config_suggest.update(self.__config_default)
        # 表单内容
        form_content = [{
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
                            'model': 'dashboard_widget_size',
                            'label': '仪表板尺寸',
                            'items': [
                                {'title': '100%', 'value': 12},
                                {'title': '2/3', 'value': 8},
                                {'title': '50%', 'value': 6},
                                {'title': '1/3', 'value': 4}
                            ],
                            'hint': '选择仪表板系统进程组件尺寸。'
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
                            'model': 'dashboard_widget_refresh',
                            'label': '仪表板刷新间隔(秒)',
                            'placeholder': '5',
                            'type': 'number',
                            'hint': '仪表板组件刷新时间间隔，单位为秒，缺省时不刷新。'
                        }
                    }]
                }]
            }]
        }]
        return form_content, config_suggest

    def get_page(self) -> List[dict]:
        """
        拼装插件详情页面，需要返回页面配置，同时附带数据
        插件详情页面使用Vuetify组件拼装，参考：https://vuetifyjs.com/
        """
        system_process_table_element = self.__build_system_process_table_element()
        return [system_process_table_element]

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

    def get_dashboard(self, key: str, **kwargs) -> Optional[Tuple[Dict[str, Any], Dict[str, Any], List[dict]]]:
        """
        获取插件仪表盘页面，需要返回：1、仪表板col配置字典；2、全局配置（自动刷新等）；3、仪表板页面元素配置json（含数据）
        1、col配置参考：
        {
            "cols": 12, "md": 6
        }
        2、全局配置参考：
        {
            "refresh": 10, // 自动刷新时间，单位秒
            "border": True, // 是否显示边框，默认True，为False时取消组件边框和边距，由插件自行控制
            "title": "组件标题", // 组件标题，如有将显示该标题，否则显示插件名称
            "subtitle": "组件子标题", // 组件子标题，缺省时不展示子标题
        }
        3、页面配置使用Vuetify组件拼装，参考：https://vuetifyjs.com/

        kwargs参数可获取的值：1、user_agent：浏览器UA

        :param key: 仪表盘key，根据指定的key返回相应的仪表盘数据，缺省时返回一个固定的仪表盘数据（兼容旧版）
        """
        return self.__get_system_process_dashboard()

    def stop_service(self):
        """
        停止插件
        """
        pass

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
        return config

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

    @staticmethod
    def __get_all_process_info() -> List[ProcessInfo]:
        """
        获取全部进程信息
        """
        all_process_info = SystemUtils.processes()
        if not all_process_info:
            return []
        return sorted(all_process_info, key=lambda info: info.pid, reverse=True)

    @classmethod
    def __build_system_process_table_element(cls, max_height = None) -> dict:
        """
        构造系统进程表格元素
        """
        # 进程数据
        all_process_info = cls.__get_all_process_info()
        # 表内容
        if all_process_info:
            table_contents = [{
                'component': 'tr',
                'props': {
                    'class': 'text-sm'
                },
                'content': [{
                    'component': 'td',
                    'props': {
                        'class': 'whitespace-nowrap'
                    },
                    'text': item.pid
                }, {
                    'component': 'td',
                    'props': {
                        'class': 'whitespace-nowrap'
                    },
                    'text': item.name
                }, {
                    'component': 'td',
                    'props': {
                        'class': 'whitespace-nowrap'
                    },
                    'text': StringUtils.str_secends(time_sec=item.run_time)
                }, {
                    'component': 'td',
                    'props': {
                        'class': 'whitespace-nowrap'
                    },
                    'text': f'{item.memory}MB'
                }]
            } for item in all_process_info if item]
        else:
            table_contents = [{
                'component': 'tr',
                'props': {
                    'class': 'text-sm'
                },
                'content': [{
                    'component': 'td',
                    'props': {
                        'colspan': '6',
                        'class': 'text-center'
                    },
                    'text': '暂无数据'
                }]
            }]
        # 表样式
        table_style = {}
        if max_height:
            table_style['max-height'] = max_height
        # 表
        table = {
            'component': 'VTable',
            'props': {
                'hover': True,
                'fixed-header': True,
                'density': 'compact',
                'style': table_style
            },
            'content': [{
                'component': 'thead',
                'content': [{
                    'component': 'th',
                    'props': {
                        'class': 'text-start ps-4'
                    },
                    'text': '进程ID'
                }, {
                    'component': 'th',
                    'props': {
                        'class': 'text-start ps-4'
                    },
                    'text': '进程名称'
                }, {
                    'component': 'th',
                    'props': {
                        'class': 'text-start ps-4'
                    },
                    'text': '运行时长'
                }, {
                    'component': 'th',
                    'props': {
                        'class': 'text-start ps-4'
                    },
                    'text': '占用内存'
                }]
            }, {
                'component': 'tbody',
                'content': table_contents
            }]
        }
        return table

    @classmethod
    def __build_system_process_dashboard_element(cls) -> dict:
        """
        构造系统进程仪表板组件元素
        """
        return cls.__build_system_process_table_element(max_height='242px')

    def __get_system_process_dashboard(self) -> Optional[Tuple[Dict[str, Any], Dict[str, Any], List[dict]]]:
        """
        获取系统进程仪表板组件
        """
        # 列配置
        dashboard_widget_size = self.__get_config_item(config_key='dashboard_widget_size')
        cols = {
            'cols': 12,
            'xxl': dashboard_widget_size,
            'xl': dashboard_widget_size,
            'lg': dashboard_widget_size,
            'md': dashboard_widget_size,
            'sm': 12,
            'xs': 12
        }

        # 全局配置
        attrs = {
            'title': self.plugin_name
        }
        dashboard_widget_refresh = self.__get_config_item(config_key='dashboard_widget_refresh')
        if dashboard_widget_refresh:
            attrs['refresh'] = dashboard_widget_refresh

        # 页面元素
        elements = [self.__build_system_process_dashboard_element()]

        return cols, attrs, elements

