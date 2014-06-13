#! /usr/bin/env python
# -*- coding:utf-8 -*-

from communicaton_system import CommunicatorSock
import json
import struct
import unittest


class TestCmdMessageClient(unittest.TestCase):

    def setUp(self):
        self.communicator_sock = CommunicatorSock()
        self.command_type = "syncronized"
        self.param = {
            "request": {},
            "respose": {"yes": 201, "no": "300", },
        }

    def test_packing_message(self):
        content = self.communicator_sock._packing_message(self.command_type, self.param)
        pack_format = '!i{}s'.format(len(content) - struct.calcsize('i'))
        length, data = struct.unpack(pack_format, content)
        data = json.loads(data)

    def test_unpacking_message(self):
        cmd_struct = {
            'request': self.command_type,
            'body': self.param,
        }
        cmd_struct = json.dumps(cmd_struct)
        pack_size = len(cmd_struct)
        data = struct.pack('!i', pack_size)
        length = self.communicator_sock._unpacking_message(data)
        pack_format = '!i{}s'.format(pack_size)
        data = struct.pack(pack_format, pack_size, cmd_struct)
        command = self.communicator_sock._unpacking_message(data, pack_format)
      
        
if __name__ == '__main__':
    unittest.main()
