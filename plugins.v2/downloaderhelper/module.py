from enum import Enum
from typing import Set, List, Optional

from app.plugins.downloaderhelper.convertor import IConvertor, ByteSizeConvertor, PercentageConvertor, StateConvertor, SpeedConvertor, RatioConvertor, TimestampConvertor, LimitSpeedConvertor, LimitRatioConvertor, TimeIntervalConvertor, TagsConvertor


class TaskResult:
    """
    任务执行结果
    """

    def __init__(self, name: str):
        self.__name: str = name
        self.__success: bool = True
        self.__total: int = 0
        self.__seeding: int = 0
        self.__tagging: int = 0
        self.__delete: int = 0

    def get_name(self) -> str:
        return self.__name

    def set_success(self, success: bool):
        self.__success = success
        return self

    def is_success(self):
        return self.__success

    def set_total(self, total: int):
        self.__total = total
        return self

    def get_total(self):
        return self.__total

    def set_seeding(self, seeding: int):
        self.__seeding = seeding
        return self

    def get_seeding(self):
        return self.__seeding

    def set_tagging(self, tagging: int):
        self.__tagging = tagging
        return self

    def get_tagging(self):
        return self.__tagging

    def set_delete(self, delete: int):
        self.__delete = delete
        return self

    def get_delete(self):
        return self.__delete


class TaskContext:
    """
    任务上下文
    """

    def __init__(self):
        # 选择的下载器集合，为None时表示选择全部
        self.__selected_downloaders: Optional[Set[str]] = None

        # 启用的子任务
        # 启用做种
        self.__enable_seeding: bool = True
        # 启用打标
        self.__enable_tagging: bool = True
        # 启用删种
        self.__enable_delete: bool = True

        # 选择的种子，为None时表示选择全部
        # self.__selected_torrents: Set[str] = None
        self.__selected_torrents = None

        #  源文件删除事件数据
        self.__download_file_deleted_event_data = None
        #  下载任务删除事件数据
        self.__download_deleted_event_data = None

        # 任务结果集
        self.__results: Optional[List[TaskResult]] = None

        # 操作用户名
        self.__username: Optional[str] = None

        # 是否使用种子缓存
        self.__use_torrents_cache: bool = False

    def select_downloader(self, downloader_name: str):
        """
        选择下载器
        :param downloader_name: 下载器名称
        """
        if not self.__selected_downloaders:
            self.__selected_downloaders = set()
        if downloader_name:
            self.select_downloaders(downloader_names=[downloader_name])
        return self

    def select_downloaders(self, downloader_names: List[str]):
        """
        选择下载器
        :param downloader_names: 下载器名称s
        """
        if not self.__selected_downloaders:
            self.__selected_downloaders = set()
        if downloader_names:
            for downloader_name in downloader_names:
                self.__selected_downloaders.add(downloader_name)
        return self

    def is_selected_the_downloader(self, downloader_name: str) -> bool:
        """
        是否选择了指定的下载器
        :param downloader_name: 下载器名称
        :return: 是否选择了指定的下载器
        """
        if not downloader_name:
            return False
        return True if self.__selected_downloaders is None or downloader_name in self.__selected_downloaders else False

    def enable_seeding(self, enable_seeding: bool = True):
        """
        是否启用做种
        :param enable_seeding: 是否启用做种
        """
        self.__enable_seeding = enable_seeding if enable_seeding else False
        return self

    def is_enabled_seeding(self) -> bool:
        """
        是否启用了做种
        :return: 是否启用了做种
        """
        return self.__enable_seeding

    def enable_tagging(self, enable_tagging: bool = True):
        """
        是否启用打标
        :param enable_tagging: 是否启用打标
        """
        self.__enable_tagging = enable_tagging if enable_tagging else False
        return self

    def is_enabled_tagging(self) -> bool:
        """
        是否启用了打标
        :return: 是否启用了打标
        """
        return self.__enable_tagging

    def enable_delete(self, enable_delete: bool = True):
        """
        是否启用删种
        :param enable_delete: 是否启用删种
        """
        self.__enable_delete = enable_delete if enable_delete else False
        return self

    def is_enabled_delete(self) -> bool:
        """
        是否启用了删种
        :return: 是否启用了删种
        """
        return self.__enable_delete

    def select_torrent(self, torrent: str):
        """
        选择种子
        :param torrent: 种子key
        """
        if not torrent:
            return self
        if not self.__selected_torrents:
            self.__selected_torrents = set()
        self.__selected_torrents.add(torrent)
        return self

    def select_torrents(self, torrents: List[str]):
        """
        选择种子
        :param torrents: 种子keys
        """
        if not torrents:
            return self
        for torrent in torrents:
            self.select_torrent(torrent)
        return self

    # def get_selected_torrents(self) -> Set[str]:
    def get_selected_torrents(self):
        """
        获取所有选择的种子
        """
        return self.__selected_torrents

    def set_download_file_deleted_event_data(self, download_file_deleted_event_data: dict):
        """
        设置源文件删除事件数据
        """
        self.__download_file_deleted_event_data = download_file_deleted_event_data
        return self

    def get_download_file_deleted_event_data(self) -> dict:
        """
        获取源文件删除事件数据
        """
        return self.__download_file_deleted_event_data

    def set_download_deleted_event_data(self, download_deleted_event_data: dict):
        """
        设置下载任务删除事件数据
        """
        self.__download_deleted_event_data = download_deleted_event_data
        return self

    def get_download_deleted_event_data(self) -> dict:
        """
        获取下载任务删除事件数据
        """
        return self.__download_deleted_event_data

    def save_result(self, result: TaskResult):
        """
        存储结果
        :param result: 结果
        """
        if not result:
            return self
        if not self.__results:
            self.__results = []
        self.__results.append(result)
        return self

    def get_results(self) -> List[TaskResult]:
        """
        获取结果集
        """
        return self.__results

    def set_username(self, username: str):
        """
        设置操作用户名
        """
        self.__username = username
        return self

    def get_username(self) -> str:
        """
        获取操作用户名
        """
        return self.__username

    def set_use_torrents_cache(self, use_torrents_cache: bool):
        """
        设置是否使用种子缓存
        """
        self.__use_torrents_cache = use_torrents_cache
        return self

    def get_use_torrents_cache(self) -> bool:
        """
        获取是否使用种子缓存
        """
        return self.__use_torrents_cache


class TorrentField(Enum):
    """
    种子字段枚举
    """
    NAME = ('名称', 'name', 'name', None)
    SELECT_SIZE = ('选定大小', 'size', 'sizeWhenDone', ByteSizeConvertor())
    TOTAL_SIZE = ('总大小', 'total_size', 'totalSize', ByteSizeConvertor())
    PROGRESS = ('已完成', 'progress', 'percentDone', PercentageConvertor())
    STATE = ('状态', 'state', 'status', StateConvertor())
    DOWNLOAD_SPEED = ('下载速度', 'dlspeed', 'rateDownload', SpeedConvertor())
    UPLOAD_SPEED = ('上传速度', 'upspeed', 'rateUpload', SpeedConvertor())
    REMAINING_TIME = ('剩余时间', '#REMAINING_TIME', '#REMAINING_TIME', TimeIntervalConvertor())
    RATIO = ('比率', 'ratio', 'uploadRatio', RatioConvertor())
    CATEGORY = ('分类', 'category', None, None)
    TAGS = ('标签', 'tags', 'labels', TagsConvertor())
    ADD_TIME = ('添加时间', 'added_on', 'addedDate', TimestampConvertor())
    COMPLETE_TIME = ('完成时间', 'completion_on', 'doneDate', TimestampConvertor())
    DOWNLOAD_LIMIT = ('下载限制', 'dl_limit', 'downloadLimit', LimitSpeedConvertor())
    UPLOAD_LIMIT = ('上传限制', 'up_limit', 'uploadLimit', LimitSpeedConvertor())
    DOWNLOADED = ('已下载', 'downloaded', 'downloadedEver', ByteSizeConvertor())
    UPLOADED = ('已上传', 'uploaded', 'uploadedEver', ByteSizeConvertor())
    DOWNLOADED_SESSION = ('本次会话下载', 'downloaded_session', None, ByteSizeConvertor())
    UPLOADED_SESSION = ('本次会话上传', 'uploaded_session', None, ByteSizeConvertor())
    REMAINING = ('剩余', '#REMAINING', '#REMAINING', ByteSizeConvertor())
    SAVE_PATH = ('保存路径', 'save_path', 'downloadDir', None)
    COMPLETED = ('完成', 'completed', '#COMPLETED', ByteSizeConvertor())
    RATIO_LIMIT = ('比率限制', 'ratio_limit', 'seedRatioLimit', LimitRatioConvertor())

    def __init__(self, name_: str, qb: str, tr: str, convertor: IConvertor):
        self.name_ = name_
        self.qb = qb
        self.tr = tr
        self.convertor = convertor


# TorrentField 映射
TorrentFieldMap = dict((field.name, field) for field in TorrentField)


class DownloaderTransferInfo():
    """
    下载器传输信息
    """

    # 下载速度
    download_speed: Optional[str] = '0.00B/s'
    # 上传速度
    upload_speed: Optional[str] = '0.00B/s'
    # 下载量
    download_size: Optional[str] = '0.00B'
    # 上传量
    upload_size: Optional[str] = '0.00B'
    # 剩余空间
    free_space: Optional[str] = '0.00B'


class EventDeleteTorrentStrategy(Enum):
    """
    事件删种策略
    """

    EARLY = ("提前删种", "当监听到源文件删除事件时立即删除种子，但不删除数据文件")
    DELAYED = ("延迟删种", "当监听到源文件删除事件时会判断种子数据文件是否存在，只有数据文件不存在时才会删种，比如剧集这种多文件种子，只有当最后一集源文件被删除时才会删种")

    def __init__(self, name_: str, desc: str):
        self.name_ = name_
        self.desc = desc
