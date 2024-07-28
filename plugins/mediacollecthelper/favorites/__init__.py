from abc import ABCMeta, abstractmethod
from typing import Any, List, Dict, Tuple, Optional
from cachetools import cached, TTLCache

from app.chain.media import MediaChain
from app.core.context import MediaInfo
from app.log import logger
from app.plugins import _PluginBase
from app.plugins.mediacollecthelper.module import MediaDigest
from app.schemas.types import MediaType


class Favorites(metaclass=ABCMeta):
    """
    收藏夹组件基类
    """

    # 组件key：取组件类名去除Favorites后缀后的小写
    comp_key: str = ""
    # 组件名称
    comp_name: str = ""

    # 配置相关
    # 组件缺省配置
    __config_default: Dict[str, Any] = {}

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
        config_default = self.__config_default or {}
        config_value = config.get(config_key)
        if config_value is None and use_default:
            config_value = config_default.get(config_key)
        return config_value

    def __build_plugin_data_key(self, key: str) -> str:
        """
        根据组件数据kee构造插件数据key
        """
        if not key:
            return None
        return f"comp-data.{self.comp_key}.{key}"

    def save_data(self, key: str, value: Any):
        """
        保存组件数据
        :param key: 数据key
        :param value: 数据值
        """
        if not key:
            logger.warn(f"{self.comp_name} - 保存组件数据 - 中止: 参数key无效")
            return
        try:
            plugin_data_key = self.__build_plugin_data_key(key=key)
            self.__plugin.save_data(key=plugin_data_key, value=value)
            logger.debug(f"{self.comp_name} - 保存组件数据 - 成功: key = {key}, value = {str(value)}")
        except Exception as e:
            logger.error(f"{self.comp_name} - 保存组件数据 - 异常: {str(e)}, key = {key}, value = {str(value)}", exc_info=True)
            raise e

    def get_data(self, key: str = None) -> Any:
        """
        获取组件数据
        :param key: 数据key
        """
        if not key:
            logger.warn(f"{self.comp_name} - 获取组件数据 - 中止: 参数key无效")
            return None
        try:
            plugin_data_key = self.__build_plugin_data_key(key=key)
            value = self.__plugin.get_data(key=plugin_data_key)
            logger.debug(f"{self.comp_name} - 获取组件数据 - 成功: key = {key}, value = {str(value)}")
            return value
        except Exception as e:
            logger.error(f"{self.comp_name} - 获取组件数据 - 异常: {str(e)}, key = {key}", exc_info=True)
            raise e

    def del_data(self, key: str, plugin_id: str = None) -> Any:
        """
        删除组件数据
        :param key: 数据key
        """
        if not key:
            logger.warn(f"{self.comp_name} - 删除组件数据 - 中止: 参数key无效")
            return None
        try:
            plugin_data_key = self.__build_plugin_data_key(key=key)
            value = self.__plugin.del_data(key=plugin_data_key)
            logger.debug(f"{self.comp_name} - 删除组件数据 - 成功: key = {key}, value = {str(value)}")
            return value
        except Exception as e:
            logger.error(f"{self.comp_name} - 删除组件数据 - 异常: {str(e)}, key = {key}", exc_info=True)
            raise e

    def distinct_media_digests(self, media_data: List[MediaDigest]) -> List[MediaDigest]:
        """
        媒体摘要去重
        """
        result: List[MediaDigest] = []
        if not media_data:
            return result
        tmdb_ids = set()
        for md in media_data:
            if not md or not md.tmdb_id or md.tmdb_id in tmdb_ids:
                continue
            result.append(md)
            tmdb_ids.add(md.tmdb_id)
        return result

    def recognize_media_info(self, media_data: MediaDigest) -> Optional[MediaInfo]:
        """
        识别媒体信息
        """
        if not media_data:
            return None
        media_info =  self.recognize_media_info_by_tmdb(media_type=media_data.type, tmdb_id=media_data.tmdb_id)
        if not media_info:
            logger.warn(f"{self.comp_name} - 未识别到媒体信息: tmdb_id = {media_data.tmdb_id}, type = {media_data.type}, title = {media_data.title}, year = {media_data.year}")
        return media_info

    @cached(cache=TTLCache(maxsize=10000, ttl=600))
    def recognize_media_info_by_tmdb(self, media_type: MediaType, tmdb_id: str) -> Optional[MediaInfo]:
        """
        根据tmdb识别媒体信息
        """
        if not media_type or not tmdb_id:
            return None
        return MediaChain().recognize_media(tmdbid=tmdb_id, mtype=media_type)

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
    def stop_service(self):
        """
        停止组件
        """
        pass

    @abstractmethod
    def collect(self, media_data: List[MediaDigest]) -> List[MediaDigest]:
        """
        收藏影视
        :return: 本次新收藏的影视信息
        """
        pass
