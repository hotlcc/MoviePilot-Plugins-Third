# noinspection SpellCheckingInspection
"""
歌单操作
"""
import sys
from typing import List, Optional

from .. import session
from ..compatible import assert_util


# noinspection SpellCheckingInspection,PyPep8Naming,PyShadowingBuiltins,PyShadowingNames,PyPackageRequirements,DuplicatedCode
class PlaylistAction:
    """
    歌单操作
    """

    __BASE_PATH = "/api/playlist"

    def __init__(self, session: session.NavidromeClientSession):
        """
        """
        self.__session = session

    def get_by_id(self, id: str) -> Optional[dict]:
        """
        根据ID获取单个歌单信息
        """
        assert_util.is_valid(id, "参数错误[id]")
        return self.__session.get(url=f"{self.__BASE_PATH}/{id}") or {}

    def page(self, _start: int = 0, _end: int = 15,
             _sort: str = "name", _order: str = "ASC",
             public: bool = None,
             starred: bool = None) -> List[dict]:
        """
        分页查询
        """
        if public is not None:
            public = 1 if public else 0
        params = {
            "_start": _start, "_end": _end,
            "_sort": _sort, "_order": _order,
            "public": public,
            "starred": starred,
        }
        return self.__session.get(url=self.__BASE_PATH, params=params) or []

    def list(self, _sort: str = "title", _order: str = "ASC",
             public: bool = None,
             starred: bool = None) -> List[dict]:
        """
        列表查询
        """
        return self.page(_end=sys.maxsize, _sort=_sort, _order=_order, public=public, starred=starred)

    def add(self, name: str, comment: str = None, public: bool = True) -> str:
        """
        添加
        """
        assert_util.is_valid(name, "参数错误[name]")
        json = {
            "name": name,
            "comment": comment,
            "public": public,
        }
        res_json = self.__session.post(url=self.__BASE_PATH, json=json) or {}
        id = res_json.get("id")
        assert_util.is_valid(id, "添加失败")
        return id

    def delete(self, id: str) -> None:
        """
        删除
        """
        assert_util.is_valid(id, "参数错误[id]")
        self.__session.delete(url=f"{self.__BASE_PATH}/{id}", json={})

    def delete_batch(self, ids: List[str]) -> None:
        """
        批量删除
        """
        assert_util.is_valid(ids, "参数错误[ids]")
        for id in ids:
            self.delete(id=id)

    def add_tracks(self, id: str, song_ids: List[str]) -> int:
        """
        歌单添加轨道
        :param id: 歌单ID
        :param song_ids: 歌曲IDs
        :return: 添加数量
        """
        assert_util.is_valid(id, "参数错误[id]")
        assert_util.is_valid(song_ids, "参数错误[song_ids]")
        body = {"ids": song_ids}
        res_json = self.__session.post(url=f"{self.__BASE_PATH}/{id}/tracks", json=body) or {}
        return res_json.get("added") or 0

    def remove_tracks(self, id: str, track_ids: List[str]) -> None:
        """
        歌单移除轨道
        :param id: 歌单ID
        :param track_ids: 轨道IDs
        """
        assert_util.is_valid(id, "参数错误[id]")
        assert_util.is_valid(track_ids, "参数错误[track_ids]")
        params = {"id": track_ids}
        self.__session.delete(url=f"{self.__BASE_PATH}/{id}/tracks", params=params)
