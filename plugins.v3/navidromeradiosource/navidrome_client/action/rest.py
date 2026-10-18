# noinspection SpellCheckingInspection
"""
Rest操作
"""

from .. import session
from ..compatible import assert_util


# noinspection SpellCheckingInspection,PyPep8Naming,PyShadowingBuiltins,PyShadowingNames
class RestAction:
    """
    Rest操作
    """

    __BASE_PATH = "/rest"

    def __init__(self, session: session.NavidromeClientSession):
        """
        """
        self.__session = session

    def star(self, id: str) -> None:
        """
        添加收藏
        """
        assert_util.is_valid(id, "参数错误[id]")
        params = {
            "id": id,
        }
        self.__session.fill_rest_params(params=params)
        res_json = self.__session.get(url=f"{self.__BASE_PATH}/star", params=params) or {}
        assert_util.is_valid(res_json, "操作失败")
        subsonic_response = res_json.get("subsonic-response") or {}
        assert_util.is_valid(subsonic_response, "操作失败")
        assert_util.is_true(subsonic_response.get("status") == "ok", (subsonic_response.get("error") or {}).get("message"))

    def unstar(self, id: str) -> None:
        """
        取消收藏
        """
        assert_util.is_valid(id, "参数错误[id]")
        params = {
            "id": id,
        }
        self.__session.fill_rest_params(params=params)
        res_json = self.__session.get(url=f"{self.__BASE_PATH}/unstar", params=params) or {}
        assert_util.is_valid(res_json, "操作失败")
        subsonic_response = res_json.get("subsonic-response") or {}
        assert_util.is_valid(subsonic_response, "操作失败")
        assert_util.is_true(subsonic_response.get("status") == "ok", (subsonic_response.get("error") or {}).get("message"))
