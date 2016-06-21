# -*- coding: utf-8 -*-

import logging
from SocketServer import TCPServer, StreamRequestHandler, ThreadingMixIn

from pasync.utils import json_decode, json_encode
from pasync.hooks import task_callback_hook

logger = logging.getLogger(__name__)

ACK = {
    'task_id': None,
    'task_ack': True
}


def task_handler(task):
    ret = 'Successful executed'
    task_callback_hook.send(ret)


class QHandler(StreamRequestHandler):

    def handle(self):
        while True:
            task = json_decode(self.request.recv(1024))

            if not task:
                break

            addr = self.request.getpeername()
            logger.info(
                "Got Connection from: {} with task: {}".format(
                    addr, task)
            )
            task_id = task.get('task_id')
            ACK['task_id'] = task_id
            # ack to cilent
            self.wfile.write(json_encode(ACK))
            task_handler(task)
        logger.info("Broken connect with: {}".format(self.client_address[0]))


# Support multi threading
class QServer(ThreadingMixIn, TCPServer):
    pass


if __name__ == '__main__':
    host, port = "localhost", 1234
    server = QServer((host, port), QHandler)
    logger.info("Start server at {}:{} ...".format(host, port))
    server.serve_forever()
