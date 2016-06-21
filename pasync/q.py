# -*- coding: utf-8 -*-

import heapq
from pasync._compat import Queue


class Q(Queue):
    """Priority Queue (lowest first)
    If priority is same, then first in first.
    """
    def _init(self, maxsize):
        self.queue = []
        self._index = 0

    def _qsize(self):
        return len(self.queue)

    def _put(self, item):
        _item = (-item.priority, self._index, item)
        heapq.heappush(self.queue, _item)
        self._index += 1

    def _get(self):
        return heapq.heappop(self.queue)[-1]


class Item(object):
    """Data Struct
    Data with priority to put in `Q`
    """
    def __init__(self, data, priority=0):
        self.data = data
        self.priority = priority

    def __repr__(self):
        return "Item({!r}, {!r})".format(self.data, self.priority)
