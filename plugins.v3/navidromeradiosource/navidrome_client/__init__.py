# noinspection SpellCheckingInspection
"""
Navidrome客户端
"""

import os

from . import session
from .action import album
from .action import artist
from .action import events
from .action import radio
from .action import rest
from .action import song
from .compatible import assert_util

########################### 获取环境变量 ###########################
# 基础URL
# noinspection SpellCheckingInspection
SERVICE_NAVIDROME_BASE_URL = os.environ.get("SERVICE_NAVIDROME_BASE_URL")
# 认证用户名
# noinspection SpellCheckingInspection
SERVICE_NAVIDROME_AUTH_USERNAME = os.environ.get("SERVICE_NAVIDROME_AUTH_USERNAME")
# 认证密码
# noinspection SpellCheckingInspection
SERVICE_NAVIDROME_AUTH_PASSWORD = os.environ.get("SERVICE_NAVIDROME_AUTH_PASSWORD")
# http 请求 header host
# noinspection SpellCheckingInspection
SERVICE_NAVIDROME_HTTP_HEADER_HOST = os.environ.get("SERVICE_NAVIDROME_HTTP_HEADER_HOST")


# noinspection SpellCheckingInspection,PyPep8Naming
class NavidromeClient:
    """
    Navidrome客户端
    """

    def __init__(self, base_url: str = None, username: str = None, password: str = None, header_host: str = None):
        """
        """
        base_url = base_url or SERVICE_NAVIDROME_BASE_URL
        assert_util.is_valid(base_url, "参数错误[base_url]")
        self.__base_url = base_url
        username = username or SERVICE_NAVIDROME_AUTH_USERNAME
        assert_util.is_valid(username, "参数错误[username]")
        self.__username = username
        password = password or SERVICE_NAVIDROME_AUTH_PASSWORD
        assert_util.is_valid(password, "参数错误[password]")
        self.__password = password
        header_host = header_host or SERVICE_NAVIDROME_HTTP_HEADER_HOST
        self.__header_host = header_host
        self.__session = session.NavidromeClientSession(base_url=base_url, username=username, password=password, header_host=header_host)
        # action
        self.__radio = radio.RadioAction(session=self.__session)
        self.__song = song.SongAction(session=self.__session)
        self.__rest = rest.RestAction(session=self.__session)
        self.__album = album.AlbumAction(session=self.__session)
        self.__artist = artist.ArtistAction(session=self.__session)
        self.__events = events.EventsAction(session=self.__session)

    def radio(self) -> radio.RadioAction:
        """
        电台操作
        """
        return self.__radio

    def song(self) -> song.SongAction:
        """
        歌曲操作
        """
        return self.__song

    def rest(self) -> rest.RestAction:
        """
        Rest操作
        """
        return self.__rest

    def album(self) -> album.AlbumAction:
        """
        专辑操作
        """
        return self.__album

    def artist(self) -> artist.ArtistAction:
        """
        艺人操作
        """
        return self.__artist

    def events(self) -> events.EventsAction:
        """
        事件操作
        """
        return self.__events

    def is_admin(self) -> bool:
        return self.__session.is_admin
