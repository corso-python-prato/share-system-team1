#! /usr/bin/env python
# -*- coding: utf-8 -*-

import asyncore
import socket
import json
import struct

"""
Communication system between command manager and client daemon
"""

class CommunicatorSock(asyncore.dispatcher_with_send):

    LENGTH_FORMAT = '!i'

    def _packing_message(self, command_type, param=None):
        cmd_struct = {
            'request': command_type,
            'body': param,
        }
        cmd_struct = json.dumps(cmd_struct)
        pack_size = len(cmd_struct)
        pack_format = '!i{}s'.format(pack_size)
        data = struct.pack(pack_format, pack_size, cmd_struct)
        return data

    def _unpacking_message(self):
        data_length = self.recv(struct.calcsize(self.LENGTH_FORMAT))
        data_length = struct.unpack(self.LENGTH_FORMAT, data_length)
        data = self.recv(data_length[0])
        data = struct.unpack('{}s'.format(data_length[0]), data)
        command = json.loads(data[0])
        return command

    def _executer(self, command):
        pass

    def handle_read(self):
        command = self._unpacking_message()
        self._executer(command)

    def send_message(self, command_type, param=None):
        data = self._packing_message(command_type, param)
        self.send(data)



class CmdMessageHandler(CommunicatorSock):

    def __init__(self, sock, cmd):
        CommunicatorSock.__init__(self, sock)
        self.cmd = cmd

    def _executer(self, command):
        response = self.cmd[command['request']](command["body"])
        self.send_message(command['request'], response)


class CmdMessageServer(asyncore.dispatcher):

    def __init__(self, host, port, cmd):
        asyncore.dispatcher.__init__(self)
        self.cmd = cmd
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(1)

    def handle_accept(self):
        sock, addr = self.accept()
        if sock and addr is not None:
            handler = CmdMessageHandler(sock, self.cmd)


class CmdMessageClient(CommunicatorSock):

    def __init__(self, host, port, cmd_istance):
        CommunicatorSock.__init__(self)
        self.host = host
        self.port = port
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self.cmd_istance = cmd_istance

    def _executer(self, command):
        self.cmd_istance.print_response(command)
