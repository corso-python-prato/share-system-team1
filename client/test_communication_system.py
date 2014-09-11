#! /usr/bin/env python
# -*- coding:utf-8 -*-

import unittest
import struct
import json

import communication_system


class TestCmdMessageClient(unittest.TestCase):

    def setUp(self):
        self.command_type = u'synchronized'
        self.param = {
            u'request': {},
            u'respose': {u'yes': 201, u'no': u'300', },
        }
        self.cmd_struct = {
            u'request': self.command_type,
            u'body': self.param,
        }

    def test_packing_message(self):
        content = communication_system.packing_message(self.command_type, self.param)
        pack_format = '!i{}s'.format(len(content) - struct.calcsize('i'))
        length, data = struct.unpack(pack_format, content)
        data = json.loads(data)
        self.assertEqual(self.cmd_struct, data)

    def test_unpacking_message(self):
        cmd_struct = json.dumps(self.cmd_struct)
        pack_size = len(cmd_struct)
        data = struct.pack('!i', pack_size)
        length = communication_system.unpacking_message(data)
        self.assertEqual(length, pack_size)
        pack_format = '!{}s'.format(pack_size)
        data = struct.pack(pack_format, cmd_struct)
        command = communication_system.unpacking_message(data, pack_format)
        self.assertEqual(command, self.cmd_struct)

    def test_command_not_found(self):
        self.assertEqual(
            {'result': 'error', 'details': ['command not found']},
            communication_system.command_not_found('wrong_command'))
      
        
if __name__ == '__main__':
    unittest.main()
