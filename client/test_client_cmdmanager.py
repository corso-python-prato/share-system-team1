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


class MockExecuter(object):

    def _create_user(self, username):
        RawBoxCmdTest.called = True

    def _activate_user(self, username, code):
        RawBoxCmdTest.called = True

    def _delete_user(self, username):
        RawBoxCmdTest.called = True


class RawBoxCmdTest(unittest.TestCase):

    def setUp(self):
        self.executer = MockExecuter()
        self.rawbox_cmd = RawBoxCmd(self.executer)
        RawBoxCmdTest.called = False

    def test_do_create(self):
        self.rawbox_cmd.onecmd('create user pippo@pippa.it')
        self.assertTrue(RawBoxCmdTest.called)

    def test_do_activate(self):
        self.rawbox_cmd.onecmd('activate pippo@pippa.it code=codice')
        self.assertTrue(RawBoxCmdTest.called)

    def test_do_delete(self):
        self.rawbox_cmd.onecmd('delete pippo@pippa.it')
        self.assertTrue(RawBoxCmdTest.called)



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
    
if __name__ == '__main__':
    unittest.main()
    