from dataclasses import dataclass
from enum import Enum


class SyncScope(Enum):
    """
    同步范围
    """

    SongStar = "歌曲收藏"
    AlbumStar = "专辑收藏"
    ArtistStar = "艺人收藏"
    PrivatePlaylist = "私有歌单"
    PlaylistStar = "歌单收藏"


@dataclass
class StarredInfo:
    id: str
    starred: bool
    starredAt: str  # 2026-10-18T11:42:24.020020694Z
