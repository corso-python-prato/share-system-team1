from client_cmdmanager import RawBoxCmd
from client_cmdmanager import RawBoxExecuter
import client_cmdmanager
import unittest
import getpass
import sys

mock_input = []

def mock_take_input(message, password=False):
    #print message
    return mock_input.pop()

def mock_print_response(a, b):
        pass

client_cmdmanager.take_input = mock_take_input
RawBoxExecuter.print_response = mock_print_response


class MockCmdMessageClient(object):

    def send_message(self, command_type, param):
        return command_type, param

    def read_message(self):
        pass


class CmdManagerTest(unittest.TestCase):

    def setUp(self):
        self.command_user = "user"
        self.username = "marco"

    # def test_do_create_no_user(self):
    #     mock_input = MockInput('marco', 'psw', 'psw', "prova@gmail.com")
    #     client_cmdmanager.raw_input = mock_input.mock
    #     getpass.getpass = mock_input.mock

    #     result = RawBoxCmd().do_create(self.command_user)
    #     self.assertEquals(result, {"email": "prova@gmail.com", "user": "marco", "psw": "psw"})

    # def test_do_create_user(self):
    #     mock_input = MockInput('psw', 'psw', "prova@gmail.com")
    #     client_cmdmanager.raw_input = mock_input.mock
    #     getpass.getpass = mock_input.mock

    #     result = RawBoxCmd().do_create(self.command_user + " " + self.username)
    #     self.assertEquals(result, {"email": "prova@gmail.com", "user": "marco", "psw": "psw"})

class TestRawBoxExecuter(unittest.TestCase):

    def setUp(self):
        self.comm_sock = MockCmdMessageClient()
        self.correct_user = "user@server.it"
        self.wrong_user = "user"
        self.correct_pwd = "password"
        self.wrong_pwd = "pawssworowd"
        self.raw_box_exec = RawBoxExecuter(self.comm_sock)

    def test_create_user(self):
        mock_input.append(self.correct_pwd)
        mock_input.append(self.correct_pwd)
        mock_input.append(self.correct_user)
        username, password = self.raw_box_exec._create_user()
        self.assertEquals(username, self.correct_user)
        self.assertEquals(password, self.correct_pwd)


if __name__ == '__main__':
    unittest.main()
    