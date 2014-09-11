#!/usr/bin/env python
#-*- coding: utf-8 -*-

from passlib.hash import sha256_crypt
from base64 import b64encode
import ConfigParser
import tempfile
import unittest
import hashlib
import shutil
import json
import time
import os

from server import _API_PREFIX
import server


TEST_DIRECTORY = "test_users_dirs/"
TEST_USER_DATA = "test_user_data.json"
TEST_PENDING_USERS = "test_user_pending.tmp"

TEST_ROOT = os.path.dirname(__file__)
TEST_DIRECTORY = os.path.join(TEST_ROOT, TEST_DIRECTORY)
TEST_USER_DATA = os.path.join(TEST_ROOT, TEST_USER_DATA)
TEST_PENDING_USERS = os.path.join(TEST_ROOT, TEST_PENDING_USERS)


def add_pending_user(user, psw=None, code=None):
    underskin_user = {}

    if os.path.exists(TEST_PENDING_USERS):
        with open(TEST_PENDING_USERS, "r") as tmp_file:
            underskin_user = json.load(tmp_file)

    underskin_user[user] = {
        "password": psw,
        "code": code,
        "timestamp": time.time()}
    with open(TEST_PENDING_USERS, "w") as tmp_file:
        json.dump(underskin_user, tmp_file)


def add_active_user(user, psw=None):
    underskin_user = {}

    if not os.path.exists(TEST_USER_DATA):
        open(TEST_USER_DATA, "w").close()

    underskin_user[user] = {
        "paths": {"": ["user_dirs/fake_root", False, 1405197042.793583]},
        "psw": psw,
        "timestamp": 1405197042.793476
    }
    server.User.users = underskin_user
    with open(TEST_USER_DATA, "w") as tmp_file:
        json.dump(underskin_user, tmp_file)


def server_setup(root):
    server.SERVER_ROOT = root
    server.USERS_DIRECTORIES = os.path.join(root, "user_dirs/")
    server.USERS_DATA = os.path.join(root, "user_data.json")
    if not os.path.isdir(server.USERS_DIRECTORIES):
        os.makedirs(server.USERS_DIRECTORIES)
    server.User.user_class_init()


def make_headers(user, psw):
    return {
        "Authorization": "Basic "
        + b64encode("{0}:{1}".format(user, psw))
    }


def compare_file_content(first_file, second_file):
    with open(first_file, "r") as ff:
        with open(second_file, "r") as sf:
            return ff.read() == sf.read()


def create_temporary_file(content=None):
    tmp = tempfile.NamedTemporaryFile(delete=False)
    if content:
        tmp.write(content)
    else:
        tmp.write("Hello my dear,\nit's a beautiful day here in Compiobbi.")
    tmp.close()
    return tmp.name


def get_data(file_object):
    file_md5 = hashlib.md5(file_object.read()).hexdigest()
    file_object.seek(0)
    return {"file_content": file_object, 'file_md5': file_md5}


def mock_mail_init():
    app = server.Flask(__name__)
    app.config.update(
        MAIL_SERVER="smtp_address",
        MAIL_PORT="smtp_port",
        MAIL_USERNAME="smtp_username",
        MAIL_PASSWORD="smtp_password",
        TESTING=True
    )
    return server.Mail(app)


class TestSetupServer(unittest.TestCase):
    other_directory = os.path.join(
        os.path.dirname(__file__),
        "proppolo"
    )

    def setUp(self):
        server_setup(TestSetupServer.other_directory)

    def test_setup_server(self):
        self.assertEqual(
            server.USERS_DIRECTORIES,
            os.path.join(TestSetupServer.other_directory, "user_dirs/")
        )
        self.assertEqual(
            server.USERS_DATA,
            os.path.join(TestSetupServer.other_directory, "user_data.json")
        )
        self.assertTrue(
            os.path.isdir(server.USERS_DIRECTORIES)
        )

    def tearDown(self):
        shutil.rmtree(TestSetupServer.other_directory)


class TestFilesAPI(unittest.TestCase):
    user_test = "action_man"
    password_test = "password"
    url_radix = "files/"
    root = os.path.join(
        os.path.dirname(__file__),
        "demo_test/test_file"
    )
    test_file_name = os.path.join(
        root, "user_dirs", user_test, "random_file.txt"
    )

    @classmethod
    def setUpClass(cls):
        server.app.config.update(TESTING=True)
        server.app.testing = True

        cls.demo_file1 = create_temporary_file()
        cls.demo_file2 = create_temporary_file("ps, something new.")

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.demo_file2)
        os.unlink(cls.demo_file1)

    def setUp(self):
        shutil.copy(
            os.path.join(TestFilesAPI.root, "demo_user_data.json"),
            os.path.join(TestFilesAPI.root, "user_data.json")
        )
        server_setup(TestFilesAPI.root)
        self.tc = server.app.test_client()
        self.headers = make_headers(
            TestFilesAPI.user_test,
            TestFilesAPI.password_test
        )

    def tearDown(self):
        os.remove(os.path.join(TestFilesAPI.root, "user_data.json"))

    def test_fail_auth_post(self):
        # test fail authentication
        with open(TestFilesAPI.demo_file1, "r") as f:
            data = {"file_content": f}
            rv = self.tc.post(
                _API_PREFIX + TestFilesAPI.url_radix + "something",
                data=data,
                headers=make_headers("fake_user", "some_psw"))
            self.assertEqual(rv.status_code, 401)

    def test_post(self):
        url = "{}{}".format(
            TestFilesAPI.url_radix,
            "upload_file.txt"
        )

        # correct upload
        with open(TestFilesAPI.demo_file1, "r") as f:
            start = time.time()
            rv = self.tc.post(
                _API_PREFIX + url,
                data=get_data(f),
                headers=self.headers,
            )
            end = time.time()
            response = float(rv.get_data())
            self.assertLessEqual(start, response)
            self.assertGreaterEqual(end, response)
            self.assertEqual(rv.status_code, 201)

        uploaded_file = os.path.join(
            TestFilesAPI.root,
            "user_dirs",
            TestFilesAPI.user_test,
            "upload_file.txt"
        )
        self.assertTrue(
            compare_file_content(uploaded_file, TestFilesAPI.demo_file1)
        )

        # try to re-upload the same file to check conflict error
        with open(TestFilesAPI.demo_file1, "r") as f:
            rv = self.tc.post(
                _API_PREFIX + url,
                data=get_data(f),
                headers=self.headers
            )
            self.assertEqual(rv.status_code, 409)

        url = "{}{}".format(
            TestFilesAPI.url_radix,
            "upload_file2.txt"
        )

        # try to sent a wrong md5
        with open(TestFilesAPI.demo_file1, "r") as f:
            data = {"file_content": f, 'file_md5': 'fake_md5'}
            rv = self.tc.post(
                _API_PREFIX + url,
                data=data,
                headers=self.headers,
            )
            self.assertEqual(rv.status_code, 400)

        # restore
        os.remove(uploaded_file)

    def test_fail_auth_get(self):
        # fail authentication
        received = self.tc.get(
            _API_PREFIX + TestFilesAPI.url_radix + "something",
            headers=make_headers("fake_user", TestFilesAPI.password_test)
        )
        self.assertEqual(received.status_code, 401)

    def test_get(self):
        url = "{}{}".format(TestFilesAPI.url_radix, "random_file.txt")
        server_path = TestFilesAPI.test_file_name

        # downloading file
        received = self.tc.get(
            _API_PREFIX + url,
            headers=self.headers
        )
        self.assertEqual(received.status_code, 200)
        with open(server_path, "r") as f:
            self.assertEqual(json.loads(received.data), f.read())

        # try to download file not present
        url = "{}{}".format(TestFilesAPI.url_radix, "NO_SERVER_PATH")
        rv = self.tc.get(
            _API_PREFIX + url,
            headers=self.headers
        )
        self.assertEqual(rv.status_code, 404)

    def test_fail_auth_put(self):
        # fail authentication
        with open(TestFilesAPI.demo_file1, "r") as f:
            data = {"file_content": f}
            url = "{}{}".format(TestFilesAPI.url_radix, "random_file.txt")
            rv = self.tc.put(
                _API_PREFIX + url,
                data=data,
                headers=make_headers("fake_user", TestFilesAPI.password_test)
            )
            self.assertEqual(rv.status_code, 401)

    def test_put(self):
        # set-up
        cls = TestFilesAPI
        backup = os.path.join(
            cls.root, "user_dirs", cls.user_test, "backup_random_file.txt"
        )
        shutil.copy(cls.test_file_name, backup)

        # correct put
        with open(cls.demo_file1, "r") as f:
            url = "{}{}".format(cls.url_radix, "random_file.txt")
            start = time.time()
            rv = self.tc.put(
                _API_PREFIX + url,
                data=get_data(f),
                headers=self.headers
            )
            end = time.time()
            response = float(rv.get_data())
            self.assertLessEqual(start, response)
            self.assertGreaterEqual(end, response)
            self.assertEqual(rv.status_code, 201)

        self.assertTrue(
            compare_file_content(cls.test_file_name, cls.demo_file1)
        )

        # restore
        shutil.move(
            backup,
            cls.test_file_name
        )

        # wrong path
        with open(cls.demo_file1, "r") as f:
            url = "{}{}".format(cls.url_radix, "NO_SERVER_PATH")
            rv = self.tc.put(
                _API_PREFIX + url,
                data=get_data(f),
                headers=self.headers
            )
            self.assertEqual(rv.status_code, 404)

        # try to send a wrong md5
        with open(cls.demo_file1, "r") as f:
            data = {"file_content": f, 'file_md5': 'fake_path'}
            url = "{}{}".format(cls.url_radix, "random_file.txt")
            rv = self.tc.put(
                _API_PREFIX + url,
                data=data,
                headers=self.headers
            )
            self.assertEqual(rv.status_code, 400)

    def test_to_md5(self):
        cls = TestFilesAPI
        # setup
        demo_file1_copy = os.path.join(cls.root, "demofile1_copy.txt")
        shutil.copy(cls.demo_file1, demo_file1_copy)

        # check if two files with the same content have the same md5
        first_md5 = server.to_md5(cls.demo_file1)
        first_copy_md5 = server.to_md5(demo_file1_copy)
        self.assertEqual(first_md5, first_copy_md5)

        # tear down
        os.remove(demo_file1_copy)

        # check if two different files have different md5
        second_md5 = server.to_md5(cls.demo_file2)
        self.assertNotEqual(first_md5, second_md5)

        # check if, for a directory, returns False
        tmp_dir = tempfile.mkdtemp()
        self.assertFalse(server.to_md5(tmp_dir))
        os.rmdir(tmp_dir)

    def test_files_differences(self):
        data = {
            "user": "complex_user@gmail.com",
            "psw": "password"
        }
        headers = make_headers(data["user"], data["psw"])

        def get_diff():
            rv = self.tc.get(
                _API_PREFIX + self.url_radix,
                headers=headers
            )
            self.assertEqual(rv.status_code, 200)
            return json.loads(rv.data)

        try:
            # sometimes, due to an old failed test, theres is yet the user dir
            shutil.rmtree(
                os.path.join(TestFilesAPI.root, "user_dirs", data["user"])
            )
        except OSError:
            pass

        # first check: user created just now
        snapshot1 = get_diff()
        #the user has got only an empty folder and
        #the diff method lists only files
        self.assertEqual(snapshot1["snapshot"], {})

        # second check: insert some files
        some_paths = [
            "path1/cool_filename.txt",
            "path2/path3/yo.jpg"
        ]
        for p in some_paths:
            with open(TestFilesAPI.demo_file1, "r") as f:
                rv = self.tc.post(
                    "{}{}{}".format(_API_PREFIX, self.url_radix, p),
                    data=get_data(f),
                    headers=headers
                )
            self.assertEqual(rv.status_code, 201)

        snapshot2 = get_diff()
        self.assertGreater(snapshot2["timestamp"], snapshot1["timestamp"])
        self.assertEqual(len(snapshot2["snapshot"]), 1)
        for s in snapshot2["snapshot"].values():
            self.assertEqual(len(s), 2)

        # third check: delete a file
        data3 = {"path": some_paths[1]}
        rv = self.tc.post(
            _API_PREFIX + "actions/delete",
            data=data3,
            headers=headers
        )
        self.assertEqual(rv.status_code, 200)

        snapshot3 = get_diff()
        self.assertGreater(snapshot3["timestamp"], snapshot2["timestamp"])
        self.assertEqual(len(snapshot3["snapshot"]), 1)

        for s in snapshot3["snapshot"].values():
            self.assertEqual(len(s), 1)

        #restore
        shutil.rmtree(
            os.path.join(TestFilesAPI.root, "user_dirs", data["user"])
        )

    def test_create_server_path(self):
        # check if aborts when you pass invalid paths:
        invalid_paths = [
            "../file.txt",
            "folder/../file.txt"
        ]

        for p in invalid_paths:
            with open(TestFilesAPI.demo_file1, "r") as f:
                rv = self.tc.post(
                    "{}{}{}".format(_API_PREFIX, TestFilesAPI.url_radix, p),
                    data={"file_content": f},
                    headers=self.headers
                )
            self.assertEqual(rv.status_code, 400)


class TestActionsAPI(unittest.TestCase):
    user_test = "changeman"
    headers = make_headers(user_test, "password")
    url_radix = "actions/"
    actions_root = "actions_root"

    root = os.path.join(
        os.path.dirname(__file__),
        "demo_test/test_actions"
    )
    test_folder = os.path.join(
        root, "user_dirs", user_test
    )
    full_path1 = os.path.join(test_folder, "demo1")
    full_path2 = os.path.join(test_folder, "demo2")

    @classmethod
    def setUpClass(cls):
        server.app.config.update(TESTING=True)
        server.app.testing = True

        cls.demo_file1 = create_temporary_file()
        cls.demo_file2 = create_temporary_file("ps, something new.")

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.demo_file2)
        os.unlink(cls.demo_file1)

    def setUp(self):
        cls = TestActionsAPI

        def setup_the_file_on_disk():
            os.makedirs(cls.test_folder)
            shutil.copy(cls.demo_file1, cls.full_path1)
            shutil.copy(cls.demo_file2, cls.full_path2)
            shutil.copy(
                os.path.join(cls.root, "demo_user_data.json"),
                os.path.join(cls.root, "user_data.json")
            )
        try:
            setup_the_file_on_disk()
        except OSError:
            self.tearDown()
            setup_the_file_on_disk()

        server_setup(cls.root)
        self.tc = server.app.test_client()

    def tearDown(self):
        shutil.rmtree(TestActionsAPI.test_folder)
        os.remove(os.path.join(TestActionsAPI.root, "user_data.json"))

    def test_fail_auth_actions_delete(self):
        #try delete with fake_user
        rv = self.tc.post(
            "{}{}{}".format(_API_PREFIX, TestActionsAPI.url_radix, "delete"),
            headers=make_headers("fake_user", "p"),
            data={"path": "something"}
        )
        self.assertEqual(rv.status_code, 401)

    def test_actions_delete(self):
        cls = TestActionsAPI
        url = "{}{}{}".format(
            _API_PREFIX, TestActionsAPI.url_radix, "delete"
        )
        data = {"path": "demo1"}

        #try correct delete
        start = time.time()
        rv = self.tc.post(
            url,
            data=data,
            headers=self.headers
        )
        end = time.time()
        response = float(rv.get_data())
        self.assertLessEqual(start, response)
        self.assertGreaterEqual(end, response)
        self.assertEqual(rv.status_code, 200)
        self.assertFalse(os.path.isfile(cls.full_path1))
        #check if the file is correctly removed from the dictionary
        self.assertNotIn(
            os.path.join(cls.user_test, "demo1"),
            server.User.users[cls.user_test].paths
        )

        #try to delete a not present file
        data = {"path": "i_m_not_a_file"}
        rv = self.tc.post(
            url,
            headers=self.headers,
            data=data
        )
        self.assertEqual(rv.status_code, 404)

        # delete the last file and check if the user_directory is still alive
        data = {"path": "demo2"}
        rv = self.tc.post(
            url,
            headers=self.headers,
            data=data
        )
        self.assertEqual(rv.status_code, 200)
        user_dir = os.path.join(
            cls.root, "user_dirs/", cls.user_test
        )
        self.assertTrue(os.path.isdir(user_dir))

    def test_fail_auth_actions_copy(self):
         # try copy with a fake user
        cls = TestActionsAPI
        data = {"file_src": "demo1", "file_dest": "dest"}
        url = "{}{}{}".format(
            _API_PREFIX, cls.url_radix, "copy"
        )
        rv = self.tc.post(
            url,
            data=data,
            headers=make_headers("fake_user", "fail_pass")
        )
        self.assertEqual(rv.status_code, 401)

    def test_actions_copy(self):
        cls = TestActionsAPI
        data = {"file_src": "demo1", "file_dest": "dest"}
        url = "{}{}{}".format(
            _API_PREFIX, cls.url_radix, "copy"
        )

        # try correct copy
        start = time.time()
        rv = self.tc.post(
            url,
            data=data,
            headers=self.headers
        )
        end = time.time()
        response = float(rv.get_data())
        self.assertLessEqual(start, response)
        self.assertGreaterEqual(end, response)
        self.assertEqual(rv.status_code, 201)

        self.assertTrue(
            os.path.isfile(
                os.path.join(cls.root, "user_dirs", cls.user_test, "demo1")
            )
        )
        self.assertNotIn(
            os.path.join(cls.user_test, "demo1"),
            server.User.users[cls.user_test].paths
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(cls.root, "user_dirs", cls.user_test, "dest")
            )
        )
        self.assertNotIn(
            os.path.join(cls.user_test, "dest/demo1"),
            server.User.users[cls.user_test].paths
        )

        # try copy file with conflict
        data = {"file_src": "demo1", "file_dest": "demo1"}
        rv = self.tc.post(
            url,
            data=data,
            headers=self.headers
        )
        self.assertEqual(rv.status_code, 409)

    def test_fail_auth_actions_move(self):
        cls = TestActionsAPI
        url = "{}{}{}".format(_API_PREFIX, cls.url_radix, "move")
        data = {"file_src": "demo1", "file_dest": "mv/dest.txt"}

        # try to move something with a fake user
        received = self.tc.post(
            url, data=data, headers=make_headers("fake_user", "some_psw")
        )
        self.assertEqual(received.status_code, 401)

    def test_actions_move(self):
        cls = TestActionsAPI
        url = "{}{}{}".format(_API_PREFIX, cls.url_radix, "move")
        data = {"file_src": "demo1", "file_dest": "mv/dest.txt"}

        # test the correct move action
        start = time.time()
        received = self.tc.post(
            url, data=data, headers=self.headers
        )
        end = time.time()
        response = float(received.get_data())
        self.assertLessEqual(start, response)
        self.assertGreaterEqual(end, response)
        self.assertEqual(received.status_code, 201)
        # check the disk
        self.assertFalse(
            os.path.isfile(
                os.path.join(cls.test_folder, "demo1")
            )
        )
        self.assertTrue(
            os.path.isdir(
                os.path.join(cls.test_folder, "mv")
            )
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(cls.test_folder, "mv/dest.txt")
            )
        )
        # check the structure
        user_paths = server.User.users[cls.user_test].paths
        self.assertNotIn("demo1", user_paths)
        self.assertIn("mv", user_paths)
        self.assertIn("mv/dest.txt", user_paths)

        # test the status code returned when the source doesn't exist
        data = {"file_src": "not_a_file", "file_dest": "mv/dest2.txt"}
        received = self.tc.post(
            url, data=data, headers=self.headers
        )
        self.assertEqual(received.status_code, 404)

    def test_invalid_command(self):
        received = self.tc.post(
            "{}actions/{}".format(_API_PREFIX, "not_a_command"),
            headers=self.headers
        )
        self.assertEqual(received.status_code, 404)


class TestShare(unittest.TestCase):
    # TODO: to make indipendent tests here, we need to save the shares in some
    # way. It is a task. We can easily save them in a json, or wait for the
    # implementation of the database.
    root = os.path.join(
        os.path.dirname(__file__),
        "demo_test/test_share"
    )

    @classmethod
    def setUpClass(cls):
        server.app.config.update(TESTING=True)
        server.app.testing = True

        cls.demo_file1 = create_temporary_file()
        cls.demo_file2 = create_temporary_file("ps, something new.")

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.demo_file2)
        os.unlink(cls.demo_file1)

    def setUp(self):
        shutil.copy(
            os.path.join(TestShare.root, "demo_user_data.json"),
            os.path.join(TestShare.root, "user_data.json")
        )
        server_setup(TestShare.root)
        self.tc = server.app.test_client()

        # this class comes with some users
        self.owner = "Emilio@me.it"
        self.owner_headers = make_headers(self.owner, "password")
        self.ben1 = "Ben1@me.too"
        self.ben1_headers = make_headers(self.ben1, "password")
        self.ben2 = "Ben2@me.too"

    def tearDown(self):
        os.remove(server.USERS_DATA)
        server.User.shared_resources = {}

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

        # check if it aborts, when the beneficiary is the owner
        received = self.tc.post(
            "{}shares/{}/{}".format(_API_PREFIX, "ciao.txt", self.owner),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 400)

        # share a file
        received = self.tc.post(
            "{}shares/{}/{}".format(_API_PREFIX, "ciao.txt", self.ben1),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)

        # check if it aborts, when the resource is yet shared with that
        # beneficiary
        received = self.tc.post(
            "{}shares/{}/{}".format(_API_PREFIX, "ciao.txt", self.ben1),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 400)

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
        owner = "me"
        self.assertTrue(
            server.can_write(owner, owner + "/my_file.txt")
        )
        self.assertFalse(
            server.can_write(owner, owner + "/shares/my_file.txt")
        )
        self.assertFalse(
            server.can_write(owner, "other_user/my_file.txt")
        )

    def test_can_write_usage(self):
        # share a file with an user (create a share)
        received = self.tc.post(
            "{}shares/{}/{}".format(
                _API_PREFIX, "can_write", self.ben1
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)

        # a beneficiary tries to add a file to a shared directory, but the
        # share is read-only.
        # case Files POST
        destination = os.path.join(
            "shares", self.owner, "can_write", "new_file.txt"
        )
        with open(TestShare.demo_file1, "r") as f:
            data = {"file_content": f}
            received = self.tc.post(
                "{}files/{}".format(_API_PREFIX, destination),
                data=data,
                headers=self.ben1_headers
            )
            self.assertEqual(received.status_code, 403)

        # case Files PUT
        destination = os.path.join(
            "shares", self.owner, "can_write", "parole.txt"
        )
        with open(TestShare.demo_file1, "r") as f:
            data = {"file_content": f}
            received = self.tc.put(
                "{}files/{}".format(_API_PREFIX, destination),
                data=data,
                headers=self.ben1_headers
            )
            self.assertEqual(received.status_code, 403)

        # case Action delete
        received = self.tc.post(
            "{}actions/delete".format(_API_PREFIX),
            data={"path": destination},
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

    def test_share_in_a_subdirectory(self):
        received = self.tc.post(
            "{}shares/{}/{}".format(
                _API_PREFIX, "subdir/ciao.txt", self.ben1
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 400)

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

        # the owner tries to remove himself from the share (but he can't)
        received = self.tc.delete(
            "{}shares/{}/{}".format(
                _API_PREFIX, "shared_with_two_bens.txt", self.owner
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 400)

        # the beneficiary removes himself from the share (and he can)
        path_to_remove = "/".join(
            ["shares", self.owner, "shared_with_two_bens.txt"]
        )
        received = self.tc.delete(
            "{}shares/{}/{}".format(
                _API_PREFIX, path_to_remove, self.ben1
            ),
            headers=self.ben1_headers
        )
        self.assertEqual(received.status_code, 200)

        server_path = os.path.join(
            self.owner,
            "shared_with_two_bens.txt"
        )
        self.assertIn(server_path, server.User.shared_resources)
        self.assertEqual(
            server.User.shared_resources[server_path],
            [self.ben2]
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

        # setup
        sub_path = os.path.join(server.USERS_DIRECTORIES, self.owner, subdir)
        try:
            os.mkdir(sub_path)
        except OSError:
            shutil.rmtree(sub_path)
            os.mkdir(sub_path)
        shutil.copy2(TestShare.demo_file1, os.path.join(sub_path, filename))

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
        with open(TestShare.demo_file2, "r") as f:
            received = self.tc.put(
                "{}files/{}/{}".format(
                    _API_PREFIX, subdir, filename
                ),
                data=get_data(f),
                headers=self.owner_headers
            )
        self.assertEqual(received.status_code, 201)
        owner_new_timestamp = server.User.users[self.owner].timestamp
        self.assertGreater(owner_new_timestamp, owner_timestamp)

        ben_timestamp = server.User.users[self.ben1].timestamp
        self.assertEqual(owner_new_timestamp, ben_timestamp)

        # upload a new file in shared directory and check
        with open(TestShare.demo_file1, "r") as f:
            received = self.tc.post(
                "{}files/{}/{}".format(
                    _API_PREFIX, subdir, "other_subdir/new_file"
                ),
                data=get_data(f),
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
            os.path.join(self.owner, subdir),
            server.User.shared_resources
        )

    def test_get_shares_list(self):
        # setup: share the subdir
        received = self.tc.post(
            "{}shares/{}/{}".format(
                _API_PREFIX, "shared_directory", self.ben1
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)

        # get the shares list of the beneficiary
        received = self.tc.get(
            "{}shares/".format(
                _API_PREFIX
            ),
            headers=self.ben1_headers
        )
        self.assertEqual(received.status_code, 200)

        dicts = json.loads(received.get_data())
        self.assertDictEqual(dicts["my_shares"], {})
        self.assertDictEqual(
            dicts["other_shares"],
            {self.owner: "shares/{}/shared_directory".format(self.owner)}
        )

        # get the shares list of the owner
        received = self.tc.get(
            "{}shares/".format(
                _API_PREFIX
            ),
            headers=self.owner_headers
        )
        self.assertEqual(received.status_code, 200)

        dicts = json.loads(received.get_data())
        self.assertDictEqual(
            dicts["my_shares"],
            {"shared_directory": [self.ben1]}
        )
        self.assertDictEqual(dicts["other_shares"], {})

class TestServerInternalErrors(unittest.TestCase):
    root = os.path.join(
        os.path.dirname(__file__),
        "demo_test/internal_errors"
    )
    user_data = os.path.join(root, "user_data.json")
    user_dirs = os.path.join(root, "user_dirs")

    def setUp(self):
        server.app.config.update(TESTING=True)
        server.app.testing = True
        # Note: it's possible to make assertRaises on internal server
        # exceptions from the test_client only if app testing is True.

        server_setup(TestServerInternalErrors.root)
        self.tc = server.app.test_client()

    def tearDown(self):
        cls = TestServerInternalErrors
        try:
            shutil.rmtree(cls.user_dirs)
        except OSError:
            pass
        try:
            os.remove(cls.user_data)
        except OSError:
            pass

    def test_corrupted_users_data_json(self):
        """
        If the user data file is corrupted, it will be raised a ValueError.
        """
        shutil.copy(
            os.path.join(
                TestServerInternalErrors.root,
                "corrupted_user_data.json"
            ),
            self.user_data
        )
        with self.assertRaises(ValueError):
            server_setup(TestServerInternalErrors.root)

    def setup_inconsistent_paths(self):
        # If a path exists in some user's paths dictionary, but it's not in the
        # filesystem, when somebody will try to access it, it will be raised an
        # IOError and it will be returned a status code 500.
        cls = TestServerInternalErrors

        # setup
        shutil.copy(
            os.path.join(cls.root, "demo_user_data.json"),
            cls.user_data
        )
        server_setup(cls.root)

    def test_download_from_a_non_existent_path(self):
        """
        What happens when paths dictionary is inconsistent during download.
        """
        owner_headers = make_headers("Emilio@me.it", "password")
        owner_filepath = "ciao.txt"
        self.setup_inconsistent_paths()

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

    def test_access_to_non_existent_server_path(self):
        """
        What happens when paths dictionary is inconsistent during copy or move.
        """
        owner_headers = make_headers("Emilio@me.it", "password")
        owner_filepath = "ciao.txt"
        self.setup_inconsistent_paths()

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
            received = try_to_transfer(action)
            self.assertEqual(received.status_code, 500)
        server.app.testing = True

    def test_missing_email_settings_ini(self):
        """
        If email_settings.ini is missing it will be raised a NoSectionError.
        """
        # setup
        bak = server.EMAIL_SETTINGS_INI
        server.EMAIL_SETTINGS_INI = "not_a_file"

        # test
        with self.assertRaises(server.MissingConfigIni):
            server.mail_config_init()

        # tear down
        server.EMAIL_SETTINGS_INI = bak

    def test_corrupted_email_settings_ini(self):
        """
        If email_settings.ini is corrupted it will be raised a
        ConfigParserError.
        """
        flag_dry = False
        # setup
        try:
            shutil.copy(server.EMAIL_SETTINGS_INI, "email_ini.bak")
        except IOError:
            # probably running in Travis: there is not email_settings.ini
            flag_dry = True
            pass
        open(server.EMAIL_SETTINGS_INI, "w").close()

        # test
        with self.assertRaises(ConfigParser.Error):
            server.mail_config_init()

        # tear down
        if flag_dry:
            os.remove(server.EMAIL_SETTINGS_INI)
        else:
            shutil.move("email_ini.bak", server.EMAIL_SETTINGS_INI)


class EmailTest(unittest.TestCase):
    email = "test@rawbox.com"
    obj = "test"
    content = "test content"
    user = "user_mail@demo.it"
    psw = "33password_demo.PA"
    code = "5f8e441f01abc7b3e312917efb52cc12"  # os.urandom(16).encode('hex')

    def setUp(self):
        self.mail_init_bak = server.mail_config_init
        server.mail_config_init = mock_mail_init

        EmailTest.pending_users_bak = server.PENDING_USERS
        server.PENDING_USERS = TEST_PENDING_USERS

        self.email = "test@rawbox.com"
        self.obj = "test"
        self.content = "test content"

        self.user = "user_mail@demo.it"
        self.psw = "password_demo33.PA"
        self.code = "5f8e441f01abc7b3e312917efb52cc12"  # os.urandom(16).encode('hex')
        self.url = "".join((server._API_PREFIX, "Users/", self.user))

        self.mail = server.Mail(server.Flask(__name__))
        self.tc = server.app.test_client()

    def tearDown(self):
        server.User.users = {}
        if os.path.exists(TEST_PENDING_USERS):
            os.remove(TEST_PENDING_USERS)

        server.mail_config_init = self.mail_init_bak
        server.PENDING_USERS = EmailTest.pending_users_bak

    def test_create_user_email(self):
        data = {
            "psw": self.psw
        }
        with self.mail.record_messages() as outbox:
            self.tc.post(self.url, data=data, headers=None)
            self.assertEqual(len(outbox), 1)
            with open(server.PENDING_USERS, "r") as pending_file:
                code = json.load(pending_file)[self.user]["code"]
                self.assertEqual(outbox[0].body, code)


class UserActions(unittest.TestCase):

    MAIL_SERVER = "smtp_address"
    MAIL_PORT = "smtp_port"
    MAIL_USERNAME = "smtp_username"
    MAIL_PASSWORD = "smtp_password"
    TESTING = True

    user = "user_mail@demo.it"
    psw = "$5$rounds=110000$9adcJL7bfKtZF/ii$p2vfrEbvs529hRMyQuW9LUIxiZvVKj8t62fB/7SZQSC"
    code = "5f8e441f01abc7b3e312917efb52cc12"  # os.urandom(16).encode('hex')

    def setUp(self):
        self.mail_init_bak = server.mail_config_init
        server.mail_config_init = mock_mail_init

        self.app = server.Flask(__name__)
        self.mail = server.Mail(self.app)

        self.app.config.from_object(__name__)
        server.app.config.update(TESTING=True)
        self.tc = server.app.test_client()

        try:
            os.mkdir(TEST_DIRECTORY)
        except OSError:
            shutil.rmtree(TEST_DIRECTORY)
            os.mkdir(TEST_DIRECTORY)

        shutil.copy(
            os.path.join(
                os.path.dirname(__file__),
                "user_dirs/not_write_in_share_model.txt"
            ),
            TEST_DIRECTORY
        )

        server.USERS_DIRECTORIES = TEST_DIRECTORY

        server.PENDING_USERS = TEST_PENDING_USERS

        open(TEST_USER_DATA, "w").close()
        server.USERS_DATA = TEST_USER_DATA

        self.user = "user_mail@demo.it"
        self.psw = "$5$rounds=110000$9adcJL7bfKtZF/ii$p2vfrEbvs529hRMyQuW9LUIxiZvVKj8t62fB/7SZQSC"
        self.code = "5f8e441f01abc7b3e312917efb52cc12"  # os.urandom(16).encode('hex')
        self.url = "".join((server._API_PREFIX, "Users/", self.user))

    def tearDown(self):
        server.mail_config_init = self.mail_init_bak
        server.User.users = {}
        if os.path.exists(TEST_PENDING_USERS):
            os.remove(TEST_PENDING_USERS)
        if os.path.exists(TEST_USER_DATA):
            os.remove(TEST_USER_DATA)
        try:
            shutil.rmtree(TEST_DIRECTORY)
        except OSError:
            pass

    def test_create_user_pw_too_short(self):
        data = {
            "psw": "pro"
        }

        response = self.tc.post(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_NOT_ACCEPTABLE)

    def test_create_user_pw_too_common(self):
        data = {
            "psw": "123456"
        }
        response = self.tc.post(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_NOT_ACCEPTABLE)

    def test_create_user_too_easy(self):
        data = {
            "psw": "provasemplice"
        }

        response = self.tc.post(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_NOT_ACCEPTABLE)

    def test_create_user(self):
        data = {
            "psw": self.psw
        }

        before_request_time = time.time()
        response = self.tc.post(self.url, data=data)
        self.assertEqual(response.status_code, server.HTTP_CREATED)
        after_request_time = time.time()

        with open(server.PENDING_USERS, "r") as pending_file:
            data = json.load(pending_file)
            user = data.keys()[0]
            self.assertEqual(user, self.user)
            psw = data[self.user]["password"]
            self.assertTrue(sha256_crypt.verify(self.psw, psw))
            code = data[self.user]["code"]
            self.assertIsNotNone(code)
            self.assertEqual(len(code), 32)
            request_time = data[self.user]["timestamp"]
            self.assertTrue(before_request_time < request_time < after_request_time)

    def test_create_user_missing_password(self):
        data = {}

        response = self.tc.post(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_BAD_REQUEST)

    def test_create_user_that_is_already_pending(self):
        data = {
            "psw": self.psw
        }

        add_active_user(self.user, self.psw)
        response = self.tc.post(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_CONFLICT)

    def test_create_user_that_is_already_active(self):
        data = {
            "psw": self.psw
        }

        add_active_user(self.user, self.psw)
        response = self.tc.post(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_CONFLICT)

    def test_activate_user(self):
        data = {
            "code": self.code
        }

        add_pending_user(self.user, self.psw, self.code)
        response = self.tc.put(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_CREATED)

    def test_activate_user_missing_code(self):
        data = {}

        add_pending_user(self.user, self.psw)
        response = self.tc.put(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_BAD_REQUEST)

    def test_activate_user_that_is_already_active(self):
        data = {
            "code": self.code
        }

        add_active_user(self.user, self.psw)
        response = self.tc.put(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_CONFLICT)

    def test_activate_user_that_is_not_the_last_pending_user(self):
        data = {
            "code": self.code
        }

        add_pending_user("fake_user@demo.it",
                         sha256_crypt.encrypt("fake_password"),
                         "this0is0a0fake0code0long32char00")
        add_pending_user(self.user, self.psw, self.code)
        response = self.tc.put(self.url, data=data, headers=None)
        self.assertEqual(response.status_code, server.HTTP_CREATED)
        self.assertTrue(os.path.exists(TEST_PENDING_USERS))

    def test_activate_user_whose_directory_already_present(self):
        """
        Check about a possible internal error.
        If, activating a new user, when the User is really created, a directory
        with his/her name is already present, it will be raised an OSError and
        it will be returned a status code 500.
        """
        cls = UserActions
        os.makedirs(os.path.join(server.USERS_DIRECTORIES, cls.user))
        #self.inject_user(TEST_PENDING_USERS, cls.user, cls.psw, cls.code)
        add_pending_user(cls.user, cls.psw, cls.code)

        def try_to_create_user():
            received = self.tc.put(
                self.url,
                data={"code": cls.code}
            )
            return received

        # check if OSError is raised
        server.app.testing = True
        with self.assertRaises(OSError):
            try_to_create_user()

        # check if returns 500
        server.app.testing = False
        received = try_to_create_user()
        self.assertEqual(received.status_code, 500)
        server.app.testing = True

    def test_delete_user(self):
        headers = make_headers(self.user, "password")
        root = os.path.join(TEST_ROOT, "demo_test/test_user_actions")
        shutil.copy(root + "/demo_user_data.json", root + "/user_data.json")
        os.makedirs(os.path.join(root, "user_dirs", self.user))
        server_setup(root)
        url = "".join((server._API_PREFIX, "Users/"))
        response = self.tc.delete(url, headers=headers)
        self.assertEqual(response.status_code, server.HTTP_OK)
        os.remove(root + "/user_data.json")


if __name__ == "__main__":
    # make tests!
    unittest.main()
