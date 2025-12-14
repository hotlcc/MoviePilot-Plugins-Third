from cachetools import Cache
from enum import Enum
from pydantic import BaseModel
from threading import RLock

from app.schemas.types import MediaType


class MediaDigest(BaseModel):
    """
    媒体摘要
    """
    title: str = None
    year: str = None
    type: MediaType = None
    tmdb_id: str = None
    imdb_id: str = None
    tvdb_id: str = None


class MediaDataSource(Enum):
    """
    影视数据来源
    """
    MEDIA_LIBRARY = "媒体库"
    SUBSCRIBE = "订阅"
    SUBSCRIBE_HISTORY = "订阅历史"


class AtomicCache():
    """
    原子缓存操作（线程安全）
    """

    # 锁
    __lock: RLock = None
    # 真实缓存
    __cache: Cache = None

    def __init__(self, cache: Cache):
        """
        """
        if cache is None:
            raise Exception("Param 'cache' cannot be None.")
        self.__lock: RLock = RLock()
        self.__cache: Cache = cache

    def get_and_set(self, key: any, value: any) -> any:
        """
        获取并设置缓存值
        :return: 设置前的缓存值
        """
        if not key:
            raise Exception("Param 'key' cannot be None.")
        self.__lock.acquire()
        try:
            old_value = self.__cache.get(key)
            self.__cache[key] = value
            return old_value
        finally:
            self.__lock.release()

    def clear(self):
        """
        清空缓存
        """
        self.__lock.acquire()
        try:
            self.__cache.clear()
        finally:
            self.__lock.release()
