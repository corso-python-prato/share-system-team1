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

    def test_create_user_email(self):
        data = {
            "psw": EmailTest.psw
        }

        with self.mail.record_messages() as outbox:
            self.tc.post(self.url, data=data, headers=None)
            with open(server.PENDING_USERS, "r") as pending_file:
                code = json.load(pending_file)[EmailTest.user]["code"]
                self.assertEqual(outbox[0].body, code)


class UserActions(unittest.TestCase):

    def inject_user(self, inject_dest, user, psw=None, code=None):
        underskin_user = {}

        if not os.path.exists(inject_dest):
            open(inject_dest, "w").close()

        if os.path.getsize(inject_dest) > 0:
            with open(inject_dest, "r") as tmp_file:
                underskin_user = json.load(tmp_file)

        if inject_dest == TEST_PENDING_USERS:
            underskin_user[user] = {
                "password": psw,
                "code": code,
                "timestamp": time.time()}
            with open(inject_dest, "w") as tmp_file:
                json.dump(underskin_user, tmp_file)

        if inject_dest == TEST_USER_DATA:
            underskin_user[user] = {
                "paths": {"": ["user_dirs/fake_root", False, 1405197042.793583]},
                "psw": psw,
                "timestamp": 1405197042.793476
            }
            server.User.users = underskin_user
            with open(inject_dest, "w") as tmp_file:
                json.dump(underskin_user, tmp_file)

    def setUp(self):
        self.app = server.Flask(__name__)
        self.app.config.from_object(__name__)
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

        UserActions.user = "user_mail@demo.it"
        UserActions.psw = "password_demo"
        UserActions.code = "5f8e441f01abc7b3e312917efb52cc12"  # os.urandom(16).encode('hex')
        self.url = "".join((server._API_PREFIX, "Users/", UserActions.user))

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

    def test_create_user(self):
        data = {
            "psw": UserActions.psw
        }

        response = self.tc.post(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_CREATED)

        with open(server.PENDING_USERS, "r") as pending_file:
            data = json.load(pending_file)
            user = data.keys()[0]
            self.assertEqual(user, UserActions.user)
            psw = data[UserActions.user]["password"]
            self.assertTrue(sha256_crypt.verify(UserActions.psw, psw))
            code = data[UserActions.user]["code"]
            self.assertIsNotNone(code)
            self.assertEqual(len(code), 32)
            timestamp = data[UserActions.user]["timestamp"]
            self.assertIsNotNone(timestamp)

    def test_create_user_missing_password(self):
        data = {}

        self.inject_user(TEST_USER_DATA, UserActions.user, UserActions.psw)
        response = self.tc.post(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_BAD_REQUEST)

    def test_create_user_that_is_arleady_pending(self):
        data = {
            "psw": UserActions.psw
        }

        self.inject_user(TEST_PENDING_USERS, UserActions.user, UserActions.psw)
        response = self.tc.post(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_CONFLICT)

    def test_create_user_that_is_arleady_active(self):
        data = {
            "psw": UserActions.psw
        }

        self.inject_user(TEST_USER_DATA, UserActions.user, UserActions.psw)
        response = self.tc.post(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_CONFLICT)

    def test_activate_user(self):

        data = {
            "code": UserActions.code
        }

        self.inject_user(TEST_PENDING_USERS, UserActions.user, UserActions.psw, UserActions.code)
        response = self.tc.put(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_CREATED)

    def test_activate_user_missing_code(self):

        data = {}

        self.inject_user(TEST_PENDING_USERS, UserActions.user, UserActions.psw)
        response = self.tc.put(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_BAD_REQUEST)

    def test_activate_user_that_is_arleady_active(self):
        data = {
            "code": UserActions.code
        }

        self.inject_user(TEST_USER_DATA, UserActions.user, UserActions.psw, UserActions.code)
        response = self.tc.put(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_CONFLICT)


if __name__ == "__main__":
    # make tests!
    unittest.main()
