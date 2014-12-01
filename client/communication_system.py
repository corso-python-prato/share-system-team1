#! /usr/bin/env python
# -*- coding: utf-8 -*-

import asyncore
import socket
import struct
import json

"""Communication system between command manager and client daemon."""

LENGTH_FORMAT = '!i'


def packing_message(command_type, param=None):
    """This function create the request structure, a packet with 4 byte header(which contains data length) and data
    @param command_type This is the command to be executed
    @param param It contains the params for the command, set to None as default
    @return data It is a struct containing a json with the request inside
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


def unpacking_message(packet, format=LENGTH_FORMAT):
    """This function extract the request structure from the packet
    @param packet Message to unpack
    @param format Transmission format
    @return data Interpreted packet data
    """
    unpacked = struct.unpack(format, packet)
    data = unpacked[0]
    if format != LENGTH_FORMAT:
        data = json.loads(data)
    return data


def command_not_found(command):
    """This function handles a basic response for command not found error
    @param command This is the command to be executed
    @return A dictionary with result and details key
    """
    return {'result': 'error', 'details': ['command not found']}


class CommunicatorSock(asyncore.dispatcher_with_send):

    def _executer(self, command):
        """This function handles the command execution
        @param command
        """
        pass

    def handle_read(self):
        """This function handles a read call on the socket channel
        @return If a disconnection is detected a void string is returned
        """
        header = self.recv(struct.calcsize(LENGTH_FORMAT))
        if header == '':
            return
        data_length = unpacking_message(header)
        data = self.recv(data_length)
        command = unpacking_message(data, '!{}s'.format(data_length))
        response = self._executer(command)
        self.send_message(command['request'], response)

    def send_message(self, command_type, param=None):
        """This function creates a packet and send it to the server
        @param command_type This is the command to be executed
        @param param It contains the params for the command, set to None as default
        """
        data = packing_message(command_type, param)
        self.send(data)


class CmdMessageHandler(CommunicatorSock):

    def __init__(self, sock, cmd):
        """The constructor
        @param sock
        @param cmd
        """
        CommunicatorSock.__init__(self, sock)
        self.cmd = cmd

    def _executer(self, command):
        """This function handles the command execution
        @return 
        """
        return self.cmd.get(
            command['request'],
            command_not_found)(command["body"])


class CmdMessageServer(asyncore.dispatcher):

    def __init__(self, host, port, cmd):
        """The constructor
        @param host
        @param port
        @param cmd
        """
        asyncore.dispatcher.__init__(self)
        self.cmd = cmd
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(1)

    def handle_accept(self):
        """This function is called when a connection can be estabilished
        """
        sock, addr = self.accept()
        if sock and addr is not None:
            handler = CmdMessageHandler(sock, self.cmd)


class CmdMessageClient(CommunicatorSock):
    """Blocking client socket for synchronous communication"""

    def __init__(self, host, port):
        """The constructor
        @param host
        @param port
        """
        CommunicatorSock.__init__(self)
        self.host = host
        self.port = port
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(1)
        self.connect((host, port))

    def read_message(self):
        """This function handles the synchronous read of a message"""
        header = self.recv(struct.calcsize(LENGTH_FORMAT))
        data_length = unpacking_message(header)
        data = self.recv(data_length)
        command = unpacking_message(data, '!{}s'.format(data_length))
        return command
