from typing import Dict, Any, Optional, List, Tuple
import asyncio
# noinspection PyPackageRequirements
from icalendar import Calendar, Event, vDate
from datetime import datetime, timedelta
import pytz
from fastapi.responses import StreamingResponse
import io

from app.core.config import settings
from app.chain.media import MediaChain
from app.chain.tmdb import TmdbChain
from app.core.context import MediaInfo
from app.db.models.subscribe import Subscribe
from app.plugins import _PluginBase
from app.schemas import MediaType
from app.schemas.tmdb import TmdbEpisode


class SubscribeCalendarIcs(_PluginBase):
    # 插件名称
    plugin_name = "订阅日历.ics"
    # 插件描述
    plugin_desc = "提供ics订阅日历订阅链接。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/hotlcc/MoviePilot-Plugins-Third/main/icons/SubscribeCalendarIcs.png"
    # 插件版本
    plugin_version = "1.0.2"
    # 插件作者
    # noinspection SpellCheckingInspection
    plugin_author = "hotlcc"
    # 作者主页
    author_url = "https://github.com/hotlcc"
    # 插件配置项ID前缀
    # noinspection SpellCheckingInspection
    plugin_config_prefix = "com.hotlcc.subscribecalendarics."
    # 加载顺序
    plugin_order = 66
    # 可使用的用户级别
    auth_level = 1

    # 依赖组件
    # 媒体链
    __media_chain: MediaChain = MediaChain()
    # TMDB链
    __tmdb_chain: TmdbChain = TmdbChain()

    # 常量
    __calendar_ics_endpoint = "/calendar.ics"

    # 配置相关
    # 插件缺省配置
    __config_default: Dict[str, Any] = {}
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
        calendar_ics_api = {
            "path": self.__calendar_ics_endpoint,
            "endpoint": self.__calendar_ics,
            "methods": ["GET"],
            "auth": "apikey",
            "summary": "获取日历ics数据",
            "description": "获取日历ics数据"
        }
        return [calendar_ics_api]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        插件配置页面使用Vuetify组件拼装，参考：https://vuetifyjs.com/
        """
        # 建议的配置
        config_suggest = {}
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
                            'hint': '插件总开关。'
                        }
                    }]
                }]
            }]
        }]
        return form_content, config_suggest

    # noinspection SpellCheckingInspection
    def get_page(self) -> Optional[List[dict]]:
        """
        拼装插件详情页面，需要返回页面配置，同时附带数据
        插件详情页面使用Vuetify组件拼装，参考：https://vuetifyjs.com/
        """
        if not self.get_state():
            return [{
                'component': 'VRow',
                'content': [{
                    'component': 'VCol',
                    'props': {
                        'cols': 12,
                        'xxl': 12, 'xl': 12, 'lg': 12, 'md': 12, 'sm': 12, 'xs': 12
                    },
                    'content': [{
                        'component': 'h2',
                        'text': '请先启用插件'
                    }]
                }, {
                    'component': 'VCol',
                    'props': {
                        'cols': 12,
                        'xxl': 12, 'xl': 12, 'lg': 12, 'md': 12, 'sm': 12, 'xs': 12
                    },
                    'content': [{
                        'component': 'div',
                        'text': '您在启用插件后可返回此处查看订阅链接。'
                    }]
                }]
            }]
        app_domain = settings.APP_DOMAIN or 'http://localhost:5173'
        sub_url = f"{app_domain}/api/v1/plugin/{SubscribeCalendarIcs.__name__}{self.__calendar_ics_endpoint}?apikey={settings.API_TOKEN}"
        return [{
                'component': 'VRow',
                'content': [{
                    'component': 'VCol',
                    'props': {
                        'cols': 12,
                        'xxl': 12, 'xl': 12, 'lg': 12, 'md': 12, 'sm': 12, 'xs': 12
                    },
                    'content': [{
                        'component': 'h2',
                        'text': '订阅地址'
                    }]
                }, {
                    'component': 'VCol',
                    'props': {
                        'cols': 12,
                        'xxl': 12, 'xl': 12, 'lg': 12, 'md': 12, 'sm': 12, 'xs': 12
                    },
                    'content': [{
                        'component': 'div',
                        'text': sub_url
                    }]
                }]
            }]

    def stop_service(self):
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

    @staticmethod
    def __fix_config(config: dict) -> dict | None:
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

    async def __get_movie_info_async(self, sub: Subscribe) -> Tuple[MediaInfo, None]:
        """
        异步获取电影信息
        """
        media_info = await self.__media_chain.async_recognize_media(tmdbid=sub.tmdbid, doubanid=sub.doubanid, bangumiid=sub.bangumiid, mtype=MediaType.MOVIE)
        return media_info, None

    async def __get_tv_info_async(self, sub: Subscribe) -> Tuple[MediaInfo, Optional[List[TmdbEpisode]]]:
        """
        异步获取电视剧信息
        """
        media_info = MediaInfo(type=MediaType.TV, title=sub.name, tmdb_id=sub.tmdbid, douban_id=sub.doubanid, bangumi_id=sub.bangumiid, season=sub.season)
        if not sub.tmdbid or not sub.season:
            return media_info, None
        episode_list = await self.__tmdb_chain.async_tmdb_episodes(tmdbid=sub.tmdbid, season=sub.season)
        return media_info, episode_list

    async def __get_calendar_data(self) -> Optional[List[dict]]:
        """
        获取日历数据
        """
        subs = Subscribe.list()
        if not subs:
            return None
        # 异步任务集合
        async_tasks = []
        for sub in subs:
            if not sub:
                continue
            media_type = MediaType(sub.type) if sub.type else MediaType.UNKNOWN
            if MediaType.MOVIE == media_type:
                async_tasks.append(asyncio.create_task(self.__get_movie_info_async(sub=sub)))
            elif MediaType.TV == media_type:
                async_tasks.append(asyncio.create_task(self.__get_tv_info_async(sub=sub)))
        if not async_tasks:
            return None
        # 异步任务结果
        async_results: List[Tuple[MediaInfo, Optional[List[TmdbEpisode]]]] = await asyncio.gather(*async_tasks, return_exceptions=True)
        if not async_results:
            return None
        # 日历数据
        calendar_data = []
        for async_result in async_results:
            if not async_result:
                continue
            media_info, detail = async_result
            if not media_info or not media_info.type or not media_info.title:
                continue
            if MediaType.MOVIE == media_info.type:
                if not media_info.release_date:
                    continue
                calendar_data.append({
                    "title": media_info.title,
                    "date": media_info.release_date,
                    "link": media_info.detail_link,
                    "uid": f"{media_info.tmdb_id or media_info.douban_id or media_info.bangumi_id}",
                })
            elif MediaType.TV == media_info.type:
                group_by_date = {}
                for episode in detail:
                    if not episode or not episode.air_date or not episode.episode_number:
                        continue
                    episode_numbers = group_by_date.get(episode.air_date) or []
                    episode_numbers.append(episode.episode_number)
                    group_by_date[episode.air_date] = episode_numbers
                for air_date, episode_numbers in group_by_date.items():
                    title = media_info.title
                    if len(episode_numbers) <= 1:
                        title += f" 第{episode_numbers[0]}集"
                    else:
                        title += f" 第{min(episode_numbers)}-{max(episode_numbers)}集"
                    calendar_data.append({
                        "title": title,
                        "date": air_date,
                        "link": media_info.detail_link,
                        "uid": f"{media_info.tmdb_id or media_info.douban_id or media_info.bangumi_id}:{media_info.season}:{air_date}",
                    })
        return calendar_data

    # noinspection SpellCheckingInspection
    def __calendar_ics(self, apikey: str = None):
        """
        日历ics数据
        """
        cal = Calendar()
        cal.add('VERSION', '2.0')
        cal.add('PRODID', '-//SubscribeCalendarIcs//github.com/hotlcc//CN')
        cal.add('X-WR-CALNAME','MoviePilot订阅')
        cal.add('X-APPLE-CALENDAR-COLOR','#9b75ef')
        if apikey == settings.API_TOKEN and self.get_state():
            calendar_data = asyncio.run(self.__get_calendar_data())
            if calendar_data:
                tz = pytz.timezone('Asia/Shanghai')
                now = datetime.now(tz)
                for data in calendar_data:
                    if not data or not data.get('title') or not data.get('uid') or not data.get('date'):
                        continue
                    start_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
                    end_date = start_date + timedelta(days=1)
                    event = Event()
                    event.add('SUMMARY', data.get('title'))
                    event.add('UID', data.get('uid'))
                    event.add('DTSTART',vDate(start_date))
                    event.add('DTEND', vDate(end_date))
                    event.add('URL', data.get('link'))
                    event.add('DTSTAMP', now)
                    event.add('CREATED', now)
                    event.add('LAST-MODIFIED', now)
                    cal.add_component(event)
        byte_stream = io.BytesIO(cal.to_ical())
        return StreamingResponse(
            content=byte_stream,
            media_type="text/calendar"
        )
