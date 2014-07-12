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

    def test_files_post(self):
        demo_path = "somepath/somefile.txt"
        DEMO_CLIENT.set_fake_usr(True)
        f = open(DEMO_FILE, "r")
        data = {"file_content": f}
        rv = DEMO_CLIENT.call("post", "files/" + demo_path, data)
        f.close()
        self.assertEqual(rv.status_code, 401)

        DEMO_CLIENT.set_fake_usr(False)
        f = open(DEMO_FILE, "r")
        data = {"file_content": f}
        rv = DEMO_CLIENT.call("post", "files/" + demo_path, data)
        f.close()
        self.assertEqual(rv.status_code, 201)
        with open("{}{}/{}".format(TEST_DIRECTORY, DEMO_USER, demo_path)) as f:
            uploaded_content = f.read()
            self.assertEqual(DEMO_CONTENT, uploaded_content)

        f = open(DEMO_FILE, "r")
        data = {"file_content": f}
        rv = DEMO_CLIENT.call("post", "files/" + demo_path, data)
        f.close()
        self.assertEqual(rv.status_code, 409)

    def test_files_get(self):
        client_path, server_path = set_tmp_params("dwn")
        DEMO_CLIENT.set_fake_usr(True)
        rv = DEMO_CLIENT.call("get", "files/" + client_path)
        self.assertEqual(rv.status_code, 401)

        DEMO_CLIENT.set_fake_usr(False)
        rv = DEMO_CLIENT.call("get", "files/" + client_path)
        self.assertEqual(rv.status_code, 200)

        with open(server_path) as f:
            got_content = f.read()
            self.assertEqual(DEMO_CONTENT, got_content)

        rv = DEMO_CLIENT.call("get", "files/" + NO_SERVER_PATH)
        self.assertEqual(rv.status_code, 404)

        os.remove(server_path)
        rv = DEMO_CLIENT.call("get", "files/" + client_path)
        self.assertEqual(rv.status_code, 410)

    def test_files_put(self):
        demo_path = "somepath/somefile.txt"

        client_path, server_path = set_tmp_params("pt")
        if not server_path in server.User.users[DEMO_USER].paths[client_path]:
            return

        f = open(DEMO_FILE, "r")
        data = {"file_content": f}
        DEMO_CLIENT.set_fake_usr(True)
        rv = DEMO_CLIENT.call("put", "files/" + demo_path, data)
        f.close()
        self.assertEqual(rv.status_code, 401)
        DEMO_CLIENT.set_fake_usr(False)
        f = open(DEMO_FILE, "r")
        data = {"file_content": f}
        rv = DEMO_CLIENT.call("put", "files/" + demo_path, data)
        f.close()
        self.assertEqual(rv.status_code, 201)

        with open("{}{}/{}".format(TEST_DIRECTORY, DEMO_USER, demo_path)) as f:
            put_content = f.read()
            self.assertEqual(DEMO_CONTENT, put_content)

        rv = DEMO_CLIENT.call("put", "files/" + NO_SERVER_PATH)
        self.assertEqual(rv.status_code, 404)

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

    def tearDown(self):
        os.remove(server.USERS_DATA)

    def test_add_share(self):
        # # check if it aborts, when the user doesn't exist
        # DEMO_CLIENT.set_fake_usr(True)
        # rv = DEMO_CLIENT.call("post", "shares/dir/usr")
        # self.assertEqual(rv.status_code, 401)
        # DEMO_CLIENT.set_fake_usr(False)

        # share a file
        with server.app.test_client() as tc:
            received = tc.post(
                "{}shares/{}/{}".format(_API_PREFIX, "ciao.txt", self.ben1),
                headers=self.owner_headers
            )
        self.assertEqual(received.status_code, 200)

        # share the subdir
        with server.app.test_client() as tc:
            received = tc.post(
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
        with server.app.test_client() as tc:
            received = tc.post(
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
        for verb in [tc.post, tc.put]:
            with open(os.path.join(TestShare.root, "demofile1.txt"), "r") as f:
                data = {"file_content": f}
                with server.app.test_client() as tc:
                    received = verb(
                        "{}files/{}".format(_API_PREFIX, destination),
                        data=data,
                        headers=self.ben1_headers
                    )
                    self.assertEqual(received.status_code, 403)

        # case Action delete
        data = {"path": destination}
        with server.app.test_client() as tc:
            received = tc.post(
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
        with server.app.test_client() as tc:
            for act in ["move", "copy"]:
                received = tc.post(
                    "{}actions/{}".format(_API_PREFIX, act),
                    data=data,
                    headers=self.ben1_headers
                )
                self.assertEqual(received.status_code, 403)

    def test_remove_beneficiary(self):
        tc = server.app.test_client()

        # test if aborts when the resource is not on the server
        received = tc.delete(
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
        received = tc.delete(
            "{}shares/{}/{}".format(
                _API_PREFIX, "shared_with_two_bens.txt", self.ben1
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 400)

        # share a file with a couple of users
        for beneficiary in [self.ben1, self.ben2]:
            received = tc.post(
                "{}shares/{}/{}".format(
                    _API_PREFIX, "shared_with_two_bens.txt", beneficiary
                ),
                headers=self.owner_headers
            )
            self.assertEqual(received.status_code, 200)

        # remove the first user from the share
        received = tc.delete(
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
        received = tc.delete(
            "{}shares/{}/{}".format(
                _API_PREFIX, "shared_with_two_bens.txt", self.ben2
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)
        self.assertNotIn(server_path, server.User.shared_resources)

if __name__ == '__main__':
    server.app.config.update(TESTING=True)
    server.app.testing = True

    # make tests!
    unittest.main()
