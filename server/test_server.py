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

DEMO_USER = "i_am_an_user@rawbox.it"
DEMO_PSW = "very_secret_password"
DEMO_HEADERS = {
    "Authorization": "Basic "
    + b64encode("{0}:{1}".format(DEMO_USER, DEMO_PSW))
}
DEMO_FILE = "somefile.txt"
DEMO_PATH = "somepath/somefile.txt"
DEMO_CONTENT = "Hello my dear,\nit's a beautiful day here in Compiobbi."
DEMO_DEST_COPY_PATH = "new_cp"
DEMO_DEST_MOVE_PATH = "new_mv"


def transfer(path, flag=True):
    client_path, server_path = set_tmp_params(path)
    if flag:
        func = "copy"
        new_path = "{}/{}".format(DEMO_DEST_COPY_PATH, path)
    else:
        func = "move"
        new_path = "{}/{}".format(DEMO_DEST_MOVE_PATH, path)
    with server.app.test_client() as tc:
        rv = tc.post(
               "{}actions/{}".format(server._API_PREFIX, func),
                headers = DEMO_HEADERS,
                data = { "file_src": client_path,
                         "file_dest" : os.path.join(new_path, DEMO_FILE)
            }
            )
        return rv, client_path, server_path


def set_tmp_params(father_dir):
    ''' Add a file in user's directory, in the path passed in argument 
    Please, use path here with only a word (not "dir/subdir") '''
    client_path = os.path.join(father_dir, DEMO_FILE)
    server_path = os.path.join(TEST_DIRECTORY, DEMO_USER, client_path)
    os.makedirs(os.path.dirname(server_path))
    shutil.copy(DEMO_FILE, server_path)

    server_father_path = os.path.join(TEST_DIRECTORY, DEMO_USER, father_dir)
    u = server.User.users[DEMO_USER]
    u.paths[father_dir] = [server_father_path, 0, False]
    u.paths[client_path] = [server_path, 0, 0]

    return client_path, server_path


def create_demo_user(user=None, psw=None):
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


class TestClient(object):

    def __init__(self, user, psw):
        self.user = user
        self.psw = psw
        self.headers = {
            "Authorization": "Basic "
            + b64encode("{0}:{1}".format(user, psw))
        }
        self.tc = server.app.test_client()
        self.VERBS = {
            "post": self.tc.post,
            "get": self.tc.get
        }

    def call(self, HTTP_verb, url, data=None, auth=True):
        return self.VERBS[HTTP_verb](
            server._API_PREFIX + url,
            data = data,
            headers = self.headers if auth else None
        )

    def create_demo_user(self):
        data = {
            "user": self.user,
            "psw": self.psw
        }
        return self.call("post", "create_user", data, auth=False)


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

        # demo user configuration
        create_demo_user(DEMO_USER, DEMO_PSW)
        with open(DEMO_FILE, "w") as f:
            f.write(DEMO_CONTENT)


    @classmethod
    def tearDownClass(cls):
        # restore previous status
        os.remove(DEMO_FILE)
        os.remove(TEST_USER_DATA)
        shutil.rmtree(TEST_DIRECTORY)


    def setUp(self):
        server.app.config.update(TESTING=True)
        server.app.testing = True


    def test_create_user(self):
        # check if a new user is correctly created
        dirs_counter = len(os.listdir(server.USERS_DIRECTORIES))

        user = "Gianni"
        psw = "IloveJava"
        client = TestClient(user, psw)
        rv = client.create_demo_user()
        self.assertEqual(rv.status_code, server.HTTP_CREATED)
        
        # check if a directory is created
        new_counter = len(os.listdir(server.USERS_DIRECTORIES))
        self.assertEqual(dirs_counter+1, new_counter)

        # check if, when the user already exists, 'create_user' returns an
        # error
        rv = client.create_demo_user()
        self.assertEqual(rv.status_code, server.HTTP_CONFLICT)


    def test_to_md5(self):
        # check if two files with the same content have the same md5
        second_file = "second_file.txt"
        with open(second_file, "w") as f:
            f.write(DEMO_CONTENT)

        first_md5 = server.to_md5(DEMO_FILE)
        second_md5 = server.to_md5(second_file)
        self.assertEqual(first_md5, second_md5)

        os.remove(second_file)

        # check if, for a directory, returns False
        tmp_dir = "aloha"
        os.mkdir(tmp_dir)
        self.assertFalse(server.to_md5(tmp_dir))

        os.rmdir(tmp_dir)


    def test_create_server_path(self):
        # check if aborts when you pass invalid paths:
        f = open(DEMO_FILE, "r")
        with server.app.test_client() as tc:
            rv = tc.post(
                "{}files/{}".format(server._API_PREFIX, "../file.txt"),
                headers = DEMO_HEADERS,
                data = { "file_content": f }
            )
            self.assertEqual(rv.status_code, 400)
        f.close()

        f = open(DEMO_FILE, "r")
        with server.app.test_client() as tc:
            rv = tc.post(
                "{}files/{}".format(server._API_PREFIX, "folder/../file.txt"),
                headers = DEMO_HEADERS,
                data = { "file_content": f }
            )
            self.assertEqual(rv.status_code, 400)
        f.close()


    def test_files_post(self):
        f = open(DEMO_FILE, "r")
        with server.app.test_client() as tc:
            rv = tc.post(
                "{}files/{}".format(server._API_PREFIX, DEMO_PATH),
                headers = DEMO_HEADERS,
                data = { "file_content": f }
            )
            self.assertEqual(rv.status_code, 201)
        f.close()
        with open("{}{}/{}".format(TEST_DIRECTORY, DEMO_USER, DEMO_PATH)) as f:
            uploaded_content = f.read()
            self.assertEqual(DEMO_CONTENT, uploaded_content)


    def test_files_get(self):
        client_path, server_path = set_tmp_params("dwn")

        with server.app.test_client() as tc:
            rv = tc.get(
                "{}files/{}".format(server._API_PREFIX, client_path),
                headers = DEMO_HEADERS
            )
            self.assertEqual(rv.status_code, 200)

        with open(server_path) as f:
            got_content = f.read()
            self.assertEqual(DEMO_CONTENT, got_content)


    def test_files_put(self):
        client_path, server_path = set_tmp_params("pt")
        if (server_path in server.User.users[DEMO_USER].paths[client_path]):
            f = open(DEMO_FILE, "r")
            with server.app.test_client() as tc:
                rv = tc.put(
                    "{}files/{}".format(server._API_PREFIX, DEMO_PATH),
                    headers = DEMO_HEADERS,
                    data = { "file_content": f }
                )
                self.assertEqual(rv.status_code, 201)
            f.close()
            with open("{}{}/{}".format(
                    TEST_DIRECTORY,
                    DEMO_USER,
                    DEMO_PATH)) as f:
                put_content = f.read()
                self.assertEqual(DEMO_CONTENT, put_content)

    def test_actions_delete(self):
        client_path, server_path = set_tmp_params("dlt")
        full_server_path = os.path.join(server_path, DEMO_FILE)
        with server.app.test_client() as tc:
            rv = tc.post(
                "{}actions/delete".format(server._API_PREFIX),
                headers = DEMO_HEADERS,
                data = { "path": client_path }
            )
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(os.path.isfile(full_server_path), False)
            #check if the file is correctly removed from the dictionary
            self.assertEqual(
                    server_path in server.User.users[DEMO_USER].paths,
                    False
            )


    def test_actions_copy(self):
        rv, client_path, server_path = transfer("cp", True)
        self.assertEqual(rv.status_code, 200)

        full_dest_path = os.path.join(TEST_DIRECTORY,
                DEMO_USER,
                DEMO_DEST_COPY_PATH,
                client_path)
        
        self.assertEqual(os.path.isfile(server_path), True)

        u = server.User.users[DEMO_USER]
        self.assertEqual("cp/{}".format(DEMO_FILE) in u.paths, True)
        self.assertEqual(os.path.isfile(full_dest_path), True)
        self.assertEqual(
                "{}/cp/{}".format(DEMO_DEST_COPY_PATH, DEMO_FILE) in u.paths,
                True
        )


    def test_actions_move(self):
        rv, client_path, server_path = transfer("mv", False)
        self.assertEqual(rv.status_code, 200)

        full_dest_path = os.path.join(
                TEST_DIRECTORY,
                DEMO_USER,
                DEMO_DEST_MOVE_PATH,
                client_path
        )
        self.assertEqual(os.path.isfile(server_path), False)

        u = server.User.users[DEMO_USER]
        self.assertEqual("mv/{}".format(DEMO_FILE) in u.paths, False)
        self.assertEqual(os.path.isfile(full_dest_path), True)
        self.assertEqual(
                "{}/mv/{}".format(DEMO_DEST_MOVE_PATH, DEMO_FILE) in u.paths,
                True
        )


    def test_files_differences(self):
        client = TestClient(
            user="complex_user@gmail.com",
            psw="complex_password"
        )
        client.create_demo_user()

        # first check: user created just now
        rv = client.call("get", "files/")
        self.assertEqual(rv.status_code, 200)
        snapshot1 = json.loads(rv.data)
        self.assertFalse(snapshot1["snapshot"])

        # second check: insert some files
        some_paths = [
            "path1/cool_filename.txt",
            "path2/path3/yo.jpg"
        ]
        for p in some_paths:
            f = open(DEMO_FILE, "r")
            data = { "file_content": f }
            rv = client.call("post", "files/"+p, data)
            f.close()
            self.assertEqual(rv.status_code, 201)

        rv = client.call("get", "files/")
        self.assertEqual(rv.status_code, 200)
        
        snapshot2 = json.loads(rv.data)
        self.assertGreater(snapshot2["timestamp"], snapshot1["timestamp"])
        self.assertEqual(len(snapshot2["snapshot"]), 1)
        
        for s in snapshot2["snapshot"].values():
            self.assertEqual(len(s), 2)

        # third check: delete a file
        data = { "path": some_paths[1] }
        rv = client.call("post", "actions/delete", data)
        self.assertEqual(rv.status_code, 200)

        rv = client.call("get", "files/")
        self.assertEqual(rv.status_code, 200)

        snapshot3 = json.loads(rv.data)
        self.assertGreater(snapshot3["timestamp"], snapshot2["timestamp"])
        self.assertEqual(len(snapshot3["snapshot"]), 1)

        for s in snapshot3["snapshot"].values():
            self.assertEqual(len(s), 1)


if __name__ == '__main__':
    # make tests!
    unittest.main()
