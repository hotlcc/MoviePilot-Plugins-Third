from typing import Any, List, Dict, Tuple, Set, Optional, Union
from threading import Event as ThreadEvent
from pydantic import BaseModel
from requests import Response
import re

from app.core.context import MediaInfo
from app.log import logger
from app.plugins.mediacollecthelper.favorites import Favorites
from app.plugins.mediacollecthelper.module import MediaDigest
from app.utils.http import RequestUtils
from app.schemas.types import MediaType


class Bookmark(BaseModel):
    """
    书签
    """
    url: str
    title: str = None
    description: str = None
    notes: str = None
    is_archived: bool = False
    unread: bool = False
    shared: bool = False
    tag_names: Optional[List[str]] = None


class LinkdingFavorites(Favorites):
    """
    Linkding 收藏夹
    """

    # 组件key
    comp_key: str = "linkding"
    # 组件名称
    comp_name: str = "Linkding"
    # 组件顺序
    comp_order: int = 1

    # 私有属性
    # 退出事件
    __exit_event: ThreadEvent = ThreadEvent()

    # 配置相关
    # 组件缺省配置
    __config_default: Dict[str, Any] = {
        # 记忆阈值
        "memory_threshold": 1000
    }

    # 媒体风格名称映射
    __media_genre_name_mappings = {
        "Sci-Fi & Fantasy": "科幻",
        "War & Politics": "战争"
    }

    def init_comp(self):
        """
        初始化组件
        """
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        获取组件的配置表单
        :return: 配置表单, 建议的配置
        """
        # 建议的配置
        config_suggest = {
            "custom_tags": "收藏",
            "generate_notes": True,
            "auto_tags": True,
        }
        # 合并默认配置
        config_suggest.update(self.__config_default)
        # elements
        row1 = {
            'component': 'VRow',
            'content': [{
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'url',
                        'label': '地址',
                        'placeholder': 'http://127.0.0.1:9090',
                        'hint': '必需。Linkding API 基础 URL，只需要配置到端口，不需要后面的“/api/***”。'
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
                        'model': 'token',
                        'label': 'Token',
                        'hint': '必需。配置 Linkding API 访问 Token。'
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
                        'model': 'custom_tags',
                        'label': '自定义标签',
                        'hint': '选填。添加Linkding书签时指定要添加的标签，多个用英文逗号“,”分隔。'
                    }
                }]
            }]
        }
        row2_content = [{
            'component': 'VCol',
            'props': {
                'cols': 12,
                'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
            },
            'content': [{
                'component': 'VSwitch',
                'props': {
                    'model': 'mark_unread',
                    'label': '标记未读',
                    'hint': '添加时是否将书签标记为未读。'
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
                    'model': 'generate_notes',
                    'label': '生成备注',
                    'hint': '添加时是否为书签生成备注。'
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
                    'model': 'auto_tags',
                    'label': '自动标签',
                    'hint': '启用后将自动添加影视类型标签。'
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
                    'model': 'full_coverage',
                    'label': '全量覆盖',
                    'hint': f'启用后仅在下一次任务时生效一次，生效时会全量覆盖一次历史记录。否则，正常情况下每次只会增量添加。'
                }
            }]
        }]
        row2 = {
            'component': 'VRow',
            'content': row2_content
        }   
        row3 = {
            'component': 'VRow',
            'content': [{
                'component': 'VCol',
                'props': {
                    'cols': 12
                },
                'content': [{
                    'component': 'VAlert',
                    'props': {
                        'type': 'info',
                        'variant': 'tonal'
                    },
                    'content': [{
                        'component': 'a',
                        'props': {
                            'href': 'https://github.com/sissbruecker/linkding',
                            'target': '_blank'
                        },
                        'text': '点击这里了解什么是Linkding？'
                    }]
                }]
            }]
        }
        elements = [row1, row2, row3]
        return elements, config_suggest

    def stop_service(self):
        """
        停止组件
        """
        try:
            logger.info('尝试停止停止组件...')
            self.__exit_event.set()
            logger.info('组件停止完成')
        except Exception as e:
            logger.error(f"组件停止异常: {str(e)}", exc_info=True)

    def collect(self, media_data: List[MediaDigest]) -> List[MediaDigest]:
        """
        收藏影视
        """
        media_data = media_data or []
        total = len(media_data)
        # 全量覆盖
        full_coverage = True if self.__check_full_coverage() else False
        if not self.__check_config():
            logger.warn(f"收藏影视前: 配置检查不通过")
            return
        logger.info(f"收藏影视前: total = {total}, full_coverage = {full_coverage}")
        # 记忆阈值
        memory_threshold = self.get_config_item(config_key="memory_threshold") or 1000
        # 记忆
        memory = self.__get_memory()
        if self.__exit_event.is_set():
            logger.warn('运行任务中止: 组件正在退出')
            return []
        # 全量覆盖时不做历史存在性判断
        if full_coverage:
            logger.info(f"收藏影视前: 本次全量覆盖生效")
            if self.__exit_event.is_set():
                logger.warn('运行任务中止: 组件正在退出')
                return []
            linkding_exists_media_unique_keys = self.__get_linkding_exists_media_unique_keys()
            logger.info(f"收藏影视前: 检索到Linkding中已有{len(linkding_exists_media_unique_keys)}个收藏")
            linkding_exists = self.__build_medias_by_unique_keys(unique_keys=linkding_exists_media_unique_keys)
            media_data = media_data + linkding_exists
            if self.__exit_event.is_set():
                logger.warn('运行任务中止: 组件正在退出')
                return []
            media_data = self.distinct_media_digests(media_data=media_data)
            logger.info(f"收藏影视前: 合并本次和已有数据去重后共{len(media_data)}个需要收藏")
            if self.__exit_event.is_set():
                logger.warn('运行任务中止: 组件正在退出')
                return []
            success_list = self.__collect(media_data=media_data)
            logger.info(f"收藏影视后: 本次成功收藏{len(success_list)}个")
            # 如果数量超过阈值就保存记忆
            if len(success_list) > memory_threshold:
                success_media_unique_keys = self.__build_media_unique_keys_by_media(media_data=success_list)
                self.__save_memory(memory=success_media_unique_keys)
                logger.info(f"收藏影视后: 本次收藏数量超过记忆阈{memory_threshold}，保存了{len(success_media_unique_keys)}个记忆")
            # 否则如果先前有记忆，就重置记忆
            elif memory:
                self.__reset_memory()
                logger.info(f"收藏影视后: 本次收藏数量未超过记忆阈{memory_threshold}，重置记忆完成")
            return success_list
        # 数量少时不做历史存在性判断
        if total <= 10:
            logger.info(f"收藏影视前: 本次数量少（不超过10），直接收藏")
            if self.__exit_event.is_set():
                logger.warn('运行任务中止: 组件正在退出')
                return []
            success_list = self.__collect(media_data=media_data)
            logger.info(f"收藏影视后: 本次成功收藏{len(success_list)}个")
            # 如果先前有记忆，本次需要追加记忆
            if memory:
                success_media_unique_keys = self.__build_media_unique_keys_by_media(media_data=success_list)
                self.__add_memory(memory=success_media_unique_keys)
                logger.info(f"收藏影视后: 追加了{len(success_media_unique_keys)}个记忆")
            return success_list
        # 如果先前有记忆，则通过记忆判断是否已经添加
        if memory:
            media_data = [mdata for mdata in media_data if mdata and mdata.tmdb_id and self.__build_media_unique_key_by_media(media_data=mdata) not in memory]
            logger.info(f"收藏影视前: 根据记忆进行存在性过滤后还有{len(media_data)}个需要收藏")
            if self.__exit_event.is_set():
                logger.warn('运行任务中止: 组件正在退出')
                return []
            success_list = self.__collect(media_data=media_data)
            logger.info(f"收藏影视后: 本次成功收藏{len(success_list)}个")
            success_media_unique_keys = self.__build_media_unique_keys_by_media(media_data=success_list)
            self.__add_memory(memory=set(success_media_unique_keys))
            logger.info(f"收藏影视后: 追加了{len(success_media_unique_keys)}个记忆")
            return success_list
        # 如果先前没有记忆则通过检索linkding判断
        else:
            if self.__exit_event.is_set():
                logger.warn('运行任务中止: 组件正在退出')
                return []
            linkding_exists_media_unique_keys = self.__get_linkding_exists_media_unique_keys()
            logger.info(f"收藏影视前: 检索到Linkding中已有{len(linkding_exists_media_unique_keys)}个收藏")
            media_data = [mdata for mdata in media_data if mdata and mdata.tmdb_id and self.__build_media_unique_key_by_media(media_data=mdata) not in linkding_exists_media_unique_keys]
            logger.info(f"收藏影视前: 根据Linkding检索结果进行存在性过滤后还有{len(media_data)}个需要收藏")
            if self.__exit_event.is_set():
                logger.warn('运行任务中止: 组件正在退出')
                return []
            success_list = self.__collect(media_data=media_data)
            logger.info(f"收藏影视后: 本次成功收藏{len(success_list)}个")
            # 如果linkding中总数超过阈值就放到记忆中
            linkding_count = len(linkding_exists_media_unique_keys) + len(success_list)
            if linkding_count > memory_threshold:
                success_media_unique_keys = self.__build_media_unique_keys_by_media(media_data=success_list)
                init_memory = set(list(success_media_unique_keys) + list(linkding_exists_media_unique_keys))
                self.__save_memory(memory=init_memory)
                logger.info(f"收藏影视后: 本次收藏后累计数量超过记忆阈{memory_threshold}，初始化了{len(init_memory)}个记忆")
            return success_list

    def __reset_memory(self):
        """
        重置记忆
        """
        self.del_data(key="memory")

    def __save_memory(self, memory: Set[str]):
        """
        保存记忆
        """
        memory = list(memory) if memory else []
        self.save_data(key="memory", value=memory)

    def __add_memory(self, memory: Set[str]):
        """
        添加记忆
        """
        old_memory = self.__get_memory() or set()
        if memory:
            old_memory.update(memory)
            self.__save_memory(memory=old_memory)
        return old_memory

    def __get_memory(self) -> Set[str]:
        """
        获取记忆
        """
        memory = self.get_data(key="memory")
        if not memory:
            return set()
        return set(memory)

    def __check_full_coverage(self) -> bool:
        """
        判断是否开启了全量覆盖，返回并重置
        """
        config = self.get_config() or {}
        full_coverage = config.get("full_coverage")
        if full_coverage:
            config["full_coverage"] = False
            self.update_config(config)
            return True
        return False

    def __check_config(self) -> bool:
        """
        检查配置
        """
        config = self.get_config() or {}
        url = config.get("url")
        if not url:
            logger.error(f"{self.comp_name} - 配置检查不通过: 地址必填")
            return False
        token = config.get("token")
        if not token:
            logger.error(f"{self.comp_name} - 配置检查不通过: Token必填")
            return False
        return True

    @classmethod
    def __linkding_build_authorization_header(cls, token: str) -> str:
        """
        构造 Linkding Token header 值
        """
        if not token:
            return None
        return f'Token {token}'

    @classmethod
    def __linkding_api_check_response(cls, response: Optional[Response]) -> Tuple[bool, str]:
        """
        检查响应
        """
        if not response:
            raise Exception("Linkding接口响应超时")
        if not response.ok:
            raise Exception(f"Linkding接口响应错误码[{response.status_code}]")
        return True, None

    def __linkding_api_save_bookmark(self, base_url: str, token: str, bookmark: Bookmark) -> Tuple[bool, str]:
        """
        Linkding保存书签
        """
        if not base_url:
            return False, "参数错误[base_url]"
        if not token:
            return False, "参数错误[token]"
        if not bookmark:
            return False, "参数错误[bookmark]"
        if not bookmark.url:
            return False, "书签信息有误"
        if self.__exit_event.is_set():
            logger.warn('运行任务中止: 组件正在退出')
            return False, "组件正在退出"
        url = f"{base_url}/api/bookmarks/"
        authorization = self.__linkding_build_authorization_header(token=token)
        response = RequestUtils(
            headers={
                "Authorization": authorization
            },
            timeout=60
        ).post_res(url=url, json=bookmark.dict(exclude_none=True))
        return self.__linkding_api_check_response(response=response)

    def __linkding_api_search_bookmarks(self, base_url: str, token: str, search_str: str) -> Tuple[bool, str, Optional[List[Bookmark]]]:
        """
        Linkding搜索书签
        """
        if not base_url:
            return False, "参数错误[base_url]", None
        if not token:
            return False, "参数错误[token]", None
        authorization = self.__linkding_build_authorization_header(token=token)
        url = f"{base_url}/api/bookmarks/"
        bookmarks: List[Bookmark] = []
        for offset in range(10000):
            response = RequestUtils(
                headers={
                    "Authorization": authorization
                },
                timeout=60
            ).get_res(url=url, params={
                "q": search_str,
                "limit": 1000,
                "offset": offset
            })
            success, error_msg = self.__linkding_api_check_response(response=response)
            if not success:
                return success, error_msg, None
            res_json: dict = response.json()
            if not res_json:
                break
            results: List[dict] = res_json.get("results")
            if not results:
                break
            for result in results:
                if result:
                    bookmarks.append(Bookmark(**result))
            next = res_json.get("next")
            if not next:
                break
        return True, None, bookmarks

    def __get_linkding_exists_media_unique_keys(self) -> Set[str]:
        """
        获取linkding中已经存在的媒体唯一键集合
        """
        url = self.get_config_item(config_key="url")
        token = self.get_config_item(config_key="token")
        search_str = f"https://www.themoviedb.org/ #影视 #TMDB"
        success, error_msg, boomarks = self.__linkding_api_search_bookmarks(base_url=url, token=token, search_str=search_str)
        if not success:
            raise Exception(error_msg)
        result: Set[str] = set()
        if boomarks:
            for boomark in boomarks:
                if not boomark or not boomark.url:
                    continue
                url_arr = boomark.url.strip("/").split("/")
                if len(url_arr) < 2:
                    continue
                media_unique_key = self.__build_media_unique_key(platform="tmdb", media_type=url_arr[-2], platform_id=url_arr[-1])
                result.add(media_unique_key)
        return result

    @classmethod
    def __build_media_unique_key(cls, platform: str, media_type: Union[MediaType, str], platform_id) -> Optional[str]:
        """
        构造媒体唯一键
        :param platform: tmdb|imdb|tvdb|douban
        :param media_type: 媒体类型
        :param platform_id: 平台ID，tmdb_id、douban_id等
        """
        if not platform or not media_type or not platform_id:
            return None
        if isinstance(media_type, MediaType):
            media_type = media_type.name
        if isinstance(media_type, str):
            if media_type in MediaType._value2member_map_.keys():
                media_type = MediaType(media_type).name
            media_type = media_type.lower()
        return f"{platform}:{media_type}:{platform_id}"

    @classmethod
    def __build_media_unique_key_by_media(cls, media_data: Optional[MediaDigest]) -> Optional[str]:
        """
        根据媒体信息构造媒体唯一键
        """
        if not media_data:
            return None
        return cls.__build_media_unique_key(platform="tmdb", media_type=media_data.type, platform_id=media_data.tmdb_id)

    @classmethod
    def __build_media_unique_keys_by_media(cls, media_data: Optional[List[MediaDigest]]) -> Set[str]:
        """
        根据媒体信息构造媒体唯一键
        """
        if not media_data:
            return set()
        media_unique_keys = [cls.__build_media_unique_key_by_media(media_data=item) for item in media_data if item and item.type and item.tmdb_id]
        return set(media_unique_keys)

    @classmethod
    def __build_media_by_unique_key(cls, unique_key: str) -> Optional[MediaDigest]:
        """
        根据unique_key生成媒体信息
        """
        if not unique_key:
            return None
        unique_key_arr = unique_key.split(":")
        if len(unique_key_arr) != 3:
            return None
        _, media_type, platform_id = unique_key_arr
        if not media_type or not platform_id:
            return None
        media_type = MediaType._member_map_.get(media_type.upper())
        if not media_type:
            return None
        return MediaDigest(type=media_type, tmdb_id=platform_id)

    @classmethod
    def __build_medias_by_unique_keys(cls, unique_keys: Set[str]) -> List[MediaDigest]:
        """
        根据unique_key生成媒体信息
        """
        result: List[MediaDigest] = []
        if not unique_keys:
            return result
        for unique_key in unique_keys:
            media = cls.__build_media_by_unique_key(unique_key=unique_key)
            if media:
                result.append(media)
        return result

    def __build_bookmark_by_media_info(self, media_info: MediaInfo,
                                       generate_notes: bool,
                                       custom_tags: List[str],
                                       auto_tags: bool,
                                       mark_unread: bool) -> Optional[Bookmark]:
        """
        根据媒体信息构造书签信息
        """
        if not media_info or not media_info.detail_link:
            return None
        # 书签
        bookmark = Bookmark(url=media_info.detail_link)
        bookmark.title = self.__build_bookmark_title_by_media_info(media_info=media_info)
        bookmark.description = media_info.overview
        if generate_notes:
            bookmark.notes = self.__build_bookmark_markdown_notes_by_media_info(media_info=media_info, auto_tags=auto_tags)
        bookmark.unread = mark_unread
        if auto_tags or custom_tags:
            bookmark.tag_names = self.__build_bookmark_tags_by_media_info(media_info=media_info, custom_tags=custom_tags, auto_tags=auto_tags)
        return bookmark

    def __get_config_of_custom_tags_list(self) -> List[str]:
        """
        获取自定义标签list
        """
        custom_tags_str = self.get_config_item(config_key="custom_tags")
        return re.split("\s*,\s*", custom_tags_str.strip()) if custom_tags_str else []

    def __build_bookmark_title_by_media_info(self, media_info: MediaInfo) -> Bookmark:
        """
        根据媒体信息构造书签标题
        """
        if not media_info or not media_info.title:
            return None
        if media_info.year:
            return f"{media_info.title} ({media_info.year}) — The Movie Database (TMDB)"
        else:
            return f"{media_info.title} — The Movie Database (TMDB)"

    def __build_bookmark_markdown_notes_by_media_info(self, media_info: MediaInfo,
                                                      auto_tags: bool) -> Bookmark:
        """
        根据媒体信息构造书签markdown备注
        """
        if not media_info or not media_info.title:
            return None
        notes = f"**名称:** {media_info.title}\n"
        if media_info.original_title != media_info.title:
            notes += f"**别名:** {media_info.original_title}\n"
        if media_info.year:
            notes += f"**年份:** {media_info.year}\n"
        if media_info.vote_average:
            notes += f"**评分:** {media_info.vote_average}\n"
        if media_info.runtime:
            notes += f"**时长:** {media_info.runtime}\n"
        if media_info.type or media_info.category:
            type_category = self.__build_bookmark_markdown_notes_type_category_by_media_info(media_info=media_info, auto_tags=auto_tags)
            notes += f"**类型:** {type_category}\n"
        if media_info.genres:
            genres = self.__build_bookmark_markdown_notes_genres_by_media_info(media_info=media_info, auto_tags=auto_tags)
            notes += f"**风格:** {genres}\n"
        if media_info.directors:
            directors = self.__build_bookmark_markdown_notes_directors_by_media_info(media_info=media_info)
            if directors:
                notes += f"**导演:** {directors}\n"
        if media_info.actors:
            actors = self.__build_bookmark_markdown_notes_actors_by_media_info(media_info=media_info)
            if actors:
                notes += f"**演员:** {actors}\n"
        links = self.__build_bookmark_markdown_notes_links_by_media_info(media_info=media_info)
        if links:
           notes += f"**链接:** {links}\n"
        return notes

    @classmethod
    def __build_markdown_link(cls, text: str, url: str) -> str:
        """
        生成markdown链接
        """
        if not text:
            return None
        if not url:
            return text
        return f"[{text}]({url})"

    def __build_bookmark_notes_tag_markdown_link(self, text: str) -> str:
        """
        生成书签标签markdown链接
        """
        return self.__build_markdown_link(text=text, url=f"?q=%23{text}")

    def __build_bookmark_markdown_notes_type_category_by_media_info(self, media_info: MediaInfo,
                                                                    auto_tags: bool) -> str:
        """
        生成类型
        """
        if not media_info:
            return None
        type_category = []
        if media_info.type:
            type_category.append(media_info.type.value)
        if media_info.category:
            type_category.append(media_info.category)
        if not type_category:
            return None
        if auto_tags:
            type_category = [self.__build_bookmark_notes_tag_markdown_link(text=item) for item in type_category if item]
        return " · ".join(type_category)

    def __build_bookmark_markdown_notes_genres_by_media_info(self, media_info: MediaInfo,
                                                             auto_tags: bool) -> str:
        """
        生成风格
        """
        if not media_info or not media_info.genres:
            return None
        genre_names = [self.__mapping_media_genre_name(genre_name=genre.get("name")) for genre in media_info.genres if genre and genre.get("name")]
        if not genre_names:
            return None
        if auto_tags:
            genre_names = [self.__build_bookmark_notes_tag_markdown_link(text=item) for item in genre_names if item]
        return " | ".join(genre_names)

    @classmethod
    def __mapping_media_genre_name(cls, genre_name: str) -> str:
        """
        映射媒体风格名称
        """
        if not genre_name:
            return None
        mapping_name = cls.__media_genre_name_mappings.get(genre_name)
        return mapping_name or genre_name

    def __build_bookmark_markdown_notes_directors_by_media_info(self, media_info: MediaInfo) -> str:
        """
        生成导演
        """
        if not media_info or not media_info.directors:
            return None
        director_names = [director.get("name") for director in media_info.directors if director and director.get("name") and director.get("job") == "Director"]
        if not director_names:
            return None
        return " | ".join(director_names)

    def __build_bookmark_markdown_notes_actors_by_media_info(self, media_info: MediaInfo) -> str:
        """
        生成演员
        """
        if not media_info or not media_info.actors:
            return None
        actor_names = [actor.get("name") for actor in media_info.actors if actor and actor.get("name")]
        if not actor_names:
            return None
        return " | ".join(actor_names)

    def __build_bookmark_markdown_notes_links_by_media_info(self, media_info: MediaInfo) -> str:
        """
        生成链接
        """
        if not media_info:
            return None
        links = []
        if media_info.source == "themoviedb" and media_info.tmdb_id and media_info.detail_link:
            links.append(self.__build_markdown_link(text="TMDB", url=media_info.detail_link))
        if media_info.imdb_id:
            links.append(self.__build_markdown_link(text="IMDB", url=f"https://www.imdb.com/title/{media_info.imdb_id}"))
        if media_info.tvdb_id:
            links.append(self.__build_markdown_link(text="TVDB", url=f"https://www.thetvdb.com/series/{media_info.tvdb_id}"))
        if media_info.source == "douban" and media_info.douban_id and media_info.detail_link:
            links.append(self.__build_markdown_link(text="豆瓣", url=media_info.detail_link))
        return " | ".join(links)

    def __build_bookmark_tags_by_media_info(self, media_info: MediaInfo,
                                            custom_tags: List[str],
                                            auto_tags: bool) -> List[str]:
        """
        生成标签
        """
        if not media_info:
            return None
        if not custom_tags and not auto_tags:
            return None
        tags = set(["影视", "TMDB"])
        if custom_tags:
            tags.update(custom_tags)
        if auto_tags:
            if media_info.type:
                tags.add(media_info.type.value)
            if media_info.category:
                tags.add(media_info.category)
            if media_info.genres:
                for genre in media_info.genres:
                    if not genre:
                        continue
                    genre_name = genre.get("name")
                    if genre_name:
                        tags.add(self.__mapping_media_genre_name(genre_name=genre_name))
        return list(tags)

    def __collect(self, media_data: List[MediaDigest]) -> List[MediaDigest]:
        """
        收藏影视
        """
        success_list: List[MediaDigest] = []
        if not media_data:
            return success_list
        total = len(media_data)
        logger.info(f"{self.comp_name} - 影视收藏开始: total = {total}")
        # 处理配置
        generate_notes = True if self.get_config_item(config_key="generate_notes") else False
        auto_tags = True if self.get_config_item(config_key="auto_tags") else False
        mark_unread = True if self.get_config_item(config_key="mark_unread") else False
        custom_tags = self.__get_config_of_custom_tags_list()
        url = self.get_config_item(config_key="url")
        token = self.get_config_item(config_key="token")
        try:
            for mdata in media_data:
                if self.__exit_event.is_set():
                    logger.warn('运行任务中止: 组件正在退出')
                    return success_list
                success = self.__collect_single(media_data=mdata,
                                                generate_notes=generate_notes,
                                                custom_tags=custom_tags,
                                                auto_tags=auto_tags,
                                                mark_unread=mark_unread,
                                                linkding_base_url=url,
                                                linkding_token=token)
                if success:
                    success_list.append(mdata)
            logger.info(f"{self.comp_name} - 影视收藏完成: total = {total}, success = {len(success_list)}")
        except Exception as e:
            logger.error(f"{self.comp_name} - 影视收藏失败: {str(e)}", exc_info=True)
        return success_list

    def __collect_single(self, media_data: Optional[MediaDigest],
                         generate_notes: bool,
                         custom_tags: List[str],
                         auto_tags: bool,
                         mark_unread: bool,
                         linkding_base_url: str,
                         linkding_token: str) -> bool:
        """
        收藏单个
        """
        if not media_data or not media_data.tmdb_id or not media_data.type:
            logger.error(f"{self.comp_name} - 单个影视收藏失败: 影视信息不完整, media_data = {media_data.dict() if media_data else None}")
            return False
        if self.__exit_event.is_set():
            logger.warn('运行任务中止: 组件正在退出')
            return False
        media_info: Optional[MediaInfo] = self.recognize_media_info(media_data=media_data)
        if not media_info:
            logger.error(f"{self.comp_name} - 单个影视收藏失败: 未识别到媒体, title = {media_data.title}, year = {media_data.year}, type = {media_data.type}, tmdb_id = {media_data.tmdb_id}")
            return False
        if self.__exit_event.is_set():
            logger.warn('运行任务中止: 组件正在退出')
            return False
        bookmark: Optional[Bookmark] = self.__build_bookmark_by_media_info(media_info=media_info,
                                                                           generate_notes=generate_notes,
                                                                           custom_tags=custom_tags,
                                                                           auto_tags=auto_tags,
                                                                           mark_unread=mark_unread)
        if not bookmark:
            return False
        if self.__exit_event.is_set():
            logger.warn('运行任务中止: 组件正在退出')
            return False
        success, error_msg = self.__linkding_api_save_bookmark(base_url=linkding_base_url, token=linkding_token, bookmark=bookmark)
        if not success:
            logger.error(f"{self.comp_name} - 单个影视收藏失败: {error_msg}, title = {media_info.title}, year = {media_info.year}, type = {media_info.type}, tmdb_id = {media_info.tmdb_id}")
            return False
        logger.info(f"{self.comp_name} - 单个影视收藏成功: title = {media_info.title}, year = {media_info.year}, type = {media_info.type}, tmdb_id = {media_info.tmdb_id}")
        return True
