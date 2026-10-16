import hashlib
import json
from datetime import datetime
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
    __sign_key = "f0fc4c668392f9f9a447e48584c214ee"

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

    async def __list(self, category_id: int = 0, province_code: int = 0) -> List[dict]:
        """
        """
        url = f"{self.__base_url}/list"
        params = {
            "categoryId": category_id,
            "provinceCode": province_code,
        }
        timestamp = str(int(datetime.now().timestamp() * 1000))
        sign = self.__sign(params=params, method="GET", timestamp=timestamp)
        headers = {
            "Timestamp": timestamp,
            "Sign": sign,
        }
        res_json = await self.__async_request_utils.get_json(url=url, params=params, headers=headers)
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

    @classmethod
    def __get_params_order_by_key(cls, method: str, params: dict) -> str:
        method = method or "get"
        method = method.upper()
        params = params or {}
        if method == 'POST':
            return json.dumps(params)
        else:
            keys = list(params.keys())
            keys.sort()
            return "&".join([f"{key}={params.get(key)}" for key in keys])

    @classmethod
    def __md5_str(cls, raw_str: str) -> str:
        raw_str = raw_str or ""
        raw_data = raw_str.encode("utf-8")
        md5_obj = hashlib.md5(raw_data)
        return md5_obj.hexdigest()

    @classmethod
    def __sign(cls, method: str, params: dict, timestamp: str | int) -> str:
        text = cls.__get_params_order_by_key(params=params, method=method) + "&" if params else ""
        text += f"timestamp={timestamp}&key={cls.__sign_key}"
        return cls.__md5_str(text)
