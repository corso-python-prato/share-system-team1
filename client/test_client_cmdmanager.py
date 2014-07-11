from client_cmdmanager import RawBoxCmd
import unittest


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

    
if __name__ == "__main__":
    unittest.main()
    