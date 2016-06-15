# -*- coding: utf-8 -*-

import socket
import os
import sys
import threading
from select import select

from pasync._compat import (
    Empty, Full, iteritems, BytesIO, recv, b, byte_to_chr,
    nativerstr
)
from pasync.q import LifoQueue, Queue
from pasync.server import task_callback_hook
from pasync.exceptions import (
    PAsyncError,
    TimeoutError,
    ConnectionError,
    SocketQueueError,
    SocketRecvQueueFullError,
    SocketRecvQueueEmptyError,
    InvalidResponse,
    ResponseError,
    ExecAbortError,
    BusyLoadingError,
    NoScriptError,
    ReadOnlyError
)
from pasync.utils import json_encode, json_decode

SYM_STAR = b('*')
SYM_DOLLAR = b('$')
SYM_CRLF = b('\r\n')
SYM_EMPTY = b('')

SERVER_CLOSED_CONNECTION_ERROR = "Connection closed by server."


class Token(object):
    def __init__(self, value):
        if isinstance(value, Token):
            value = value.value
        self.value = value

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value


class BaseParser(object):
    EXCEPTION_CLASSES = {
        'ERR': {
            'max number of clients reached': ConnectionError
        },
        'EXECABORT': ExecAbortError,
        'LOADING': BusyLoadingError,
        'NOSCRIPT': NoScriptError,
        'READONLY': ReadOnlyError
    }

    def parser_error(self, response):
        error_code = response.split(' ')[0]
        if error_code in self.EXCEPTION_CLASSES:
            response = response[len(error_code) + 1:]
            excepttion_class = self.EXCEPTION_CLASSES[error_code]
            if isinstance(excepttion_class, dict):
                excepttion_class = excepttion_class.get(response, ResponseError)
            return excepttion_class(response)
        return ResponseError(response)


class SocketBuffer(object):
    def __init__(self, socket, socket_read_size):
        self._sock = socket
        self.socket_read_size = socket_read_size
        self._buffer = BytesIO()
        self.bytes_written = 0
        self.bytes_read = 0

    @property
    def length(self):
        return self.bytes_written - self.bytes_read

    def _read_from_socket(self, length=None):
        socket_read_size = self.socket_read_size
        buf = self._buffer
        buf.seek(self.bytes_written)
        marker = 0

        try:
            while True:
                data = recv(self._sock, socket_read_size)
                if isinstance(data, bytes) and len(data) == 0:
                    raise socket.error(SERVER_CLOSED_CONNECTION_ERROR)
                buf.write(data)
                data_length = len(data)
                self.bytes_written += data_length
                marker += data_length

                if length is not None and length > marker:
                    continue
                break
        except socket.timeout:
            raise TimeoutError("Timeout reading from socket")
        except socket.error:
            e = sys.exc_info()[1]
            raise ConnectionError("Error while reading from socket: %s" %
                                  (e.args,))

    def read(self, length):
        length += 2

        if length > self.length:
            self._read_from_socket(length - self.length)

        self._buffer.seek(self.bytes_read)
        data = self._buffer.read(length)
        self.bytes_read += len(data)

        if self.bytes_read == self.bytes_written:
            self.purge()

        return data[:-2]

    def readline(self):
        buf = self._buffer
        buf.seek(self.bytes_read)
        data = buf.readline()

        while not data.endswith(SYM_CRLF):
            self._read_from_socket()
            buf.seek(self.bytes_read)
            data = buf.readline()

        self.bytes_read += len(data)

        if self.bytes_read == self.bytes_written:
            self.purge()

        return data[:-2]

    def purge(self):
        self._buffer.seek(0)
        self._buffer.truncate()
        self.bytes_written = 0
        self.bytes_read = 0

    def close(self):
        try:
            self.purge()
            self._buffer.close()
        except:
            pass
        self._buffer = None
        self._sock = None


class PythonParser(BaseParser):
    encoding = None

    def __init__(self, socket_read_size):
        self.socket_read_size = socket_read_size
        self._sock = None
        self._buffer = None

    def __del__(self):
        try:
            self.on_disconnect()
        except Exception:
            pass

    def on_connect(self, connection):
        self._sock = connection._sock
        self._buffer = SocketBuffer(self._sock, self.socket_read_size)
        if connection.decode_responses:
            self.encoding = connection.encoding

    def on_disconnect(self):
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        if self._buffer is not None:
            self._buffer.close()
            self._buffer = None
        self.encoding = None

    def can_read(self):
        return self._buffer and bool(self._buffer.length)

    def read_response(self):
        response = self._buffer.readline()
        if not response:
            raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR)

        byte, response = byte_to_chr(response[0], response[1:])

        if byte not in ('-', '+', ':', '$', '*'):
            raise InvalidResponse("Protocol Error: %s, %s" %
                                  (str(byte), str(response)))

        if byte == '-':
            response = nativerstr(response)
            error = self.parser_error(response)
            if isinstance(error, ConnectionError):
                raise error
            return error
        elif byte == '+':
            pass
        elif byte == ':':
            response = long(response)
        elif byte == '$':
            length = int(response)
            if length == -1:
                return None
            response = self._buffer.read(length)
        elif byte == '*':
            length = int(response)
            if length == -1:
                return None
            response = [self.read_response() for _ in xrange(length)]
        if isinstance(response, bytes) and self.encoding:
            response = response.decode(self.encoding)
        return response


class Connection(object):
    """Manages TCP communication to and from QServer"""
    description_format = "Connection<host={}, port={}>"

    def __init__(self, host="localhost", port=1234, socket_timeout=None,
                 socket_connect_timeout=None, socket_keepalive=False,
                 socket_keepalive_options=None, retry_on_time=False,
                 encoding='utf-8', encoding_errors='strict', queue_class=Queue,
                 queue_timeout=5, queue_max_size=100, decode_responses=False,
                 parser_class=PythonParser, socket_read_size=65536):
        self.pid = os.getpid()
        self.host = host
        self.port = port
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.socket_keepalive = socket_keepalive
        self.socket_keepalive_options = socket_keepalive_options or {}
        self.retry_on_time = retry_on_time
        self.encoding = encoding
        self.encoding_errors = encoding_errors
        self.decode_responses = decode_responses
        self.queue_class = queue_class
        self.queue_max_size = queue_max_size
        self.queue_timeout = queue_timeout
        self.socket_read_size = socket_read_size
        self._sock = None
        self._parser = parser_class(socket_read_size)
        self._connect_callback = []

        self.task_id = 0

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
            e = sys.exc_info()[1]
            raise ConnectionError(self._error_message(e))

        self._sock = sock
        try:
            self.on_connect()
        except PAsyncError:
            self.disconnect()
            raise

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

    def on_connect(self):
        self._parser.on_connect(self)

    def disconnect(self):
        self._parser.on_disconnect()
        if self._sock is None:
            return
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()
        except socket.error:
            pass
        self._sock = None

    def send(self, data, ack=True, **kwargs):
        task = {
            'task_id': self.task_id,
            'task_content': data,
            'task_params': kwargs
        }
        if self._sock is None:
            raise ConnectionError("Socket has not created!!")

        # register callback
        task_callback_hook.register(self._set_result)

        try:
            self._sock.sendall(json_encode(task))
            received = json_decode(self._sock.recv(self.socket_read_size))
            # After received ack
            self.task_id += 1
            if ack:
                if received.get('task_ack') is True:
                    pass
                else:
                    raise
        except Exception:
            self.disconnect()
            raise

    def can_read(self, timeout=0):
        sock = self._sock
        if not sock:
            self.connect()
            sock = self._sock
        return self._parser.can_read() or \
            bool(select([sock], [], [], timeout)[0])

    def read_response(self):
        try:
            response = self._parser.read_response()
        except:
            self.disconnect()
            raise
        if isinstance(response, ResponseError):
            raise response
        return response

    def encode(self, value):
        if isinstance(value, Token):
            return b(value.value)
        elif isinstance(value, bytes):
            return value
        elif isinstance(value, (int, long)):
            return b(str(value))
        elif isinstance(value, float):
            return b(repr(value))
        elif not isinstance(value, basestring):
            value = unicode(value)
        if isinstance(value, unicode):
            value = value.encode(self.encoding, self.encoding_errors)
        return value

    def _set_result(self, ret):
        if not hasattr(self, "queue"):
            raise SocketQueueError("Socket queue has not Initialized")

        if self.queue.qsize() < self.queue_max_size:
            self.queue.put_nowait(ret)
        else:
            try:
                self.queue.put(ret, timeout=self.queue_timeout)
            except Full:
                raise SocketRecvQueueFullError(
                    "Socket result has too many results hasn't been consume."
                    "use **conn.get(result)** to consume."
                )

    def get_result(self, timeout=5):
        if self.queue.qsize() > 0:
            return self.queue.get_nowait()
        try:
            return self.queue.get(timeout=self.queue_timeout)
        except Empty:
            raise SocketRecvQueueEmptyError("No reslut.")


class ConnectionPool(object):

    def __init__(self, connection_class=Connection, max_connections=50,
                 timeout=20, queue_class=LifoQueue, **connection_kwargs):
        self.connection_class = connection_class
        self.queue_class = queue_class
        self.timeout = timeout
        self.max_connections = max_connections
        self.connection_kwargs = connection_kwargs

        self.reset()

    def reset(self):
        self.pid = os.getpid()
        self._check_lock = threading.Lock()

        # Create and fill up a thread safe queue with ``None`` values.
        self.pool = self.queue_class(self.max_connections)
        while True:
            try:
                self.pool.put_nowait(None)
            except Full:
                break

        self._connections = []

    def _check_pid(self):
        "Check if has changed process."
        if self.pid != os.getpid():
            with self._check_lock:
                if self.pid == os.getpid():
                    return
                self.disconnect()
                self.reset()

    def make_connection(self):
        "Make a fresh connection."
        connection = self.connection_class(**self.connection_kwargs)
        self._connections.append(connection)
        return connection

    def get_connection(self):
        self._check_pid()

        connection = None
        try:
            connection = self.pool.get(timeout=self.timeout)
        except Empty:
            raise ConnectionError("No connection available.")

        if connection is None:
            connection = self.make_connection()

        return connection

    def release(self, connection):
        "Release the connection back to the pool."
        self._check_pid()
        if connection.pid != self.pid:
            return

        # Put the connetion back to the pool.
        try:
            self.pool.put_nowait(connection)
        except Full:
            pass

    def disconnect(self):
        for connection in self._connections:
            connection.disconnect()
