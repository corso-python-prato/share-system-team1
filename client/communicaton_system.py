#! /usr/bin/env python
# -*- coding: utf-8 -*-

import asyncore
import socket
import json
import struct


class CmdMessageHandler(asyncore.dispatcher_with_send):

    LENGTH_FORMAT = '!i'
    PACK_FORMAT = '{}s'.format(LENGTH_FORMAT)

    def __init__(self, sock, cmd):
        asyncore.dispatcher_with_send.__init__(sock)
        self.cmd = cmd

    def handle_read(self):
        data_length = self.recv(struct.calcsize(LENGTH_FORMAT))
        data = self.recv(data_length)
        command = json.loads(data)
        response = self.cmd[command['request']](command["body"])

        response_struct = json.dumps(response)
        pack_size = len(response_struct)
        data = struct.pack(self.PACK_FORMAT, pack_size, response_struct)

        self.send(data)


class CmdMessageServer(asyncore.dispatcher):

    def __init__(self, host, port, cmd):
        asyncore.dispatcher.__init__(self)
        self.cmd = cmd
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, post))
        self.listen(1)

    def handle_accept(self):
        sock, addr = self.accept()
        if sock and addr is not None:
            handler = CmdMessageHandler(sock, cmd)


class CmdMessageClient(asyncore.dispatcher_with_send):

    LENGTH_FORMAT = '!i'
    PACK_FORMAT = '{}89s'.format(LENGTH_FORMAT)

    def __init__(self, host, port):
        asyncore.dispatcher_with_send.__init__(self)
        self.host = host
        self.port = port
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))

    def _packing_message(self, command_type, param=None):
        cmd_struct = {
            'request': command_type,
            'body': param,
        }
        cmd_struct = json.dumps(cmd_struct)
        pack_size = len(cmd_struct)
        data = struct.pack(self.PACK_FORMAT, pack_size, cmd_struct)
        return data

    def _unpacking_message(self, response_data):
        return response_data

    def handle_read(self):
        data_length = self.recv(struct.calcsize(self.LENGTH_FORMAT))
        data = self.recv(data_length)
        response = json.loads(data)
        print response

    def send_message(self, command_type, param=None):
        data = self._packing_message(command_type, param)
        self.send(data)
