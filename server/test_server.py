#!/usr/bin/env python
#-*- coding: utf-8 -*-


import server
import os
import json
import unittest
import shutil
from base64 import b64encode

TEST_DIRECTORY = "test_users_dirs/"
TEST_USER_DATA = "test_user_data.json"
TEST_PENDING_USERS = "test_user_pending.tmp"

DEMO_USER = "i_am_an_user@rawbox.it"
DEMO_PSW = "very_secret_password"
DEMO_FAKE_USER = "fake_user"
DEMO_CLIENT = None

DEMO_FILE = "somefile.txt"
DEMO_CONTENT = "Hello my dear,\nit's a beautiful day here in Compiobbi."
DEMO_DEST_COPY_PATH = "new_cp"
DEMO_DEST_MOVE_PATH = "new_mv"
NO_SERVER_PATH = "marcoRegna"


def transfer(path, flag=True, test=True):
    client_path, server_path = set_tmp_params(path)
    if flag:
        func = "copy"
        new_path = "{}/{}".format(DEMO_DEST_COPY_PATH, path)
    else:
        func = "move"
        new_path = "{}/{}".format(DEMO_DEST_MOVE_PATH, path)

    if test:
        data = {
            "file_src": client_path,
            "file_dest": os.path.join(new_path, DEMO_FILE)
        }
        rv = DEMO_CLIENT.call("post", "actions/" + func, data)
    else:
        data = {
            "file_src": NO_SERVER_PATH,
            "file_dest": os.path.join(new_path, DEMO_FILE)
        }
        rv = DEMO_CLIENT.call("post", "actions/" + func, data)

    return rv, client_path, server_path


def set_tmp_params(father_dir):
    """ Add a file in user's directory, in the path passed in argument
    Please, use path here with only a word (not "dir/subdir") """
    client_path = os.path.join(father_dir, DEMO_FILE)
    server_path = os.path.join(TEST_DIRECTORY, DEMO_USER, client_path)
    os.makedirs(os.path.dirname(server_path))
    shutil.copy(DEMO_FILE, server_path)

    server_father_path = os.path.join(TEST_DIRECTORY, DEMO_USER, father_dir)
    u = server.User.users[DEMO_USER]
    u.paths[father_dir] = [server_father_path, 0, False]
    u.paths[client_path] = [server_path, 0, 0]

    return client_path, server_path


class EmailTest(unittest.TestCase):

    MAIL_SERVER = "smtp_address"
    MAIL_PORT = "smtp_port"
    MAIL_USERNAME = "smtp_username"
    MAIL_PASSWORD = "smtp_password"
    TESTING = True

    def setUp(self):
        self.app = server.Flask(__name__)
        self.app.config.from_object(__name__)
        self.mail = server.Mail(self.app)
        server.app.config.update(TESTING=True)
        self.tc = server.app.test_client()

        try:
            os.mkdir(TEST_DIRECTORY)
        except OSError:
            shutil.rmtree(TEST_DIRECTORY)
            os.mkdir(TEST_DIRECTORY)

        server.USERS_DIRECTORIES = TEST_DIRECTORY

        server.PENDING_USERS = TEST_PENDING_USERS

        open(TEST_USER_DATA, "w").close()
        server.USERS_DATA = TEST_USER_DATA

        EmailTest.user = "user_mail@demo.it"
        EmailTest.psw = "password_demo"
        EmailTest.code = "5f8e441f01abc7b3e312917efb52cc12"  # os.urandom(16).encode('hex')
        self.url = "".join((server._API_PREFIX, "Users/", EmailTest.user))

    def tearDown(self):
        server.User.users = {}
        if os.path.exists(TEST_PENDING_USERS):
            os.remove(TEST_PENDING_USERS)
        if os.path.exists(TEST_USER_DATA):
            os.remove(TEST_USER_DATA)
        if os.path.exists(TEST_DIRECTORY):
            try:
                os.mkdir(TEST_DIRECTORY)
            except OSError:
                shutil.rmtree(TEST_DIRECTORY)
    def test_mail(self):
        receiver = "test@rawbox.com"
        obj = "test"
        content = "test content"
        with self.mail.record_messages() as outbox:
            server.send_mail(
                receiver,
                obj,
                content
            )
            assert len(outbox) == 1
            assert outbox[0].subject == "test"
            assert outbox[0].body == "test content"

    def test_create_user_mail(self):
        user = "NennoLello"
        psw = "zerocloninell'orto"
        data = {
            "psw": psw
        }

        url = "".join((server._API_PREFIX, "user/", user))
        with self.mail.record_messages() as outbox:
            self.tc.post(url, data=data, headers=None)
            with open(server.PENDING_USERS, "r") as pending_file:
                code = json.load(pending_file)[user]["code"]
                assert outbox[0].body == code
        os.remove(TEST_PENDING_USERS)

                code = json.load(pending_file)[EmailTest.user]["code"]
                self.assertEqual(outbox[0].body, code)
                self.assertEqual(response.status_code, server.HTTP_CREATED)

    def test_activate_user(self):
        fake_pending_user = {}
        fake_pending_user[EmailTest.user] = {
            "password": EmailTest.psw,
            "code": EmailTest.code,
            "timestamp": time.time()}
        with open(TEST_PENDING_USERS, "w") as tmp_file:
            json.dump(fake_pending_user, tmp_file)

        data = {
            "code": EmailTest.code
        }


if __name__ == "__main__":
    # make tests!
    unittest.main()
