# -*- coding: utf-8 -*-

import sys
import logging
from SocketServer import TCPServer, StreamRequestHandler, ThreadingMixIn

from pasync._compat import Full
from pasync.utils import json_decode, json_encode
from pasync.hooks import task_callback_hook
from pasync.q import q, Item

logger = logging.getLogger(__name__)
q.set_maxsize(10)


def task_handler(task, timeout=3):
    try:
        q.put(Item(task), timeout=timeout)
    except Full:
        raise
    ret = 'Successful executed'
    task_callback_hook.send(ret)


class QHandler(StreamRequestHandler):

    def handle(self):
        while True:
            ack = {
                'task_id': None,
                'task_ack': True,
                'msg': None
            }
            task = json_decode(self.request.recv(1024))

            if not task:
                break

            addr = self.request.getpeername()
            logger.info(
                "Got Connection from: {} with task: {}".format(
                    addr, task)
            )
            task_id = task.get('task_id')
            ack['task_id'] = task_id
            try:
                task_handler(task)
            except Full:
                ack['task_ack'] = False
                ack['msg'] = 'Task Queue Is Full!'
            # ack to cilent
            self.wfile.write(json_encode(ack))
        logger.info("Broken connect with: {}".format(self.client_address[0]))


# Support multi threading
class QServer(ThreadingMixIn, TCPServer):
    pass


if __name__ == '__main__':
    host, port = "localhost", 1234
    server = QServer((host, port), QHandler)
    logger.info("Start server at {}:{} ...".format(host, port))
    server.serve_forever()
