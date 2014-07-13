#!/usr/bin/env python
#-*- coding: utf-8 -*-


class ServerError(Exception):
    pass


class MissingFileError(ServerError):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)
