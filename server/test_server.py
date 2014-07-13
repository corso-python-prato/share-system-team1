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
from server_errors import *

TEST_DIRECTORY = "test_users_dirs/"
TEST_USER_DATA = "test_user_data.json"

DEMO_USER = "i_am_an_user@rawbox.it"
DEMO_PSW = "very_secret_password"
DEMO_FAKE_USER = "fake_usr"
DEMO_CLIENT = None

SHARE_CLIENTS = []

DEMO_FILE = "somefile.txt"
DEMO_CONTENT = "Hello my dear,\nit's a beautiful day here in Compiobbi."
DEMO_DEST_COPY_PATH = "new_cp"
DEMO_DEST_MOVE_PATH = "new_mv"
NO_SERVER_PATH = "marcoRegna"


def make_headers(user, psw):
    return {
        "Authorization": "Basic "
        + b64encode("{0}:{1}".format(user, psw))
    }


def transfer(path, flag=True, test=True):
    client_path, server_path = set_tmp_params(path)
    if flag:
        func = "copy"
        new_path = "{}/{}".format(DEMO_DEST_COPY_PATH, path)
    else:
        func = "move"
        new_path = "{}/{}".format(DEMO_DEST_MOVE_PATH, path)\

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
            "get": self.tc.get,
            "put": self.tc.put,
            "delete": self.tc.delete
        }

    def call(self, HTTP_verb, url, data=None, auth=True):
        return self.VERBS[HTTP_verb](server._API_PREFIX + url,
                                     data=data,
                                     headers=self.headers if auth else None)

    def create_demo_user(self, flag=False):
        usr = "user"
        psw = "psw"
        if flag:
            usr = "fake_usr"
            psw = "fake_psw"

        data = {
            usr: self.user,
            psw: self.psw
        }
        return self.call("post", "create_user", data, auth=False)

    def set_fake_usr(self, flag=False):
        self.headers["Authorization"] = "".join((
            "Basic ",
            b64encode("{0}:{1}".format(
                DEMO_FAKE_USER if flag else self.user,
                self.psw
            ))
        ))


class TestFilesAPI(unittest.TestCase):
    test_path = "demo_test/test_file"
    test_file_name = "a_file.txt"
    test_file = os.path.join(test_path, test_file_name)
    user_test = "user"
    password_test = "password"
    url_radix = "files/"

    @classmethod
    def setUpClass(cls):
        #create the path to do the test on files
        try:
            os.mkdir(TestFilesAPI.test_path)
        except OSError:
            shutil.rmtree(TestFilesAPI.test_path)
            os.mkdir(TestFilesAPI.test_path)

        with open(TestFilesAPI.test_file, "wb") as fp:
            fp.write("some random text")

    def set_tmp_params(self, father_dir):
        ''' Add a file in user's directory, in the path passed in argument
        Please, use path here with only a word (not "dir/subdir") '''
        client_path = os.path.join(father_dir, TestFilesAPI.test_file_name)

        server_path = os.path.join(TestFilesAPI.test_path,
                                   TestFilesAPI.user_test, client_path)
        os.makedirs(os.path.dirname(server_path))
        shutil.copy(TestFilesAPI.test_file_name, server_path)

        server_father_path = os.path.join(TestFilesAPI.test_path,
                                          TestFilesAPI.user_test, father_dir)

        server_path = os.path.join(TestFilesAPI.test_path, "user_dirs",
                                   TestFilesAPI.user_test, client_path)
        if not os.path.isdir(os.path.dirname(server_path)):
            os.makedirs(os.path.dirname(server_path))
        shutil.copy(TestFilesAPI.test_file, server_path)

        server_father_path = os.path.join(TestFilesAPI.test_path, "user_dirs",
                                          TestFilesAPI.user_test, father_dir)

        u = server.User.users[TestFilesAPI.user_test]
        u.paths[father_dir] = [server_father_path, 0, False]
        u.paths[client_path] = [server_path, 0, 0]

        return client_path, server_path

    def setUp(self):
        server.SERVER_ROOT = TestFilesAPI.test_path
        server.server_setup()
        if TestFilesAPI.user_test not in server.User.users:
            server.User(TestFilesAPI.user_test, TestFilesAPI.password_test)

    def test_post(self):
        with server.app.test_client() as tc:
            f = open(TestFilesAPI.test_file, "r")
            data = {"file_content": f}
            url = "{}{}".format(TestFilesAPI.url_radix,
                                TestFilesAPI.test_file_name)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers("fake_user",
                                              TestFilesAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 401)

        with server.app.test_client() as tc:
            f = open(TestFilesAPI.test_file, "r")
            data = {"file_content": f}
            url = "{}{}".format(TestFilesAPI.url_radix,
                                TestFilesAPI.test_file_name)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers(TestFilesAPI.user_test,
                                              TestFilesAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 201)

        with open("{}{}/{}/{}".format(TestFilesAPI.test_path, "user_dirs",
                                      TestFilesAPI.user_test,
                                      TestFilesAPI.test_file_name)) as f:
            with open("{}{}/{}/{}".format(TestFilesAPI.test_path, "/user_dirs",
                                          TestFilesAPI.user_test,
                                          TestFilesAPI.test_file_name)) as f:

                uploaded_content = f.read()
                f = open(TestFilesAPI.test_file, "r")
                self.assertEqual(f.read(), uploaded_content)
                f.close()

        with server.app.test_client() as tc:
            f = open(TestFilesAPI.test_file, "r")
            data = {"file_content": f}
            url = "{}{}".format(TestFilesAPI.url_radix,
                                TestFilesAPI.test_file_name)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers(TestFilesAPI.user_test,
                                              TestFilesAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 409)

    def test_get(self):
        client_path, server_path = self.set_tmp_params("to_download")
        with server.app.test_client() as tc:
            f = open(TestFilesAPI.test_file, "r")
            data = {"file_content": f}
            url = "{}{}".format(TestFilesAPI.url_radix, client_path)
            rv = tc.get(server._API_PREFIX + url,
                        headers=make_headers("fake_user",
                                             TestFilesAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 401)

        with server.app.test_client() as tc:
            f = open(TestFilesAPI.test_file, "r")
            data = {"file_content": f}
            url = "{}{}".format(TestFilesAPI.url_radix, client_path)
            rv = tc.get(server._API_PREFIX + url,
                        headers=make_headers(TestFilesAPI.user_test,
                                             TestFilesAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 200)
            with open(server_path, "r") as f:
                got_content = f.read()
                with open(TestFilesAPI.test_file, "r") as fp:
                    self.assertEqual(fp.read(), got_content)

        with server.app.test_client() as tc:
            f = open(TestFilesAPI.test_file, "r")
            data = {"file_content": f}
            url = "{}{}".format(TestFilesAPI.url_radix, "NO_SERVER_PATH")
            rv = tc.get(server._API_PREFIX + url,
                        headers=make_headers(TestFilesAPI.user_test,
                                             TestFilesAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 404)

        os.remove(server_path)
        with server.app.test_client() as tc:
            f = open(TestFilesAPI.test_file, "r")
            data = {"file_content": f}
            url = "{}{}".format(TestFilesAPI.url_radix, client_path)
            rv = tc.get(server._API_PREFIX + url,
                        headers=make_headers(TestFilesAPI.user_test,
                                             TestFilesAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 410)

    def test_put(self):

        client_path, server_path = self.set_tmp_params("modify")
        if not server_path in server.User.users[TestFilesAPI.user_test
                                                ].paths[client_path]:
            return

        with server.app.test_client() as tc:
            f = open(TestFilesAPI.test_file, "r")
            data = {"file_content": f}
            url = "{}{}".format(TestFilesAPI.url_radix,
                                TestFilesAPI.test_file_name)
            rv = tc.put(server._API_PREFIX + url,
                        data=data,
                        headers=make_headers("fake_user",
                                             TestFilesAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 401)

        with server.app.test_client() as tc:
            f = open(TestFilesAPI.test_file, "r")
            data = {"file_content": f}
            url = "{}{}".format(TestFilesAPI.url_radix,
                                TestFilesAPI.test_file_name)
            rv = tc.put(server._API_PREFIX + url,
                        data=data,
                        headers=make_headers(TestFilesAPI.user_test,
                                             TestFilesAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 201)

        with open(server_path, "r") as f:
                got_content = f.read()
                with open(TestFilesAPI.test_file, "r") as fp:
                    self.assertEqual(fp.read(), got_content)

        with server.app.test_client() as tc:
            f = open(TestFilesAPI.test_file, "r")
            data = {"file_content": f}
            url = "{}{}".format(TestFilesAPI.url_radix, "NO_SERVER_PATH")
            rv = tc.put(server._API_PREFIX + url,
                        data=data,
                        headers=make_headers(TestFilesAPI.user_test,
                                             TestFilesAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 404)


class TestActionsAPI(unittest.TestCase):
    test_path = "demo_test/test_actions/"
    test_file_name = "some_text.txt"
    test_file = os.path.join(test_path, test_file_name)
    user_test = "actions_user"
    password_test = "password"
    url_radix = "actions/"
    DEMO_CLIENT = None

    @classmethod
    def setUpClass(cls):
        #create the path to do the test on actions
        try:
            os.mkdir(TestActionsAPI.test_path)
        except OSError:
            shutil.rmtree(TestActionsAPI.test_path)
            os.mkdir(TestActionsAPI.test_path)

        with open(TestActionsAPI.test_file, "wb") as fp:
            fp.write("some random text")

    def set_tmp_params(self, father_dir):
        ''' Add a file in user's directory, in the path passed in argument
        Please, use path here with only a word (not "dir/subdir") '''
        client_path = os.path.join(father_dir, TestActionsAPI.test_file_name)
        server_path = os.path.join(TestActionsAPI.test_path,
                                   TestActionsAPI.user_test, client_path)
        os.makedirs(os.path.dirname(server_path))
        shutil.copy(TestActionsAPI.test_file_name, server_path)

        server_father_path = os.path.join(TestActionsAPI.test_path,
                                          TestActionsAPI.user_test, father_dir)
        u = server.User.users[TestActionsAPI.user_test]
        u.paths[father_dir] = [server_father_path, 0, False]
        u.paths[client_path] = [server_path, 0, 0]

        return client_path, server_path

    def transfer(path, flag=True, test=True):
        client_path, server_path = self.set_tmp_params(path)
        if flag:
            func = "copy"
            new_path = "{}/{}".format("new_cp", path)
        else:
            func = "move"
            new_path = "{}/{}".format("new_mv", path)

        if test:
            data = {
                "file_src": client_path,
                "file_dest": os.path.join(new_path,
                                          TestActionsAPI.test_file_name)
            }
            rv = DEMO_CLIENT.call("post", "actions/" + func, data)
        else:
            data = {"file_src": "marcoRegna",
                    "file_dest": os.path.join(new_path,
                                              TestActionsAPI.test_file_name)}
            rv = DEMO_CLIENT.call("post", "actions/" + func, data)

        return rv, client_path, server_path

    def setUp(self):
        server.SERVER_ROOT = TestActionsAPI.test_path
        server.server_setup()
        server.User(TestFilesAPI.user_test, TestActionsAPI.password_test)

    def test_actions_delete(self):
        client_path, server_path = set_tmp_params("dlt")

        with server.app.test_client() as tc:
            f = open(TestActionsAPI.test_file, "r")
            data = {"file_content": f}
            url = "{}{}".format(TestActionsAPI.url_radix, "delete",
                                client_path)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers("fake_user",
                                              TestActionsAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 401)

        with server.app.test_client() as tc:
            f = open(TestActionsAPI.test_file, "r")
            data = {"file_content": f}
            url = "{}{}".format(TestActionsAPI.url_radix, "delete",
                                TestActionsAPI.test_file_name)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers(TestActionsAPI.user_test,
                                              TestActionsAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 200)
            self.assertFalse(os.path.isfile(full_server_path))
            #check if the file is correctly removed from the dictionary
            self.assertFalse(server_path in
                             server.User.users[TestActionsAPI.user_test].paths)

        with server.app.test_client() as tc:
            f = open(TestActionsAPI.test_file, "r")
            data = {"marcoRegna": f}
            url = "{}{}".format(TestActionsAPI.url_radix, "delete",
                                TestActionsAPI.test_file_name)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers(TestActionsAPI.user_test,
                                              TestActionsAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 404)

        with server.app.test_client() as tc:
            f = open(TestActionsAPI.test_file, "r")
            data = {"marcoRegna": f}
            url = "{}{}".format(TestActionsAPI.url_radix, "destroy",
                                TestActionsAPI.test_file_name)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers(TestActionsAPI.user_test,
                                              TestActionsAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 404)

    def test_last_file_delete_in_root(self):
        # create a demo user
        user = "emilio"
        client = TestClient(user, "passw")
        client.create_demo_user()

        # upload a file
        path = "filename.txt"
        with server.app.test_client() as tc:
            f = open(TestActionsAPI.test_file, "r")
            data = {"file_content": f}
            url = "{}{}".format("files/",
                                client_path)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers(user, passw))
            f.close()
            self.assertEqual(rv.status_code, 201)

        # delete the file
        with server.app.test_client() as tc:
            f = open(TestActionsAPI.test_file, "r")
            data = {"path": path}
            url = "{}{}".format(TestActionsAPI.url_radix, "delete",
                                TestActionsAPI.test_file_name)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers(TestActionsAPI.user_test,
                                              TestActionsAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 200)
            user_root = os.path.join(server.USERS_DIRECTORIES, user)
            self.assertTrue(os.path.isdir(user_root))

    def test_actions_copy(self):
        with server.app.test_client() as tc:
            f = open(TestActionsAPI.test_file, "r")
            data = {"file_src": "src", "file_dest": "dest"}
            url = "{}{}".format(TestActionsAPI.url_radix, "copy",
                                client_path)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers("fake_user",
                                              TestActionsAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 401)

        with server.app.test_client() as tc:
            f = open(TestActionsAPI.test_file, "r")
            data = {"file_src": "src", "file_dest": "dest"}
            url = "{}{}".format(TestActionsAPI.url_radix, "copy",
                                TestActionsAPI.test_file_name)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers(TestActionsAPI.user_test,
                                              TestActionsAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 201)
            self.assertEqual(os.path.isfile(server_path), True)
            u = server.User.users[TestActionsAPI.user_test]
            self.assertEqual("cp/{}".format(TestActionsAPI.test_file_name)
                             in u.paths, True)
            self.assertEqual(os.path.isfile(full_dest_path), True)
            self.assertEqual("{}/cp/{}".format("new_cp",
                                               TestActionsAPI.test_file_name)
                             in u.paths, True)

        client_path, server_path = set_tmp_params("prova")
        data = {"file_src": client_path, "file_dest": client_path}
        with server.app.test_client() as tc:
            f = open(TestActionsAPI.test_file, "r")
            data = {"file_src": "src", "file_dest": "dest"}
            url = "{}{}".format(TestActionsAPI.url_radix, "copy",
                                client_path)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers(TestActionsAPI.user_test,
                                              TestActionsAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 409)

    def test_actions_move(self):
        with server.app.test_client() as tc:
            f = open(TestActionsAPI.test_file, "r")
            data = {"file_src": "src", "file_dest": "dest"}
            url = "{}{}".format(TestActionsAPI.url_radix, "move",
                                client_path)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers("fake_user",
                                              TestActionsAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 401)

        with server.app.test_client() as tc:
            f = open(TestActionsAPI.test_file, "r")
            data = {"file_src": "src", "file_dest": "dest"}
            url = "{}{}".format(TestActionsAPI.url_radix, "move",
                                TestActionsAPI.test_file_name)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers(TestActionsAPI.user_test,
                                              TestActionsAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 201)
            self.assertEqual(os.path.isfile(server_path), False)
            u = server.User.users[TestActionsAPI.user_test]
            self.assertEqual("mv/{}".format(TestActionsAPI.test_file_name)
                             in u.paths, False)
            self.assertEqual(os.path.isfile(full_dest_path), True)
            self.assertEqual("{}/mv/{}".format("new_mv",
                                               TestActionsAPI.test_file_name)
                             in u.paths, True)

        with server.app.test_client() as tc:
            f = open(TestActionsAPI.test_file, "r")
            data = {"file_src": "src", "file_dest": "dest"}
            url = "{}{}".format(TestActionsAPI.url_radix, "move",
                                client_path)
            rv = tc.post(server._API_PREFIX + url,
                         data=data,
                         headers=make_headers(TestActionsAPI.user_test,
                                              TestActionsAPI.password_test))
            f.close()
            self.assertEqual(rv.status_code, 404)


class NewRootTestExample(unittest.TestCase):
    other_directory = "proppolo"

    def setUp(self):
        server.SERVER_ROOT = NewRootTestExample.other_directory
        server.server_setup()

    def test_setup_server(self):
        self.assertEqual(
            server.USERS_DIRECTORIES,
            os.path.join(NewRootTestExample.other_directory, "user_dirs/")
        )
        self.assertEqual(
            server.USERS_DATA,
            os.path.join(NewRootTestExample.other_directory, "user_data.json")
        )
        self.assertTrue(
            os.path.isdir(server.USERS_DIRECTORIES)
        )

    def tearDown(self):
        shutil.rmtree(NewRootTestExample.other_directory)


class TestUser(unittest.TestCase):
    root = "demo_test/test_user"

    def setUp(self):
        server.SERVER_ROOT = TestUser.root
        server.server_setup()

    def tearDown(self):
        try:
            os.remove(server.USERS_DATA)
        except OSError:
            pass
        shutil.rmtree(server.USERS_DIRECTORIES)

    def test_create_user(self):
        # check if a new user is correctly created
        dirs_counter = len(os.listdir(server.USERS_DIRECTORIES))

        data = {
            "user": "Gianni",
            "psw": "IloveJava"
        }
        with server.app.test_client() as tc:
            received = tc.post(_API_PREFIX + "create_user", data=data)
        self.assertEqual(received.status_code, server.HTTP_CREATED)

        # check if a directory is created
        new_counter = len(os.listdir(server.USERS_DIRECTORIES))
        self.assertEqual(dirs_counter + 1, new_counter)

        # check if, when the user already exists, 'create_user' returns an
        # error
        with server.app.test_client() as tc:
            received = tc.post(_API_PREFIX + "create_user", data=data)
        self.assertEqual(received.status_code, server.HTTP_CONFLICT)

        # TODO: to be revised after server fix
        # # check the error raised when the directory for a new user
        # # already exists
        # data = {
        #     "user": "Giovanni",
        #     "psw": "zappa"
        # }
        # os.mkdir(os.path.join(server.USERS_DIRECTORIES, data["user"]))
        # with server.app.test_client() as tc:
        #     with self.assertRaises(ConflictError):
        #         tc.post(_API_PREFIX + "create_user", data=data)

    def test_to_md5(self):
        # check if two files with the same content have the same md5
        first_md5 = server.to_md5(
            os.path.join(TestUser.root, "demofile1.txt")
        )
        first_copy_md5 = server.to_md5(
            os.path.join(TestUser.root, "demofile1_copy.txt")
        )
        self.assertEqual(first_md5, first_copy_md5)

        # check if two different files have different md5
        second_md5 = server.to_md5(
            os.path.join(TestUser.root, "demofile2.txt")
        )
        self.assertNotEqual(first_md5, second_md5)

        # check if, for a directory, returns False
        tmp_dir = "aloha"
        os.mkdir(tmp_dir)
        self.assertFalse(server.to_md5(tmp_dir))
        os.rmdir(tmp_dir)


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
        global DEMO_CLIENT
        DEMO_CLIENT = TestClient(DEMO_USER, DEMO_PSW)
        DEMO_CLIENT.create_demo_user()
        with open(DEMO_FILE, "w") as f:
            f.write(DEMO_CONTENT)

        # create some clients for share tests
        for i in range(5):
            random.seed(i)
            user = "".join(random.sample(string.letters, 7) +
                           ["@"] + random.sample(string.letters, 3)
                           + [".com"])
            random.seed(i + 40)
            psw = "".join(random.sample(string.letters, 10))
            u = TestClient(user, psw)
            u.create_demo_user()
            SHARE_CLIENTS.append(u)

    @classmethod
    def tearDownClass(cls):
        # restore previous status
        os.remove(DEMO_FILE)
        os.remove(TEST_USER_DATA)
        shutil.rmtree(TEST_DIRECTORY)

    def setUp(self):
        server.app.config.update(TESTING=True)
        server.app.testing = True

    def test_create_server_path(self):
        # check if aborts when you pass invalid paths:
        invalid_paths = [
            "../file.txt",
            "folder/../file.txt"
        ]

        for p in invalid_paths:
            f = open(DEMO_FILE, "r")
            data = {"file_content": f}
            rv = DEMO_CLIENT.call("post", "files/" + p, data)
            f.close()

            self.assertEqual(rv.status_code, 400)
        # TODO: other tests here?

    def test_actions_delete(self):
        client_path, server_path = set_tmp_params("dlt")
        full_server_path = os.path.join(server_path, DEMO_FILE)

        data = {"path": client_path}
        DEMO_CLIENT.set_fake_usr(True)
        rv = DEMO_CLIENT.call("post", "actions/delete", data)
        self.assertEqual(rv.status_code, 401)

        DEMO_CLIENT.set_fake_usr(False)
        rv = DEMO_CLIENT.call("post", "actions/delete", data)
        self.assertEqual(rv.status_code, 200)
        self.assertFalse(os.path.isfile(full_server_path))
        #check if the file is correctly removed from the dictionary
        self.assertFalse(server_path in server.User.users[DEMO_USER].paths)

        data = {"path": NO_SERVER_PATH}
        rv = DEMO_CLIENT.call("post", "actions/delete", data)
        self.assertEqual(rv.status_code, 404)

        rv = DEMO_CLIENT.call("post", "actions/destroy", data)
        self.assertEqual(rv.status_code, 404)

    def test_last_file_delete_in_root(self):
        # create a demo user
        user = "emilio"
        client = TestClient(user, "passw")
        client.create_demo_user()

        # upload a file
        path = "filename.txt"
        f = open(DEMO_FILE, "r")
        data = {"file_content": f}
        rv = client.call("post", "files/" + path, data)
        f.close()
        self.assertEqual(rv.status_code, 201)

        # delete the file
        data = {"path": path}
        rv = client.call("post", "actions/delete", data)
        self.assertEqual(rv.status_code, 200)

        user_root = os.path.join(server.USERS_DIRECTORIES, user)
        self.assertTrue(os.path.isdir(user_root))

    def test_actions_copy(self):
        DEMO_CLIENT.set_fake_usr(True)
        data = {"file_src": "src", "file_dest": "dest"}
        rv = DEMO_CLIENT.call("post", "actions/copy", data)
        self.assertEqual(rv.status_code, 401)
        DEMO_CLIENT.set_fake_usr(False)
        rv, client_path, server_path = transfer("cp", True)
        self.assertEqual(rv.status_code, 201)

        full_dest_path = os.path.join(TEST_DIRECTORY,
                                      DEMO_USER,
                                      DEMO_DEST_COPY_PATH,
                                      client_path)
        self.assertEqual(os.path.isfile(server_path), True)

        u = server.User.users[DEMO_USER]
        self.assertEqual("cp/{}".format(DEMO_FILE) in u.paths, True)
        self.assertEqual(os.path.isfile(full_dest_path), True)
        self.assertEqual("{}/cp/{}".format(DEMO_DEST_COPY_PATH,
                                           DEMO_FILE) in u.paths, True)
        client_path, server_path = set_tmp_params("prova")
        data = {"file_src": client_path, "file_dest": client_path}
        rv = DEMO_CLIENT.call("post", "actions/copy", data)
        self.assertEqual(rv.status_code, 409)

    def test_actions_move(self):
        DEMO_CLIENT.set_fake_usr(True)
        data = {"file_src": "src", "file_dest": "dest"}
        rv = DEMO_CLIENT.call("post", "actions/move", data)
        self.assertEqual(rv.status_code, 401)
        DEMO_CLIENT.set_fake_usr(False)
        rv, client_path, server_path = transfer("mv", False)
        self.assertEqual(rv.status_code, 201)

        full_dest_path = os.path.join(TEST_DIRECTORY,
                                      DEMO_USER,
                                      DEMO_DEST_MOVE_PATH,
                                      client_path)
        self.assertEqual(os.path.isfile(server_path), False)

        u = server.User.users[DEMO_USER]
        self.assertEqual("mv/{}".format(DEMO_FILE) in u.paths, False)
        self.assertEqual(os.path.isfile(full_dest_path), True)
        self.assertEqual("{}/mv/{}".format(DEMO_DEST_MOVE_PATH,
                                           DEMO_FILE) in u.paths, True)
        rv, client_path, server_path = transfer("mv", False, False)
        self.assertEqual(rv.status_code, 404)

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
            data = {"file_content": f}
            rv = client.call("post", "files/" + p, data)
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
        data = {"path": some_paths[1]}
        rv = client.call("post", "actions/delete", data)
        self.assertEqual(rv.status_code, 200)

        rv = client.call("get", "files/")
        self.assertEqual(rv.status_code, 200)

        snapshot3 = json.loads(rv.data)
        self.assertGreater(snapshot3["timestamp"], snapshot2["timestamp"])
        self.assertEqual(len(snapshot3["snapshot"]), 1)

        for s in snapshot3["snapshot"].values():
            self.assertEqual(len(s), 1)

    def test_user_class_init(self):
        # create a temporary directory and work on it
        working_directory = os.getcwd()

        test_dir = "tmptmp"
        try:
            os.mkdir(test_dir)
        except OSError:
            shutil.rmtree(test_dir)
            os.mkdir(test_dir)

        os.chdir(test_dir)

        # check 1: if the folder is empty, nothing is modified
        previous_users = server.User.users
        server.User.user_class_init()
        self.assertEqual(server.User.users, previous_users)
        # check 2: if there is a json, upload the users from it
        username = "UserName"
        tmp_dict = {
            "users": {
                username: {
                    "paths": {
                        "": [
                            "user_dirs/{}".format(username),
                            False,
                            1403512334.247553
                        ],
                        "hello.txt": [
                            "user_dirs/{}/hello.txt".format(username),
                            "6186badadb5fbb0416cd29a04e2d92d7",
                            1403606130.356392
                        ]
                    },
                    "psw": "encrypted password",
                    "timestamp": 1403606130.356392
                },
            }
        }
        with open(server.USERS_DATA, "w") as f:
            json.dump(tmp_dict, f)
        server.User.user_class_init()
        self.assertIn(username, server.User.users)

        # check 3: if the json is invalid, remove it
        with open(server.USERS_DATA, "w") as f:
            f.write("{'users': poksd [sd ]sd []}")
        server.User.user_class_init()
        self.assertFalse(os.path.exists(server.USERS_DATA))

        # restore the previous situation
        os.chdir(working_directory)
        shutil.rmtree(test_dir)


class TestShare(unittest.TestCase):
    root = "demo_test/test_share"

    def setUp(self):
        server.SERVER_ROOT = TestShare.root
        shutil.copy(
            os.path.join(TestShare.root, "demo_user_data.json"),
            os.path.join(TestShare.root, "user_data.json")
        )
        server.server_setup()

        # this class comes with some users
        self.owner = "Emilio@me.it"
        self.owner_headers = make_headers(self.owner, "password")
        self.ben1 = "Ben1@me.too"
        self.ben1_headers = make_headers(self.ben1, "password")
        self.ben2 = "Ben2@me.too"
        # self.ben2_headers = make_headers(self.ben2, "password")
        self.tc = server.app.test_client()

    def tearDown(self):
        os.remove(server.USERS_DATA)

    def test_add_share(self):
        # check if it aborts, when the beneficiary doesn't exist
        received = self.tc.post(
            "{}shares/{}/{}".format(_API_PREFIX, "ciao.txt", "not_an_user"),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 400)

        # check if it aborts, when the resource doesn't exist
        received = self.tc.post(
            "{}shares/{}/{}".format(_API_PREFIX, "not_a_resource", self.ben1),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 400)

        # share a file
        received = self.tc.post(
            "{}shares/{}/{}".format(_API_PREFIX, "ciao.txt", self.ben1),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)

        # share the subdir
        received = self.tc.post(
            "{}shares/{}/{}".format(
                _API_PREFIX, "shared_directory", self.ben1
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)
        self.assertIn(
            "shares/{}/shared_directory".format(self.owner),
            server.User.users[self.ben1].paths
        )
        self.assertIn(
            "shares/{}/shared_directory/interesting_file.txt".format(
                self.owner
            ),
            server.User.users[self.ben1].paths
        )

    def test_can_write(self):
        # DEMO_CLIENT.set_fake_usr(True)
        # rv = DEMO_CLIENT.call("post", "shares/dir/usr")
        # self.assertEqual(rv.status_code, 401)
        # DEMO_CLIENT.set_fake_usr(False)

        # share a file with an user (create a share)
        # TODO: load this from json when the shares will be saved on file
        received = self.tc.post(
            "{}shares/{}/{}".format(
                _API_PREFIX, "can_write", self.ben1
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)

        # a beneficiary tries to add a file to a shared directory, but the
        # share is read-only.
        # case Files POST and PUT
        destination = os.path.join(
            "shares", self.owner, "can_write", "parole.txt"
        )
        demo_file = "demo_test/demofile1.txt"
        for verb in [self.tc.post, self.tc.put]:
            with open(demo_file, "r") as f:
                data = {"file_content": f}
                received = verb(
                    "{}files/{}".format(_API_PREFIX, destination),
                    data=data,
                    headers=self.ben1_headers
                )
                self.assertEqual(received.status_code, 403)

        # case Action delete
        data = {"path": destination}
        received = self.tc.post(
            "{}actions/delete".format(_API_PREFIX),
            data=data,
            headers=self.ben1_headers
        )
        self.assertEqual(received.status_code, 403)

        # case copy or move into a shared directory (not owned)
        data = {
            "file_src": "my_file.txt",
            "file_dest": os.path.join("shares", self.owner, "can_write/")
        }
        for act in ["move", "copy"]:
            received = self.tc.post(
                "{}actions/{}".format(_API_PREFIX, act),
                data=data,
                headers=self.ben1_headers
            )
            self.assertEqual(received.status_code, 403)


    def test_remove_beneficiary(self):
        # test if aborts when the resource is not on the server
        received = self.tc.delete(
            "{}shares/{}/{}".format(
                _API_PREFIX, "file_not_present.txt", self.ben1
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 400)
        self.assertEqual(
            received.data,
            '"The specified file or directory is not present"'
        )

        # test if aborts when the resource is not shared with the beneficiary
        received = self.tc.delete(
            "{}shares/{}/{}".format(
                _API_PREFIX, "shared_with_two_bens.txt", self.ben1
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 400)

        # share a file with a couple of users
        for beneficiary in [self.ben1, self.ben2]:
            received = self.tc.post(
                "{}shares/{}/{}".format(
                    _API_PREFIX, "shared_with_two_bens.txt", beneficiary
                ),
                headers=self.owner_headers
            )
            self.assertEqual(received.status_code, 200)

        # remove the first user from the share
        received = self.tc.delete(
            "{}shares/{}/{}".format(
                _API_PREFIX, "shared_with_two_bens.txt", self.ben1
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)

        server_path = os.path.join(
            server.USERS_DIRECTORIES,
            self.owner,
            "shared_with_two_bens.txt"
        )
        self.assertIn(server_path, server.User.shared_resources)
        self.assertEqual(
            server.User.shared_resources[server_path],
            [self.owner, self.ben2]
        )

        # remove the second user
        received = self.tc.delete(
            "{}shares/{}/{}".format(
                _API_PREFIX, "shared_with_two_bens.txt", self.ben2
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)
        self.assertNotIn(server_path, server.User.shared_resources)

    def test_remove_share(self):
        # test if aborts when the resource doesn't exist
        received = self.tc.delete(
            "{}shares/{}".format(_API_PREFIX, "not_a_file.txt"),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 400)

        # test if aborts when the resource isn't a share
        received = self.tc.delete(
            "{}shares/{}".format(_API_PREFIX, "not_shared_file.txt"),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 400)

        # share a file with a couple of users
        for beneficiary in [self.ben1, self.ben2]:
            received = self.tc.post(
                "{}shares/{}/{}".format(
                    _API_PREFIX, "shared_with_two_bens.txt", beneficiary
                ),
                headers=self.owner_headers
            )
            self.assertEqual(received.status_code, 200)

        # remove the share on the resource and check
        received = self.tc.delete(
            "{}shares/{}".format(_API_PREFIX, "shared_with_two_bens.txt"),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)
        self.assertNotIn(
            os.path.join(
                server.USERS_DIRECTORIES,
                self.owner,
                "shared_with_two_bens.txt"
            ),
            server.User.shared_resources
        )

    def test_changes_in_shared_directory(self):
        subdir = "changing"
        filename = "changing_file.txt"
        demo_file1 = "demo_test/demofile1.txt"
        demo_file2 = "demo_test/demofile2.txt"

        # setup
        sub_path = os.path.join(server.USERS_DIRECTORIES, self.owner, subdir)
        os.mkdir(sub_path)
        shutil.copy2(demo_file1, os.path.join(sub_path, filename))

        # share subdir with beneficiary
        # TODO: load this from json when the shares will be saved on file
        received = self.tc.post(
            "{}shares/{}/{}".format(
                _API_PREFIX, subdir, self.ben1
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)

        # update a shared file and check if it's ok
        owner_timestamp = server.User.users[self.owner].timestamp
        with open(demo_file2, "r") as f:
            received = self.tc.put(
                "{}files/{}/{}".format(
                    _API_PREFIX, subdir, filename
                ),
                data={"file_content": f},
                headers=self.owner_headers
            )
        self.assertEqual(received.status_code, 201)
        owner_new_timestamp = server.User.users[self.owner].timestamp
        self.assertGreater(owner_new_timestamp, owner_timestamp)

        ben_timestamp = server.User.users[self.ben1].timestamp
        self.assertEqual(owner_new_timestamp, ben_timestamp)

        # upload a new file in shared directory and check
        with open(demo_file1, "r") as f:
            received = self.tc.post(
                "{}files/{}/{}".format(
                    _API_PREFIX, subdir, "other_subdir/new_file"
                ),
                data={"file_content": f},
                headers=self.owner_headers
            )
        self.assertEqual(received.status_code, 201)
        self.assertEqual(
            server.User.users[self.owner].timestamp,
            server.User.users[self.ben1].timestamp
        )
        self.assertIn(
            os.path.join("shares", self.owner, subdir, "other_subdir"),
            server.User.users[self.ben1].paths
        )
        self.assertIn(
            os.path.join(
                "shares", self.owner, subdir, "other_subdir/new_file"
            ),
            server.User.users[self.ben1].paths
        )

        # remove a file and check
        received = self.tc.post(
            "{}actions/delete".format(_API_PREFIX),
            data={"path": os.path.join(subdir, "other_subdir/new_file")},
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)

        self.assertEqual(
            server.User.users[self.owner].timestamp,
            server.User.users[self.ben1].timestamp
        )
        self.assertNotIn(
            "/".join(["shares", self.owner, subdir, "other_subdir"]),
            server.User.users[self.ben1].paths
        )
        self.assertNotIn(
            "/".join(["shares", self.owner, subdir, "other_subdir/new_file"]),
            server.User.users[self.ben1].paths
        )

        # remove every file in shared subdir and check if the shared_resource
        # has been removed
        received = self.tc.post(
            "{}actions/delete".format(_API_PREFIX),
            data={"path": "/".join([subdir, filename])},
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)

        self.assertNotIn(
            os.path.join(
                server.USERS_DIRECTORIES, self.owner, subdir
            ),
            server.User.shared_resources
        )


if __name__ == '__main__':
    server.app.config.update(TESTING=True)
    server.app.testing = True

    # make tests!
    unittest.main()
