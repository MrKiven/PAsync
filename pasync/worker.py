# -*- coding: utf-8 -*-

import socket
import os
import sys

from pasync._compat import Empty, Full, iteritems
from pasync.q import LifoQueue, Queue
from pasync.exceptions import (
    TimeoutError,
    ConnectionError,
    SocketRecvQueueFullError,
    SocketRecvQueueEmptyError
)


class Connection(object):

    description_format = "Connection<host={}, port={}>"

    def __init__(self, host="localhsot", port=1234, socket_timeout=None,
                 socket_connect_timeout=None, socket_keepalive=False,
                 retry_on_time=False, queue_class=Queue, queue_timeout=5,
                 queue_max_size=100, socket_read_size=65536):
        self.pid = os.getpid()
        self.host = host
        self.port = port
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.socket_keepalive = socket_keepalive
        self.retry_on_time = retry_on_time
        self.queue_class = queue_class
        self.queue_max_size = queue_max_size
        self.queue_timeout = queue_timeout
        self._sock = None
        self._connect_callback = []

        self._init_queue()

    def _init_queue(self):
        self.queue = self.queue_class(maxsize=self.queue_max_size)

    def __repr__(self):
        return self.description_format.format(self.host, self.port)

    def register_connect_callback(self, callback):
        self._connect_callback.append(callback)

    def clear_connect_callback(self):
        self._connect_callback = []

    def connect(self):
        if self._sock:
            return
        try:
            sock = self._connect()
        except socket.timeout:
            raise TimeoutError("Timeout connecting to server")
        except socket.error:
            e = sys.exc_info[0]
            raise ConnectionError(self._error_message(e))

        self._sock = sock

        for callback in self._connect_callback:
            if callable(callback):
                callback(self)

    def _connect(self):
        err = None
        for res in socket.getaddrinfo(self.host, self.port, 0,
                                      socket.SOCK_STREAM):
            family, socktype, proto, canonname, socket_address = res
            sock = None
            try:
                sock = socket.socket(family, socktype, proto)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

                #  TCP_KEEPALIVE
                if self.socket_keepalive:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    for k, v in iteritems(self.socket_keepalive_options):
                        sock.setsockopt(socket.SOL_TCP, k, v)

                sock.settimeout(self.socket_connect_timeout)
                sock.connect(socket_address)

                sock.settimeout(self.socket_timeout)
                return sock
            except socket.error as e:
                err = e
                if sock is not None:
                    sock.close()

        if err is not None:
            raise err

        raise socket.error("socket.getaddrinfo returned an empty list")

    def _error_message(self, exception):
        if len(exception.args) == 1:
            return "Error connection to %s:%s. %s." % \
                (self.host, self.port, exception.args[0])
        else:
            return "Error %s connecting to %s:%s. %s." % \
                (exception.args[0], self.host, self.port, exception.args[1])

    def disconnect(self):
        if self._sock is None:
            return
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()
        except socket.error:
            pass
        self._sock = None

    def send(self, data):
        if self._sock is None:
            raise ConnectionError("Socket has not created!!")
        try:
            self._sock.sendall(data)
            received = self._sock.recv(self.socket_read_size)
            self._set_result(received)
        except Exception:
            raise

    def _set_result(self, ret):
        if self.queue.qsize < self.queue_max_size:
            self.queue.put_nowait(ret)
        else:
            try:
                self.queue.put(timeout=self.queue_timeout)
            except Full:
                raise SocketRecvQueueFullError(
                    "Socket result has too many results hasn't been consume."
                    "use **conn.get(result)** to consume."
                )

    def get_result(self, timeout=5):
        if self.queue.qsize > 0:
            return self.queue.get_nowait()
        try:
            return self.queue.get(timeout=self.queue_timeout)
        except Empty:
            raise SocketRecvQueueEmptyError("No reslut.")
