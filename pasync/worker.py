# -*- coding: utf-8 -*-

import socket
from pasync._compat import Empty
from pasync.q import LifoQueue


class Connection(object):

    def __init__(self, host="localhsot", port=1234, socket_timeout=None,
                 socket_connect_timeout=None, socket_keepalive=False,
                 retry_on_time=False):
        pass

    def _init(self):
        self.queue = self.queue_class(self.qsize)
        self._connect()

    def _connect(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.host, self.port))

    def send(self, data):
        if self.client is None:
            raise RuntimeError("Client has not created!!")
        try:
            self.client.sendall(data)
            received = self.client.recv(1024)
            self.queue.put(received)
        except Exception:
            raise

    def result(self):
        try:
            return self.queue.get(timeout=self.timeout)
        except Empty:
            raise ValueError("Queue is empty!!")
