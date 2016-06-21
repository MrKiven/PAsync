# -*- coding: utf-8 -*-


class TaskHandlerHook(object):
    def __init__(self, name):
        self.name = name
        self.callbacks = []

    def register(self, callback):
        self.callbacks.append(callback)

    def send(self, *args, **kwargs):
        for c in self.callbacks:
            try:
                c(*args, **kwargs)
            except Exception:
                raise

    def clear(self):
        self.callbacks = []

task_callback_hook = TaskHandlerHook('task')
