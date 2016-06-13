# -*- coding: utf-8 -*-


class PAsyncError(Exception):
    pass


class TimeoutError(PAsyncError):
    pass


class ConnectionError(PAsyncError):
    pass


class SocketQueueError(PAsyncError):
    pass


class SocketRecvQueueFullError(PAsyncError):
    pass


class SocketRecvQueueEmptyError(PAsyncError):
    pass
