# -*- coding: utf-8 -*-

import logging

from pasync.server import QServer, QHandler

logger = logging.getLogger(__name__)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(
    logging.Formatter('[PASYNC %(levelname)-7s] %(message)s'))
logger.addHandler(console)
logger.setLevel(logging.INFO)

version_info = (0, 0, 1)
__version__ = ".".join([str(v) for v in version_info])


__all__ = ["QServer", "QHandler", "__version__"]
