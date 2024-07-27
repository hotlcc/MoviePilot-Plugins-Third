from enum import Enum
from pydantic import BaseModel

from app.schemas.types import MediaType


class MediaDigest(BaseModel):
    """
    媒体摘要
    """
    title: str = None
    year: str = None
    type: MediaType
    tmdb_id: str
    imdb_id: str = None
    tvdb_id: str = None


class MediaDataSource(Enum):
    """
    影视数据来源
    """
    MEDIA_LIBRARY = "媒体库"
    SUBSCRIBE = "订阅"
    SUBSCRIBE_HISTORY = "订阅历史"
