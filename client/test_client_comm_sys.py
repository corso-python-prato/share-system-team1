#! /usr/bin/env python
# -*- coding: utf-8 -*-

from communicaton_system import CmdMessageClient
import unittest
import asyncore
import socket
import struct
import json
import threading


class AsyncorePoller(threading.Thread):
    def __init__(self):
        super(AsyncorePoller, self).__init__()
        self.continue_running = True

    def run(self):
        while self.continue_running:
            asyncore.poll()

    def stop(self):
        self.continue_running = False


class TestServerSock(asyncore.dispatcher_with_send):

    def __init__(self, sock, callback):
        asyncore.disparcher_with_send.__init__(self, sock)
        self.check = callback

    def handle_read(self):
        data = self.recv(1024)
        self.check(data)


class TestServer(asyncore.dispatcher):
    def __init__(self):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(('localhost', 6666))
        self.listen(1)
        
    def callback_inizializator(self, callback):
        self.test_callback = callback

    def handle_accept(self):
        sock, addr = self.accept()
        if sock and addr is not None:
            comm_sock = TestServerSock(sock, self.test_callback)


class TestCmdMessageClient(unittest.TestCase):

    def setUp(self):
        self.test_server_sock = TestServer()
        self.async_poller = AsyncorePoller()
        self.async_poller.start()


    def tearDown(self):
        self.test_server_sock.close()
        self.async_poller.stop()

    def test_socket_send(self):
        def check_pkt_callback(data):
            header, pkt = struct.unpack('!is')
            self.assertEqual(header, len(pkt))
            data_struct = json.loads(pkt)
            expected_value = {
            'request': 'test_cmd',
            'body': {
                'param1': 'value1',
                'param2': 'value2',
                }
            }
            self.assertEqual(data_struct, expected_value)

        self.test_server_sock.callback_inizializator(check_pkt_callback)
        self.cmd_client = CmdMessageClient('localhost', 6666)

        test_request = 'test_cmd'
        test_body = {
            'param1': 'value1',
            'param2': 'value2',
        }

        self.cmd_client.send_message(test_request, test_body)
        self.cmd_client.close()

if __name__ == '__main__':
    unittest.main()