#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest
import os

from client_cmdmanager import RawBoxExecuter
from client_cmdmanager import RawBoxCmd
import client_cmdmanager

CONFIG_DEMO = os.path.join(os.path.dirname(__file__), "demo_test/config.ini")
mock_input = []


def mock_take_input(message, password=False):
    """override client_cmdmanager.take_input
    to bypass the raw input in client_cmdmanager"""
    return mock_input.pop()
client_cmdmanager.take_input = mock_take_input


def mock_print_response(a, b):
    pass
RawBoxExecuter.print_response = mock_print_response


def mock_check_shareable_path(path):
    """used for testing do_add_share,
    do_remove_share, do_remove_beneficiary"""
    return True


class MockCmdMessageClient(object):

    def send_message(self, _, param):
        """override comm_sock.send_message to intercept data sended
        to the socket
        param {
            'user': <username>
            'psw': <password>
            'code': <32 character alfanumeric code>
        }
        code and psw are used only respectively in
        activate_user and create_user
        """
        TestRawBoxExecuter.username = param.get('user')
        TestRawBoxExecuter.psw = param.get('psw', "empty")
        TestRawBoxExecuter.code = param.get('code', "empty")
        TestRawBoxExecuter.pathtoshare = param.get('path')
        TestRawBoxExecuter.beneficiary = param.get('beneficiary')

    def read_message(self):
        """override comm_sock.read_message
        it's useless for testing"""
        pass


class MockExecuter(object):
    def _create_user(self, username):
        RawBoxCmdTest.called = True

    def _activate_user(self, username, code):
        RawBoxCmdTest.called = True

    def _delete_user(self):
        RawBoxCmdTest.called = True

    def _add_share(self, path, beneficiary):
        RawBoxCmdTest.called = True

    def _remove_share(self, path):
        RawBoxCmdTest.called = True

    def _remove_beneficiary(self, path, beneficiary):
        RawBoxCmdTest.called = True

    def _get_shares_list(self):
        RawBoxCmdTest.called = True


class CheckShareablePathTest(unittest.TestCase):
    def setUp(self):
        self.config_bak = client_cmdmanager.FILE_CONFIG
        client_cmdmanager.CONFIG.read(CONFIG_DEMO)

    def tearDown(self):
        client_cmdmanager.CONFIG.read(self.config_bak)

    def test_check_shareable_path(self):
        resp = client_cmdmanager.check_shareable_path(".")
        self.assertTrue(resp)
        resp = client_cmdmanager.check_shareable_path("/withslashes/")
        self.assertFalse(resp)
        resp = client_cmdmanager.check_shareable_path("inexistent")
        self.assertFalse(resp)


class RawBoxCmdTest(unittest.TestCase):

    def setUp(self):
        self.executer = MockExecuter()
        self.rawbox_cmd = RawBoxCmd(self.executer)
        client_cmdmanager.check_shareable_path = mock_check_shareable_path
        RawBoxCmdTest.called = False

    def test_do_create(self):
        self.rawbox_cmd.onecmd('create user pippo@pippa.it')
        self.assertTrue(RawBoxCmdTest.called)

    def test_do_activate(self):
        self.rawbox_cmd.onecmd('activate pippo@pippa.it code=codice')
        self.assertTrue(RawBoxCmdTest.called)

    def test_do_delete(self):
        mock_input.append('yes')
        self.rawbox_cmd.onecmd('delete')
        self.assertTrue(RawBoxCmdTest.called)

    def test_do_add_share(self):
        self.rawbox_cmd.onecmd('add_share shared_folder beneficiary')
        self.assertTrue(RawBoxCmdTest.called)

    def test_do_remove_share(self):
        self.rawbox_cmd.onecmd('remove_share shared_folder')
        self.assertTrue(RawBoxCmdTest.called)

    def test_do_remove_beneficiary(self):
        mock_input.append('y')
        self.rawbox_cmd.onecmd('remove_beneficiary shared_folder beneficiary')
        self.assertTrue(RawBoxCmdTest.called)

    def test_do_get_shares_list(self):
        self.rawbox_cmd.onecmd('get_shares_list')
        self.assertTrue(RawBoxCmdTest.called)


class TestRawBoxExecuter(unittest.TestCase):
    def setUp(self):
        self.comm_sock = MockCmdMessageClient()
        self.correct_user = "user@server.it"

        # no "@" and no final ".something"
        self.wrong_user0 = "user"

        # nothing before "@" and no final ".something"
        self.wrong_user1 = "@ceoijeo"

        # nothing before "@" no "@" nothing after "@"
        self.wrong_user2 = ".user"

        # nothing before "@" and no "@"
        self.wrong_user3 = "user.it"

        self.correct_pwd = "33>Password!"
        self.wrong_pwd = "pawssworowd"
        self.correct_code = "9fe2598cc1721ee1a61f5f1fclungo32"
        self.tooshort_code = "123tinycode123"
        self.toolong_code = "questocodiceeveramentelunghissimo1111090912301919"
        self.raw_box_exec = RawBoxExecuter(self.comm_sock)
        TestRawBoxExecuter.username = "empty"
        TestRawBoxExecuter.psw = "empty"
        TestRawBoxExecuter.code = "empty"
        TestRawBoxExecuter.pathtoshare = ""
        TestRawBoxExecuter.ben = ""
        self.pathtoshare = "mypath"
        self.beneficiary = "friend"

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

    def test_create_user_wrong_psw(self):
        mock_input.append(self.correct_pwd)
        mock_input.append(self.wrong_pwd)

        mock_input.append(self.wrong_pwd)
        mock_input.append(self.correct_pwd)

        mock_input.append(self.correct_pwd)
        mock_input.append(self.correct_pwd)

        mock_input.append(self.correct_user)

        self.raw_box_exec._create_user()

        self.assertNotEquals(TestRawBoxExecuter.psw, self.wrong_pwd)
        self.assertEquals(TestRawBoxExecuter.psw, self.correct_pwd)

    def test_activate_user(self):
        mock_input.append(self.correct_code)
        mock_input.append(self.correct_user)

        self.raw_box_exec._activate_user()

        self.assertEquals(TestRawBoxExecuter.code, self.correct_code)

    def test_activate_user_invalid_email(self):
        mock_input.append(self.correct_code)

        mock_input.append(self.correct_user)
        mock_input.append(self.wrong_user3)
        mock_input.append(self.wrong_user2)
        mock_input.append(self.wrong_user1)
        mock_input.append(self.wrong_user0)

        self.raw_box_exec._activate_user()

        self.assertNotEquals(TestRawBoxExecuter.username, self.wrong_user0)
        self.assertNotEquals(TestRawBoxExecuter.username, self.wrong_user1)
        self.assertNotEquals(TestRawBoxExecuter.username, self.wrong_user2)
        self.assertNotEquals(TestRawBoxExecuter.username, self.wrong_user3)
        self.assertEquals(TestRawBoxExecuter.username, self.correct_user)

    def test_activate_user_invalid_code(self):
        mock_input.append(self.correct_code)
        mock_input.append(self.tooshort_code)
        mock_input.append(self.toolong_code)

        mock_input.append(self.correct_user)

        self.raw_box_exec._activate_user()

        self.assertNotEquals(TestRawBoxExecuter.code, self.toolong_code)
        self.assertNotEquals(TestRawBoxExecuter.code, self.tooshort_code)
        self.assertEquals(TestRawBoxExecuter.code, self.correct_code)

    def test_add_share(self):
        self.raw_box_exec._add_share(self.pathtoshare, self.beneficiary)
        self.assertEquals(TestRawBoxExecuter.pathtoshare, self.pathtoshare)
        self.assertEquals(TestRawBoxExecuter.beneficiary, self.beneficiary)

    def test_remove_share(self):
        self.raw_box_exec._remove_share(self.pathtoshare)
        self.assertEquals(TestRawBoxExecuter.pathtoshare, self.pathtoshare)

    def test_remove_beneficiary(self):
        self.raw_box_exec._remove_beneficiary(self.pathtoshare, self.beneficiary)
        self.assertEquals(TestRawBoxExecuter.pathtoshare, self.pathtoshare)
        self.assertEquals(TestRawBoxExecuter.beneficiary, self.beneficiary)


if __name__ == '__main__':
    unittest.main()
