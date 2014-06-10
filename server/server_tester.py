#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
import server
import string
import random
import unittest
import shutil
from base64 import b64encode

TEST_DIRECTORY = "test_users_dirs/"


class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        server.app.testing = True
        server.USERS_DIRECTORIES = TEST_DIRECTORY


    def user_demo(self, user="Gianni", psw="linux"):
        # self.client.preserve_context = False
        with server.app.test_client() as tc:
            return tc.post("/create_user", 
                    data = { 
                        "user" : user,
                        "psw" : psw 
                    }
            )


    # check id uniqueness
    # DANGER current comodifications of users.counter_id
    def test_id(self):
        tmp = server.users.counter_id
        
        nums = []
        for i in range(10):
            nums.append(server.users.get_id())

        for i, n in enumerate(nums):
            for j in range(i+1, len(nums)):
                self.assertNotEqual(n, nums[j])

        server.users.counter_id = tmp
    

    # check if the server works
    def test_welcome(self):
        with server.app.test_client() as tc:
            rv = tc.get("/")
            self.assertEqual(rv.status_code, 200)
            welcomed = rv.get_data().startswith("Welcome on the Server!")
            self.assertTrue(welcomed)


    # check if a new user is correctly created
    def test_correct_user_creation(self):
        username = "".join(random.sample(string.letters, 5))
        password = "".join(random.sample(string.letters, 5))
        dirs_counter = len(os.listdir(server.USERS_DIRECTORIES))
        with server.app.test_client() as tc:
            rv = self.user_demo(username, password)
            self.assertEqual(rv.status_code, 201)
        
        # check if a directory is created
        new_counter = len(os.listdir(server.USERS_DIRECTORIES))
        self.assertEqual(dirs_counter+1, new_counter)


    # check if, when the user already exists, 'create_user' returns an error
    def test_user_who_already_exists(self):
        with server.app.test_client() as tc:
            self.user_demo()
            rv = self.user_demo()
            self.assertEqual(rv.status_code, 409)


    # check a GET authentication access
    def test_correct_hidden_page(self):
        user = "Giovannina"
        psw = "cracracra"
        with server.app.test_client() as tc:
            tc.post("/create_user", 
                    data = { 
                        "user" : user,
                        "psw" : psw 
                    }
            )

        headers = {
            'Authorization': 'Basic ' + b64encode("{0}:{1}".format(user, psw))
        }

        with server.app.test_client() as tc:
            rv = tc.get("/hidden_page", headers=headers)
            self.assertEqual(rv.status_code, 200)


if __name__ == '__main__':
    try:
        os.mkdir(TEST_DIRECTORY)
    except OSError:
        shutil.rmtree(TEST_DIRECTORY)
        os.mkdir(TEST_DIRECTORY)

    unittest.main(exit=False)

    shutil.rmtree(TEST_DIRECTORY)

