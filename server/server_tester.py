#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
import server
import string
import random
import unittest

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        server.app.testing = True
        self.client = server.app.test_client()

    #check id uniqueness
    def test_id(self):
        nums = []
        for i in range(10):
            nums.append(server.IdCreator.get_id())

        for i, n in enumerate(nums):
            for j in range(i+1, len(nums)):
                self.assertNotEqual(n, nums[j])
    
    #check if the server works
    def test_welcome(self):
        with self.client as tc:
            rv = tc.get("/")
            self.assertEqual(rv.status_code, 200)
            welcomed = rv.get_data().startswith("Welcome on the Server!")
            self.assertTrue(welcomed)

    #check if a new user is correctly created        
    def test_create_user(self):
        username = random.sample(string.letters, 5)
        password = random.sample(string.letters, 5)
        path, dirs, files = os.walk(server.USERS_DIRECTORIES)
        dirs_counter = len(dirs)
        with self.client as tc:
            rv = tc.post("/create_user", data = { "user" : username, "psw" : password })
            self.assertEqual(rv.status_code, 201)
            path, dirs, files = os.walk(server.USERS_DIRECTORIES)
            new_counter = len(dirs)
            self.assertEqual(dirs_counter+1, new_counter)


if __name__ == '__main__':
    unittest.main()