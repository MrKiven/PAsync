# -*- coding: utf-8 -*-

import logging
from SocketServer import TCPServer, StreamRequestHandler, ThreadingMixIn

logger = logging.getLogger(__name__)


class QHandler(StreamRequestHandler):

    def handle(self):
        self.data = self.request.recv(1024)
        self.wfile.write('OK')

        addr = self.request.getpeername()
        logger.info("Got Connection from: {}".format(addr))
        # ack to cilent


# Support multi threading
class QServer(ThreadingMixIn, TCPServer):
    pass


if __name__ == '__main__':
    host, port = "localhost", 1234
    server = QServer((host, port), QHandler)
    logger.info("Start server at {}:{} ...".format(host, port))
    server.serve_forever()
