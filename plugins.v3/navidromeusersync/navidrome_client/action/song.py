# noinspection SpellCheckingInspection
"""
歌曲操作
"""
import sys
from typing import List, Optional

from .. import session
from ..compatible import assert_util


# noinspection SpellCheckingInspection,PyPep8Naming,PyShadowingBuiltins,PyShadowingNames
class SongAction:
    """
    歌曲操作
    """

    __BASE_PATH = "/api/song"

    def __init__(self, session: session.NavidromeClientSession):
        """
        """
        self.__session = session

    def get_by_id(self, id: str) -> Optional[dict]:
        """
        根据ID获取单个歌曲信息
        """
        assert_util.is_valid(id, "参数错误[id]")
        return self.__session.get(url=f"{self.__BASE_PATH}/{id}") or {}

    def page(self, _start: int = 0, _end: int = 15,
             _sort: str = "title", _order: str = "ASC",
             album_id: str = None,
             library_id: List[int] = None,
             starred: bool = None) -> List[dict]:
        """
        分页查询
        """
        params = {
            "_start": _start, "_end": _end,
            "_sort": _sort, "_order": _order,
            "album_id": album_id,
            "library_id": library_id,
            "starred": starred,
        }
        return self.__session.get(url=self.__BASE_PATH, params=params) or []

    def list(self, _sort: str = "title", _order: str = "ASC",
             album_id: str = None,
             library_id: List[int] = None,
             starred: bool = None) -> List[dict]:
        """
        列表查询
        """
        return self.page(_end=sys.maxsize, _sort=_sort, _order=_order, album_id=album_id, library_id=library_id, starred=starred)
