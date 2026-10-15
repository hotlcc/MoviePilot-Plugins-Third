from typing import List, Any, Optional

from app.sdk.network import AsyncRequestUtils

from . import BaseSource
from ..model import Radio


class CnrSource(BaseSource):
    """
    央广网广播源
    """

    # 组件key
    comp_key: str = "cnr"
    # 组件名称
    comp_name: str = "央广网"
    # 组件顺序
    comp_order: int = 1

    __base_url = "https://apppc.cnr.cn"

    def __init__(self):
        self.__async_request_utils = AsyncRequestUtils()

    async def get_radios(self) -> List[Radio]:
        infos: List[Radio] = []
        national_radios = await self.__get_national_radios()
        if national_radios:
            infos.extend(national_radios)
        local_list = await self.__get_local_list()
        if local_list:
            for local in local_list:
                if not local:
                    continue
                local_id = local.get("id")
                if not local_id:
                    continue
                local_radio_infos = await self.__get_local_radios(local_id=local_id)
                if local_radio_infos:
                    infos.extend(local_radio_infos)
        return infos

    async def __get_national_radios(self) -> List[Radio]:
        """
        获取国家广播信息列表
        """
        url = f"{self.__base_url}/national"
        res_json = await self.__async_request_utils.post_json(url=url, json={})
        data = self.__check_and_get(res_json=res_json) or {}
        return self.__extract_radios(data=data)

    async def __get_local_list(self) -> List[dict]:
        """
        获取地区列表
        """
        url = f"{self.__base_url}/local/list"
        res_json = await self.__async_request_utils.post_json(url=url, json={})
        data = self.__check_and_get(res_json=res_json) or {}
        return data.get("liveChannelPlace") or []

    async def __get_local_radios(self, local_id: str) -> List[Radio]:
        """
        获取地方广播信息列表
        """
        url = f"{self.__base_url}/local"
        body = {
            "id": local_id
        }
        res_json = await self.__async_request_utils.post_json(url=url, json=body)
        data = self.__check_and_get(res_json=res_json) or {}
        return self.__extract_radios(data=data)

    @classmethod
    def __check_and_get(cls, res_json: dict) -> Any:
        if not res_json:
            raise Exception("请求失败")
        code = res_json.get("code")
        if code != "200" and code != 200:
            raise Exception(res_json.get("message"))
        return res_json.get("data")

    @classmethod
    def __extract_radios(cls, data: dict) -> List[Radio]:
        """
        提取广播信息列表
        """
        if not data:
            return []
        categories = data.get("categories") or []
        category = categories[0] if categories else {}
        detail = category.get("detail") or []
        radios = [cls.__convert_radio(info=d) for d in detail if d]
        radios = [radio for radio in radios if radio]
        return radios

    @classmethod
    def __convert_radio(cls, info: dict) -> Optional[Radio]:
        """
        转换广播信息
        """
        info = info or {}
        name = info.get("name")
        other_info11 = info.get("other_info11") or []
        other_info11_url = (other_info11[0] if other_info11 else {}).get("url")
        if not name or not other_info11_url:
            return None
        other_info8 = info.get("other_info8")
        return Radio(name=name, stream_url=other_info11_url, home_page_url=other_info8)
