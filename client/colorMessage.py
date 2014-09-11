#!/usr/bin/env python
#-*- coding: utf-8 -*-

from colorama import init as windows_init
import platform
import json


class Message(object):
    """Nice color prompt manager for Linux and windows"""
    _json_config = 'layout_config.json'
    message_color = {
        'HEADER':   'MAGENTA',
        'INFO':     'BLUE',
        'SUCCESS':  'GREEN',
        'WARNING':  'YELLOW',
        'ERROR':    'RED',
        'ENDC':     'WHITE'
    }
    _default_color = {
        'MAGENTA':  {'Linux': '\033[95m', 'Windows': '\x1b[35m'},
        'BLUE':     {'Linux': '\033[94m', 'Windows': '\x1b[36m'},
        'GREEN':    {'Linux': '\033[92m', 'Windows': '\x1b[32m'},
        'YELLOW':   {'Linux': '\033[93m', 'Windows': '\x1b[33m'},
        'RED':      {'Linux': '\033[91m', 'Windows': '\x1b[31m'},
        'WHITE':    {'Linux': '\033[0m' , 'Windows': '\x1b[37m'},
    }

    def __init__(self, color=None, message=None):
        """Print a color according to the message by __init__"""
        self.platform = platform.system()

        if self.platform == 'Windows':
            windows_init()

        if color and message:
            self.print_color(color, message)

        try:
            Message.message_color = json.load(open(Message._json_config))
        except IOError:
            json.dump(Message.message_color, open(Message._json_config, 'w'))

    def print_color(self, color, message):
        """Print a color according to the message"""
        if color in Message.message_color:
            pcolor, endpcolor = Message.message_color[color], Message.message_color['ENDC']
            print Message._default_color[pcolor][self.platform]
            print message
            print Message._default_color[endpcolor][self.platform]
        else:
            print message

    def color(self, color, message):
        """Return a colored message"""
        if color in Message.message_color:
            pcolor, endpcolor = Message.message_color[color], Message.message_color['ENDC']
            return Message._default_color[pcolor][self.platform] + message + Message._default_color[endpcolor][self.platform]
        else:
            print message
