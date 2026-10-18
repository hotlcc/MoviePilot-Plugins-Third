# noinspection SpellCheckingInspection
"""
电台操作
"""

import sys
from typing import List
from typing import Optional

from .. import session
from ..compatible import assert_util


# noinspection SpellCheckingInspection,PyPep8Naming,PyShadowingBuiltins,PyShadowingNames
class RadioAction:
    """
    电台操作
    """

    __BASE_PATH = "/api/radio"

    def __init__(self, session: session.NavidromeClientSession):
        """
        """
        self.__session = session

    def add(self, name: str, stream_url: str, home_page_url: str = None) -> str:
        """
        添加
        """
        assert_util.is_valid(name, "参数错误[name]")
        assert_util.is_valid(stream_url, "参数错误[stream_url]")
        json = {
            "name": name,
            "streamUrl": stream_url,
            "homePageUrl": home_page_url,
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

    def update(self, id: str, name: str, stream_url: str, home_page_url: str = None) -> Optional[dict]:
        """
        更新
        """
        assert_util.is_valid(id, "参数错误[id]")
        assert_util.is_valid(name, "参数错误[name]")
        assert_util.is_valid(stream_url, "参数错误[stream_url]")
        json = self.get_by_id(id=id) or {}
        json.update({
            "name": name,
            "streamUrl": stream_url,
            "homePageUrl": home_page_url,
        })
        return self.__session.put(url=f"{self.__BASE_PATH}/{id}", json=json) or {}

    def get_by_id(self, id: str) -> Optional[dict]:
        """
        根据ID获取单个信息
        """
        assert_util.is_valid(id, "参数错误[id]")
        return self.__session.get(url=f"{self.__BASE_PATH}/{id}") or {}

    def page(self, _start: int = 0, _end: int = 10,
             _sort: str = "name", _order: str = "ASC",
             name: str = None) -> List[dict]:
        """
        分页查询
        """
        params = {
            "_start": _start, "_end": _end,
            "_sort": _sort, "_order": _order,
            "name": name,
        }
        return self.__session.get(url=self.__BASE_PATH, params=params) or []

    def list(self, _sort: str = "name", _order: str = "ASC",
             name: str = None) -> List[dict]:
        """
        列表查询
        """
        return self.page(_end=sys.maxsize, _sort=_sort, _order=_order, name=name)
