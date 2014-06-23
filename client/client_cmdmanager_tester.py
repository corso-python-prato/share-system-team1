from client_cmdmanager import RawBoxCmd
import client_cmdmanager
import unittest
import getpass
import sys


class MockInput(object):

    def __init__(self, *mock_list):
        self.list = list(mock_list)[::-1]

    def mock(self, *args):
        return self.list.pop()


class CmdManagerTest(unittest.TestCase):

    def setUp(self):
        self.command_user = "user"
        self.username = "marco"

    def test_do_create_no_user(self):
        mock_input = MockInput('marco', 'psw', 'psw', "prova@gmail.com")
        client_cmdmanager.raw_input = mock_input.mock
        getpass.getpass = mock_input.mock

        result = RawBoxCmd().do_create(self.command_user)
        self.assertEquals(result, {"email": "prova@gmail.com", "user": "marco", "psw": "psw"})

    def test_do_create_user(self):
        mock_input = MockInput('psw', 'psw', "prova@gmail.com")
        client_cmdmanager.raw_input = mock_input.mock
        getpass.getpass = mock_input.mock

        result = RawBoxCmd().do_create(self.command_user + " " + self.username)
        self.assertEquals(result, {"email": "prova@gmail.com", "user": "marco", "psw": "psw"})
    
if __name__ == '__main__':
    unittest.main()
    