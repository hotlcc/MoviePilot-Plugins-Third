# noinspection SpellCheckingInspection
"""
Navidrome客户端会话
"""

from typing import Dict

import requests.auth

from .compatible import assert_util
from .compatible import http_util


# noinspection SpellCheckingInspection,PyArgumentList
class NavidromeClientSession(requests.Session):
    """
    Navidrome客户端会话
    """

    __TOKEN_HEADER_NAME: str = "X-Nd-Authorization"

    def __init__(self, base_url: str, username: str, password: str, header_host: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not base_url:
            raise ValueError("参数错误[base_url]")
        self.__base_url = base_url
        if not username:
            raise ValueError("参数错误[username]")
        self.__username = username
        if not password:
            raise ValueError("参数错误[password]")
        self.__password = password
        self.__header_host = header_host
        if header_host:
            self.headers.update({
                "Host": header_host
            })
            self.verify = False
        # 登录
        self.__auth_login(username=username, password=password)

    # noinspection PyTypeChecker
    def __auth_login(self, username: str, password: str) -> dict:
        """
        登录
        """
        json = {
            "username": username,
            "password": password
        }
        res_json: dict = self.post("/auth/login", json=json) or {}
        assert_util.is_valid(res_json, "登录失败")
        token = res_json.get("token")
        assert_util.is_valid(token, "登录失败")
        self.__token = token
        self.__subsonic_salt = res_json.get("subsonicSalt")
        self.__subsonic_token = res_json.get("subsonicToken")
        self.__is_admin = res_json.get("isAdmin")
        return res_json

    # noinspection PyAttributeOutsideInit
    def refresh_token(self, token: str = None) -> None:
        if token:
            if token != self.__token:
                self.__token = token
            return
        # 登录
        self.__auth_login(username=self.__username, password=self.__password)

    # noinspection PyAttributeOutsideInit
    def request0(self, method, url, headers: Dict[str, str] = None, *args, **kwargs) -> requests.Response:
        url = http_util.improve_url(base_url=self.__base_url, req_url=url)
        headers = headers or {}
        if not url.endswith("/auth/login"):
            headers.update({
                self.__TOKEN_HEADER_NAME: f"Bearer {self.__token}"
            })
        res = super().request(method=method, url=url, headers=headers, *args, **kwargs)
        token = res.headers.get(self.__TOKEN_HEADER_NAME)
        if token:
            self.refresh_token(token=token)
        if res.status_code == 401:
            res_json = res.json() or {}
            error = res_json.get("error") or ""
            if error == "Invalid username or password":
                raise Exception("用户名或密码无效")
            elif error == "Not authenticated":
                self.refresh_token()
                return self.request0(method, url, headers=headers, *args, **kwargs)
        if not res.ok:
            res_json = res.json() or {}
            raise Exception((res_json or {}).get("error", "请求失败"))
        return res

    # noinspection PyAttributeOutsideInit
    def request(self, method, url, headers: Dict[str, str] = None, *args, **kwargs):
        """
        改写请求
        """
        res = self.request0(method=method, url=url, headers=headers, *args, **kwargs)
        return res.json()

    def fill_rest_params(self, params: dict) -> None:
        """
        填充 rest 参数
        """
        assert_util.is_valid(params, "参数错误[params]")
        params.update({
            "u": self.__username,
            "t": self.__subsonic_token,
            "s": self.__subsonic_salt,
            "f": "json",
            "v": "1.8.0",
            "c": "NavidromeUI",
        })

    @property
    def base_url(self) -> str:
        return self.__base_url

    @property
    def token(self) -> str:
        return self.__token

    @property
    def is_admin(self) -> bool:
        return True if self.__is_admin else False
