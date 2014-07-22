#!/usr/bin/env python
#-*- coding: utf-8 -*-

from base64 import b64encode
import unittest
import server
import shutil
import string
import random
import json
import os

from server import _API_PREFIX

TEST_DIRECTORY = "test_users_dirs/"
TEST_USER_DATA = "test_user_data.json"


class TestServerInternalErrors(unittest.TestCase):
    root = os.path.join(
        os.path.dirname(__file__),
        "demo_test/internal_errors"
    )

    def setUp(self):
        server.app.config.update(TESTING=True)
        server.app.testing = True
        # Note: it's possible to make assertRaises on internal server
        # exceptions from the test_client only if app testing is True.

        self.root = TestServerInternalErrors.root
        server.SERVER_ROOT = self.root
        server.server_setup()

        self.user_data = os.path.join(self.root, "user_data.json")
        self.user_dirs = os.path.join(self.root, "user_dirs")
        self.tc = server.app.test_client()

    def tearDown(self):
        try:
            shutil.rmtree(self.user_dirs)
        except OSError:
            pass
        try:
            os.remove(self.user_data)
        except OSError:
            pass

    def test_corrupted_users_data_json(self):
        """
        If the user data file is corrupted, it will be raised a ValueError.
        """
        shutil.copy(
            os.path.join(self.root, "corrupted_user_data.json"),
            self.user_data
        )
        with self.assertRaises(ValueError):
            server.server_setup()

    def test_directory_already_present(self):
        """
        If, creating a new user, after checking his username, a directory with
        his/her name is already present, it will be raised an OSError and
        it will be returned a status code 500.
        """
        username = "papplamoose@500.com"
        try:
            os.makedirs(os.path.join(self.user_dirs, username))
        except OSError:
            shutil.rmtree(self.user_dirs)
            os.makedirs(os.path.join(self.user_dirs, username))

        def try_to_create_user():
            return self.tc.post(
                _API_PREFIX + "create_user",
                data={
                    "user": username,
                    "psw": "omg_it_will_be_raised_an_error!"
                }
            )

        # check if OSError is raised
        with self.assertRaises(OSError):
            try_to_create_user()

        # check if returns 500
        server.app.testing = False
        received = try_to_create_user()
        self.assertEqual(received.status_code, 500)

    def test_access_to_non_existent_server_path(self):
        """
        If a path exists in some user's paths dictionary, but it's not in the
        filesystem, when somebody will try to access it, it will be raised an
        IOError and it will be returned a status code 500.
        """
        owner = "Emilio@me.it"
        owner_headers = make_headers(owner, "password")
        owner_filepath = "ciao.txt"

        # setup
        shutil.copy(
            os.path.join(self.root, "demo_user_data.json"),
            self.user_data
        )
        server.server_setup()

        # 1. case download
        def try_to_download():
            return self.tc.get(
                "{}files/{}".format(_API_PREFIX, owner_filepath),
                headers=owner_headers
            )
        # check IOError
        with self.assertRaises(IOError):
            try_to_download()
        # check service code
        server.app.testing = False
        received = try_to_download()
        self.assertEqual(received.status_code, 500)
        server.app.testing = True

        # 2. case move or copy
        def try_to_transfer(action):
            return self.tc.post(
                "{}actions/{}".format(_API_PREFIX, action),
                data={
                    "file_src": owner_filepath,
                    "file_dest": "transferred.file"
                },
                headers=owner_headers
            )
        # check IOError
        for action in ["move", "copy"]:
            with self.assertRaises(IOError):
                try_to_transfer(action)
        # check service code
        server.app.testing = False
        for action in ["move", "copy"]:
            try_to_transfer(action)
        self.assertEqual(received.status_code, 500)
        server.app.testing = True


if __name__ == '__main__':
    # make tests!
    unittest.main()
