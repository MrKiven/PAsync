# -*- coding: utf-8 -*-


class BaseWorker(object):

    def __init__(self, host="localhost", port=1234, **kwargs):
        self.host = host
        self.port = port
        self.kwargs = kwargs

    def send_task(self, task, ack=True):
        raise NotImplementedError

    def task_result(self, timeout=5):
        raise NotImplementedError
