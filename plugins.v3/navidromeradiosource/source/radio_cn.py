from typing import List, Optional, Any

from app.sdk.network import AsyncRequestUtils

from . import BaseSource
from ..model import Radio


# noinspection SpellCheckingInspection,DuplicatedCode
class RadioCnSource(BaseSource):
    """
    云听广播源
    https://www.radio.cn/pc-portal/erji/radioStation.html
    """

    # 组件key
    comp_key: str = "radio_cn"
    # 组件名称
    comp_name: str = "云听"
    # 组件顺序
    comp_order: int = 3

    __base_url = "https://ytmsout.radio.cn/web/appBroadcast"
    __home_page_url = "https://www.radio.cn/pc-portal/erji/radioStation.html"

    def __init__(self):
        self.__async_request_utils = AsyncRequestUtils()

    async def get_radios(self) -> List[Radio]:
        """
        获取全部广播信息列表
        """
        infos = await self.__list() or []
        radios = [self.__convert_radio(info=info) for info in infos if info]
        radios = [radio for radio in radios if radio]
        return radios

    async def __list(self, category_id: int = 0, province_code: int = 0) -> dict:
        """
        """
        url = f"{self.__base_url}/list?categoryId={category_id}&provinceCode={province_code}"
        res_json = await self.__async_request_utils.get_json(url=url)
        return self.__check_and_get(res_json=res_json) or []

    def __convert_radio(self, info: dict) -> Optional[Radio]:
        """
        转换广播信息
        """
        info = info or {}
        name = info.get("title")
        play_url = info.get("playUrlMulti") or info.get("mp3PlayUrlHigh") or info.get("playUrlLow") or info.get("mp3PlayUrlLow")
        if not name or not play_url:
            return None
        display_name = self.build_radio_display_name(raw_name=name)
        return Radio(name=display_name, stream_url=play_url, home_page_url=self.__home_page_url)

    @classmethod
    def __check_and_get(cls, res_json: dict) -> Any:
        if not res_json:
            raise Exception("请求失败")
        if res_json.get("code") != 0:
            raise Exception(res_json.get("message"))
        return res_json.get("data")
