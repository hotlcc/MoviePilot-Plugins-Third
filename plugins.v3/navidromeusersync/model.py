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
