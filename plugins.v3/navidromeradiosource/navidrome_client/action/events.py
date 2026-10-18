# noinspection SpellCheckingInspection
"""
事件操作
"""
import json
from enum import Enum
from typing import Dict, Any, Callable, TypeAlias, List, Optional

from sseclient import SSEClient

from .. import session
from ..compatible.log import logger


class EventType(Enum):
    ServerStart = "serverStart"
    KeepAlive = "keepAlive"
    RefreshResource = "refreshResource"


EventData: TypeAlias = Dict[str, Any]
EventHandler: TypeAlias = Callable[[EventType, EventData], None]


# noinspection SpellCheckingInspection,PyPep8Naming,PyShadowingBuiltins,PyShadowingNames
class EventsAction:
    """
    事件操作
    """

    __BASE_PATH = "/api/events"

    def __init__(self, session: session.NavidromeClientSession):
        """
        """
        self.__session = session
        self.__status = False
        self.__handlers: Dict[Optional[EventType], List[EventHandler]] = {}

    def __create_client(self) -> SSEClient:
        headers = {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache"
        }
        params = {
            "jwt": self.__session.token
        }
        res = self.__session.request0(method="GET", url=self.__BASE_PATH, headers=headers, params=params, stream=True)
        return SSEClient(res.iter_content())

    def __handle_event(self, event_type: EventType, event_data: EventData) -> None:
        handlers: List[EventHandler] = self.__handlers.get(event_type) or []
        self.__call_handlers(handlers=handlers, event_type=event_type, event_data=event_data)
        if event_type:
            handlers: List[EventHandler] = self.__handlers.get(None) or []
            self.__call_handlers(handlers=handlers, event_type=event_type, event_data=event_data)

    @classmethod
    def __call_handlers(cls, handlers: List[EventHandler], event_type: EventType, event_data: EventData) -> None:
        if not handlers:
            return
        for handler in handlers:
            cls.__call_handler(handler=handler, event_type=event_type, event_data=event_data)

    @classmethod
    def __call_handler(cls, handler: EventHandler, event_type: EventType, event_data: EventData) -> None:
        if not handler:
            return
        try:
            handler(event_type, event_data)
        except Exception as e:
            logger.error(f"单个EventHandler调用失败: error = {e}")

    def add_handler(self, event_type: Optional[EventType], handler: EventHandler) -> None:
        handlers: List[EventHandler] = self.__handlers.get(event_type) or []
        handlers.append(handler)
        self.__handlers.update({event_type: handlers})

    # noinspection PyTypeChecker
    def start_client(self):
        self.__status = True
        client: SSEClient = None
        while self.__status:
            try:
                client = self.__create_client()
                for event in client.events():
                    event_type: EventType = EventType._value2member_map_.get(event.event) if event.event else None
                    data = event.data
                    event_data: EventData = json.loads(data) if data else {}
                    try:
                        self.__handle_event(event_type=event_type, event_data=event_data)
                        logger.debug(f"处理事件成功: event_id = {event.id}, event_type = {event_type}")
                    except Exception as e:
                        logger.error(f"处理事件失败: event_id = {event.id}, event_type = {event_type}, error = {e}")
            except Exception as e:
                logger.warn(f"SSE连接断开，重试中: {e}")
        if client:
            client.close()
            logger.info("已停止监听SSE")

    def stop_client(self):
        self.__status = False
