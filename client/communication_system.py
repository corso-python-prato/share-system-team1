#! /usr/bin/env python
# -*- coding: utf-8 -*-

import asyncore
import socket
import struct
import json

"""
Communication system between command manager and client daemon
"""

LENGTH_FORMAT = '!i'


def packing_message(command_type, param=None):
    """
    Create pkt with 4 byte header(which contains data length) and data
    """
    cmd_struct = {
        'request': command_type,
        'body': param,
    }
    cmd_struct = json.dumps(cmd_struct)
    pack_size = len(cmd_struct)
    pack_format = '!i{}s'.format(pack_size)
    data = struct.pack(pack_format, pack_size, cmd_struct)
    return data


def unpacking_message(data, format=LENGTH_FORMAT):
    """
    Returns data lenght o data content
    """
    pkts = struct.unpack(format, data)
    data = pkts[0]
    if format != LENGTH_FORMAT:
        data = json.loads(data)
    return data


def command_not_found(command):
    '''
        basic resposnse for command not found error
        return dictionary with result and details key
    '''
    return {'result': 'error', 'details': ['command not found']}


class CommunicatorSock(asyncore.dispatcher_with_send):

    def _executer(self, command):
        pass

    def handle_read(self):
        header = self.recv(struct.calcsize(LENGTH_FORMAT))
        if header == '':
            ''' disconnection detect:
                recv return a void string for disconnection event
            '''
            return
        data_length = unpacking_message(header)
        data = self.recv(data_length)
        command = unpacking_message(data, '!{}s'.format(data_length))
        response = self._executer(command)
        self.send_message(command['request'], response)

    def send_message(self, command_type, param=None):
        data = packing_message(command_type, param)
        self.send(data)


class CmdMessageHandler(CommunicatorSock):

    def __init__(self, sock, cmd):
        CommunicatorSock.__init__(self, sock)
        self.cmd = cmd

    def _executer(self, command):
        return self.cmd.get(
            command['request'],
            command_not_found)(command["body"])


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
    """Blocking client socket for synchronous communication"""

    def __init__(self, host, port):
        CommunicatorSock.__init__(self)
        self.host = host
        self.port = port
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(1)
        self.connect((host, port))

    def read_message(self):
        """Synchronous read message metod"""
        header = self.recv(struct.calcsize(LENGTH_FORMAT))
        data_length = unpacking_message(header)
        data = self.recv(data_length)
        command = unpacking_message(data, '!{}s'.format(data_length))
        return command
