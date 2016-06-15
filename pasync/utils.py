# -*- coding: utf-8 -*-

import json


#  format `print`
def printf(msg):
    pass


def json_encode(data):
    try:
        return json.dumps(data)
    except ValueError:
        return data


def json_decode(data):
    try:
        return json.loads(data)
    except ValueError:
        return data
