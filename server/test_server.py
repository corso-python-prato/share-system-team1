#!/usr/bin/env python
#-*- coding: utf-8 -*-

import server
import os
import string
import json
import random
import unittest
import shutil
from base64 import b64encode

TEST_DIRECTORY = "test_users_dirs/"
TEST_USER_DATA = "test_user_data.json"


class TestSequenceFunctions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
    # set a test "USERS_DIRECTORIES"
        try:
            os.mkdir(TEST_DIRECTORY)
        except OSError:
            shutil.rmtree(TEST_DIRECTORY)
            os.mkdir(TEST_DIRECTORY)

        server.USERS_DIRECTORIES = TEST_DIRECTORY
    
    # set a test "USER_DATA" json
        open(TEST_USER_DATA, "w").close()
        server.USERS_DATA = TEST_USER_DATA


    @classmethod
    def tearDownClass(cls):
    # restore previous status
        os.remove(TEST_USER_DATA)
        shutil.rmtree(TEST_DIRECTORY)


    def setUp(self):
        server.app.config.update(TESTING=True)
        server.app.testing = True


    def user_demo(self, user=None, psw=None):
        if not user:
            random.seed(10)
            user = "".join(random.sample(string.letters, 5))
        if not psw:
            random.seed(10)
            psw = "".join(random.sample(string.letters, 5))

        with server.app.test_client() as tc:
            return tc.post("/API/v1/create_user",
                    data = {
                        "user" : user,
                        "psw" : psw
                    }
            )
    

    # check if the server works
    def test_welcome(self):
        with server.app.test_client() as tc:
            rv = tc.get("/")
            self.assertEqual(rv.status_code, server.HTTP_OK)
            welcomed = rv.get_data().startswith("Welcome on the Server!")
            self.assertTrue(welcomed)


    # check if a new user is correctly created
    def test_correct_user_creation(self):
        dirs_counter = len(os.listdir(server.USERS_DIRECTORIES))
        with server.app.test_client() as tc:
            rv = self.user_demo()
            self.assertEqual(rv.status_code, server.HTTP_CREATED)
        
        # check if a directory is created
        new_counter = len(os.listdir(server.USERS_DIRECTORIES))
        self.assertEqual(dirs_counter+1, new_counter)


    # check if, when the user already exists, 'create_user' returns an error
    def test_user_who_already_exists(self):
        user = "Gianni"
        psw = "IloveJava"
        with server.app.test_client() as tc:
            self.user_demo(user, psw)
            rv = self.user_demo(user, psw)
            self.assertEqual(rv.status_code, server.HTTP_CONFLICT)


    # check a GET authentication access
    def test_correct_hidden_page(self):
        user = "Giovannina"
        psw = "cracracra"
        rv = self.user_demo(user, psw)
        self.assertEqual(rv.status_code, server.HTTP_CREATED)

        headers = {
            'Authorization': 'Basic ' + b64encode("{0}:{1}".format(user, psw))
        }

        with server.app.test_client() as tc:
            rv = tc.get("/hidden_page", headers=headers)
            self.assertEqual(rv.status_code, server.HTTP_OK)


    # check if the backup function create the folder and the files
    def test_backup_config_files(self):
        successful =  server.backup_config_files("test_backup")
        if not successful:
            # the directory is already present due to an old failed test
            shutil.rmtree("test_backup")
            successful =  server.backup_config_files("test_backup")

        self.assertTrue(successful)

        try:
            dir_content = os.listdir("test_backup")
        except OSError:
            self.fail("Directory not created")
        else:
            self.assertIn(server.USERS_DATA, dir_content,
                    msg="'user_data' missing in backup folder")
        shutil.rmtree("test_backup")


    # TODO:
    # def test_to_md5(self):
    #     self.assertEqual(TEST_DIRECTORY, )


    def test_files_post(self):
        user = "test_post"
        psw = "test_post"
        rv = self.user_demo(user, psw)
        self.assertEqual(rv.status_code, 201)

        headers = {
            "Authorization": "Basic " + b64encode("{0}:{1}".format(user, psw))
        }

        content = "Hello my dear,\nit's a beautiful day here in Compiobbi."
        with open("somefile.txt", "w") as f:
            f.write(content)

        f = open("somefile.txt", "r")
        path = "somepath/somefile.txt"
        with server.app.test_client() as tc:
            rv = tc.post(
                "{}files/{}".format(server._API_PREFIX, path),
                headers = headers,
                data = {
                    "file_content": f
                    # "file_name": "somefile.txt"
                }
            )
            self.assertEqual(rv.status_code, 201)
        f.close()
        with open("{}{}/{}".format(TEST_DIRECTORY, user, path)) as f:
            uploaded_content = f.read()
            self.assertEqual(content, uploaded_content)


if __name__ == '__main__':
    # make tests!
    unittest.main()
