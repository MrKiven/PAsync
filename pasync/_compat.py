# -*- coding: utf-8 -*-

import sys

try:  # Python 3
    from queue import LifoQueue, Empty, Full
except ImportError:
    from Queue import Empty, Full
    try:  # Python 2.6 - 2.7
        from Queue import LifoQueue, Queue
    except ImportError:  # Python 2.5
        from Queue import Queue

        class LifoQueue(Queue):

            def __init__(self, maxsize):
                self.maxsize = maxsize
                self.queue = []

            def _qsize(self, len=len):
                return len(self.queue)

            def _put(self, item):
                self.queue.append(item)

            def _get(self):
                return self.queue.pop()

if sys.version_info[0] < 3:

    import time
    import socket
    import errno

    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO
    else:
        from io import BytesIO

    def _retryable_call(s, func, *args, **kwargs):
        timeout, deadline = None, 0.0
        attempted = False
        try:
            timeout = s.gettimeout()
        except AttributeError:
            pass

        if timeout:
            deadline = time.time() + timeout

        try:
            while True:
                if attempted and timeout:
                    now = time.time()
                    if now >= deadline:
                        raise socket.error(errno.EWOULDBLOCK, "timeout")
                    else:
                        s.settimeout(deadline - now)
                try:
                    attempted = True
                    return func(*args, **kwargs)
                except socket.error as e:
                    if e.args[0] == errno.EINTR:
                        continue
                    raise
        finally:
            if timeout:
                s.settimeout(timeout)

    def recv(sock, *args, **kwargs):
        return _retryable_call(sock, sock.recv, *args, **kwargs)

    def recv_into(sock, *args, **kwargs):
        return _retryable_call(sock, sock.recv_into, *args, **kwargs)

    def iteritems(x):
        return x.iteritems()
else:

    def recv(sock, *args, **kwargs):
        return sock.recv(*args, **kwargs)

    def recv_info(sock, *args, **kwargs):
        return sock.recv_info(*args, **kwargs)

    def iteritems(x):
        return iter(x.items())
