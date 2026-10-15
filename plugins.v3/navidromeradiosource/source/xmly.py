from typing import List, Optional, Any

from app.sdk.network import AsyncRequestUtils

from . import BaseSource
from ..model import Radio


# noinspection SpellCheckingInspection
class XmlySource(BaseSource):
    """
    喜马拉雅广播源
    """

    # 组件key
    comp_key: str = "xmly"
    # 组件名称
    comp_name: str = "喜马拉雅"
    # 组件顺序
    comp_order: int = 2

    __base_url = "https://m.ximalaya.com"

    def __init__(self):
        self.__async_request_utils = AsyncRequestUtils()

    async def get_radios(self) -> List[Radio]:
        """
        获取全部广播信息列表
        """
        infos = await self.__search_list() or []
        radios = [self.__convert_radio(info=info) for info in infos if info]
        radios = [radio for radio in radios if radio]
        return radios

    async def __search_page(self, page_num: int = 1, page_size: int = 10,
                            location_id: int = 0, location_type_id: int = 0,
                            category_id: int = 0) -> dict:
        """
        搜索一页
        :return: 分页
        """
        url = f"{self.__base_url}/radio-first-page-app/search"
        params = {
            "pageNum": page_num,
            "pageSize": page_size,
            "locationId": location_id,
            "locationTypeId": location_type_id,
            "categoryId": category_id,
        }
        res_json = await self.__async_request_utils.get_json(url=url, params=params)
        page = self.__check_and_get(res_json=res_json) or {}
        if not page:
            return {}
        page["hasNextPage"] = page.get("total") > page.get("pageNum") * page.get("pageSize")
        return page

    async def __search_list(self, location_id: int = 0, location_type_id: int = 0,
                            category_id: int = 0) -> List[dict]:
        """
        搜索列表
        """
        page_size = 500
        result = []
        for page_num in range(1, 10000):
            page = await self.__search_page(page_num=page_num, page_size=page_size,
                                            location_id=location_id, location_type_id=location_type_id,
                                            category_id=category_id)
            if not page:
                break
            radios = page.get("radios")
            if not radios:
                break
            result.extend(radios)
            if not page.get("hasNextPage"):
                break
        return result

    @classmethod
    def __convert_radio(cls, info: dict) -> Optional[Radio]:
        """
        转换广播信息
        """
        info = info or {}
        name = info.get("name")
        play_url = info.get("playUrl") or {}
        play_url = play_url.get("aac64") or play_url.get("ts64") or play_url.get("aac24") or play_url.get("ts24")
        if not name or not play_url:
            return None
        id = info.get("id")
        return Radio(name=name, stream_url=play_url, home_page_url=f"{cls.__base_url}/radio/{id}")

    @classmethod
    def __check_and_get(cls, res_json: dict) -> Any:
        if not res_json:
            raise Exception("请求失败")
        if res_json.get("ret") != 0:
            raise Exception(res_json.get("msg"))
        return res_json.get("data")
