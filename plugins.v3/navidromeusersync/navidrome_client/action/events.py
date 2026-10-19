# noinspection SpellCheckingInspection
"""
事件操作
"""
import asyncio
import json
from enum import Enum
from threading import RLock
from typing import Dict, Any, Callable, TypeAlias, List, Optional, Coroutine, Union
from urllib import parse

from aiohttp_sse_client2 import client as sse_client

from .. import session as _session
from ..compatible.log import logger


class EventType(Enum):
    ServerStart = "serverStart"
    KeepAlive = "keepAlive"
    RefreshResource = "refreshResource"


EventData: TypeAlias = Dict[str, Any]
SyncOrAsyncResult: TypeAlias = Union[None, Coroutine[Any, Any, None]]
EventHandler: TypeAlias = Callable[[EventType, EventData], SyncOrAsyncResult]


# noinspection SpellCheckingInspection,PyPep8Naming,PyShadowingBuiltins,PyShadowingNames
class EventsAction:
    """
    事件操作
    """

    __BASE_PATH = "/api/events"

    def __init__(self, session: _session.NavidromeClientSession):
        """
        """
        self.__session: _session.NavidromeClientSession = session
        self.__handlers: Dict[Optional[EventType], List[EventHandler]] = {}
        self.__running_lock = RLock()
        self.__running_task: Optional[asyncio.Task] = None

    # noinspection PyTypeChecker
    async def __on_message(self, event: sse_client.MessageEvent) -> None:
        if not event:
            return
        try:
            event_type: EventType = EventType._value2member_map_.get(event.type) if event.type else None
            event_data: EventData = json.loads(event.data) if event.data else {}
            await self.__handle_event(event_type=event_type, event_data=event_data)
            logger.debug(f"处理消息成功: last_event_id = {event.last_event_id}, type = {event.type}")
        except Exception as e:
            logger.error(f"处理消息失败: last_event_id = {event.last_event_id}, type = {event.type}, error = {e}")

    async def __handle_event(self, event_type: EventType, event_data: EventData) -> None:
        try:
            handlers: List[EventHandler] = self.__handlers.get(event_type) or []
            await self.__call_handlers(handlers=handlers, event_type=event_type, event_data=event_data)
            if event_type:
                handlers: List[EventHandler] = self.__handlers.get(None) or []
                await self.__call_handlers(handlers=handlers, event_type=event_type, event_data=event_data)
            logger.debug(f"处理事件成功: event_type = {event_type}")
        except Exception as e:
            logger.error(f"处理事件失败: event_type = {event_type}, error = {e}")

    @classmethod
    async def __call_handlers(cls, handlers: List[EventHandler], event_type: EventType, event_data: EventData) -> None:
        if not handlers:
            return
        for handler in handlers:
            await cls.__call_handler(handler=handler, event_type=event_type, event_data=event_data)

    @classmethod
    async def __call_handler(cls, handler: EventHandler, event_type: EventType, event_data: EventData) -> None:
        if not handler:
            return
        try:
            if asyncio.iscoroutinefunction(func=handler):
                await handler(event_type, event_data)
            else:
                handler(event_type, event_data)
        except Exception as e:
            logger.error(f"单个EventHandler调用失败: error = {e}")

    def add_handler(self, event_type: Optional[EventType], handler: EventHandler) -> None:
        handlers: List[EventHandler] = self.__handlers.get(event_type) or []
        handlers.append(handler)
        self.__handlers.update({event_type: handlers})

    def __create_event_source(self) -> sse_client.EventSource:
        params = {
            "jwt": self.__session.token
        }
        query_str = parse.urlencode(params)
        url = f"{self.__session.base_url}{self.__BASE_PATH}?{query_str}"
        return sse_client.EventSource(
            url=url,
            on_open=lambda: logger.info("SSE连接成功"),
        )

    async def __fetch_event(self) -> None:
        while self.__running_task:
            event_source = self.__create_event_source()
            try:
                async with event_source:
                    async for event in event_source:
                        await self.__on_message(event=event)
            except asyncio.CancelledError as e:
                raise e
            except Exception as e:
                logger.error(f"SSE连接错误: {e}")
                await asyncio.sleep(30)
                self.__session.refresh_token()

    # noinspection PyTypeChecker,PyProtectedMember
    async def start_listen(self) -> None:
        if self.__running_task:
            logger.warn("SSE监听已经开始，无需重复开始")
            return
        try:
            self.__running_lock.acquire()
            if self.__running_task:
                logger.warn("SSE监听已经开始，无需重复开始")
                return
            self.__running_task = asyncio.create_task(self.__fetch_event())
        finally:
            self.__running_lock.release()
            logger.info("SSE监听已开始")

    async def stop_listen(self) -> None:
        if not self.__running_task:
            logger.warning("SSE监听未开始，无需停止")
            return
        try:
            self.__running_lock.acquire()
            if not self.__running_task:
                logger.warning("SSE监听未开始，无需停止")
                return
            try:
                self.__running_task.cancel()
            except asyncio.CancelledError:
                pass
            self.__running_task = None
        finally:
            self.__running_lock.release()
            logger.info("SSE监听已停止")
