#!/usr/bin/env python
#-*- coding: utf-8 -*-

class Message(object):
	"""Nice color prompt manager"""

	_message_type = {
	 	'HEADER': '\033[95m',
		'INFO': '\033[94m',
		'SUCCESS': '\033[92m',
		'WARNING': '\033[93m',
		'ERROR': '\033[91m',
		'ENDC': '\033[0m',
	}

	def __init__(self, color = None, message = None):
		"""Print a color according to the message by __init__"""
		if color and message:
			self.print_color(color, message)

	def print_color(self, color, message):
		"""Print a color according to the message"""
		if color in Message._message_type:
				print Message._message_type[color] , message , Message._message_type['ENDC']
		else: print message

	def color(self, color, message):
		"""Return a colored message"""
		if color in Message._message_type:
			return Message._message_type[color] + message + Message._message_type['ENDC']
		else: print message