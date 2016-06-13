# -*- coding: utf-8 -*-

from pasync import QServer, QHandler

HOST, PORT = ("localhost", 1234)

import logging
logger = logging.getLogger(__name__)


server = QServer((HOST, PORT), QHandler)
server.serve_forever()
