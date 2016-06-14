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
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO
    else:
        from io import BytesIO
    def iteritems(x):
        return x.iteritems()
else:
    def iteritems(x):
        return iter(x.items())
