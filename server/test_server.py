#!/usr/bin/env python
#-*- coding: utf-8 -*-

import time
import server
import os
import json
import unittest
import shutil

TEST_DIRECTORY = "test_users_dirs/"
TEST_USER_DATA = "test_user_data.json"
TEST_PENDING_USERS = "test_user_pending.tmp"


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

        server.PENDING_USERS = TEST_PENDING_USERS

        EmailTest.email = "test@rawbox.com"
        EmailTest.obj = "test"
        EmailTest.content = "test content"

        EmailTest.user = "user_mail@demo.it"
        EmailTest.psw = "password_demo"
        EmailTest.code = "5f8e441f01abc7b3e312917efb52cc12"  # os.urandom(16).encode('hex')
        self.url = "".join((server._API_PREFIX, "Users/", EmailTest.user))

    def tearDown(self):
        server.User.users = {}
        if os.path.exists(TEST_PENDING_USERS):
            os.remove(TEST_PENDING_USERS)

    def test_mail_correct_data(self):
        with self.mail.record_messages() as outbox:
            server.send_mail(
                EmailTest.email,
                EmailTest.obj,
                EmailTest.content
            )
            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, EmailTest.obj)
            self.assertEqual(outbox[0].body, EmailTest.content)

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
        data = {
            "psw": EmailTest.psw
        }

        with self.mail.record_messages() as outbox:
            response = self.tc.post(self.url, data=data, headers=None)
            with open(server.PENDING_USERS, "r") as pending_file:
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
