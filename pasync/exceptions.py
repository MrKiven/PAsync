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


class ResponseError(PAsyncError):
    pass


class InvalidResponse(PAsyncError):
    pass


class ExecAbortError(PAsyncError):
    pass


class BusyLoadingError(PAsyncError):
    pass


class NoScriptError(PAsyncError):
    pass


class ReadOnlyError(PAsyncError):
    pass
