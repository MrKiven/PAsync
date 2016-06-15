# -*- coding: utf-8 -*-

import json


#  format `print`
def printf(msg):
    pass


def json_encode(obj):
    try:
        return json.dumps(obj)
    except ValueError:
        return obj


def json_decode(obj):
    try:
        return json.loads(obj)
    except ValueError:
        return obj
