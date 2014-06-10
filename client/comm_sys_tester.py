#! /usr/bin/env python
# -*- coding:utf-8 -*-

from communicaton_system import CmdMessageClient
import json
import struct
import unittest


class TestCmdMessageClient(unittest.TestCase):
	
	def setUp(self):
		self.cmdmessageclient = CmdMessageClient('localhost', 6666)
	
	def test_packing_message(self):
		LENGHT_FORMAT = '!i'
		PACK_FORMAT = '{}89s'.format(LENGHT_FORMAT)
		command_type = "syncronized"
		param = {
					"request" : {},
					"respose" : {"yes" : 201, "no" : "300" ,}, 
				}		
		content = self.cmdmessageclient._packing_message(command_type, param)
		data = struct.unpack(PACK_FORMAT, content)
		data = json.loads(data[1])
		

if __name__ == '__main__':
	unittest.main()