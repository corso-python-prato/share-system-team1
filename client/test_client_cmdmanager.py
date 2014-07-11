from client_cmdmanager import RawBoxCmd
from client_cmdmanager import RawBoxExecuter
import unittest

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


class TestRawBoxExecuter(unittest.TestCase):

    def setUp(self):
        self.comm_sock = MockCmdMessageClient()
        self.correct_user = "user@server.it"
        self.wrong_user0 = "user"       # no "@" and no final ".something"
        self.wrong_user1 = "@ceoijeo"   # nothing before "@" and no final ".something"
        self.wrong_user2 = ".user"      # nothing before "@" no "@" nothing after "@"
        self.wrong_user3 = "user.it"    # nothing before "@" and no "@"
        self.correct_pwd = "password"
        self.wrong_pwd = "pawssworowd"
        self.correct_code = "9fe2598cc1721ee1a61f5f1fclungo32"
        self.tooshort_code = "123tinycode123"
        self.toolong_code = "questocodiceeveramentelunghissimo111109091230191209"
        self.raw_box_exec = RawBoxExecuter(self.comm_sock)
        TestRawBoxExecuter.username = "empty"
        TestRawBoxExecuter.psw = "empty"
        TestRawBoxExecuter.code = "empty"

    def test_create_user(self):
        mock_input.append(self.correct_pwd)
        mock_input.append(self.correct_pwd)

        mock_input.append(self.correct_user)

        self.raw_box_exec._create_user()

        self.assertEquals(TestRawBoxExecuter.username, self.correct_user)
        self.assertEquals(TestRawBoxExecuter.psw, self.correct_pwd)
    def test_create_user_invalid_email(self):
        mock_input.append(self.correct_pwd)
        mock_input.append(self.correct_pwd)

        mock_input.append(self.correct_user)
        mock_input.append(self.wrong_user3)
        mock_input.append(self.wrong_user2)
        mock_input.append(self.wrong_user1)
        mock_input.append(self.wrong_user0)

        self.raw_box_exec._create_user()

        self.assertNotEquals(TestRawBoxExecuter.username, self.wrong_user0)
        self.assertNotEquals(TestRawBoxExecuter.username, self.wrong_user1)
        self.assertNotEquals(TestRawBoxExecuter.username, self.wrong_user2)
        self.assertNotEquals(TestRawBoxExecuter.username, self.wrong_user3)
        self.assertEquals(TestRawBoxExecuter.username, self.correct_user)


if __name__ == '__main__':
    unittest.main()
    