from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SyncScope(Enum):
    """
    同步范围
    """

    SongStar = "歌曲收藏"
    AlbumStar = "专辑收藏"
    ArtistStar = "艺人收藏"
    PublicPlaylistStar = "公开歌单收藏"
    PrivatePlaylist = "私有歌单"


@dataclass
class StarredDTO:
    id: str
    starred: bool
    starredAt: str  # 2026-10-18T11:42:24.020020694Z

    def __clone(self) -> StarredDTO:
        return StarredDTO(id=self.id, starred=self.starred, starredAt=self.starredAt)

    @classmethod
    def __merge_latest_version(cls, o1: StarredDTO, o2: StarredDTO) -> StarredDTO:
        if not o1 or not o2:
            raise Exception("参数错误")
        if not o1.id or not o2.id:
            raise Exception("参数错误[id]")
        o = o1.__clone()
        if (o.starredAt or "") < (o2.starredAt or ""):
            o.starred = o2.starred
            o.starredAt = o2.starredAt
        return o

    def marge_latest_version(self, other: StarredDTO) -> StarredDTO:
        return self.__merge_latest_version(self, other)
