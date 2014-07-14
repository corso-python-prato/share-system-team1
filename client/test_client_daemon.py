from client_daemon import DirSnapshotManager
from client_daemon import DirectoryEventHandler
from client_daemon import ServerCommunicator
from client_daemon import FileSystemOperator
from client_daemon import CommandExecuter
from client_daemon import get_abspath
from client_daemon import get_relpath
from client_daemon import load_config

#Watchdog event import for event_handler test
from watchdog.events import FileDeletedEvent
from watchdog.events import FileModifiedEvent
from watchdog.events import FileCreatedEvent
from watchdog.events import FileMovedEvent
from watchdog.events import DirDeletedEvent
from watchdog.events import DirModifiedEvent
from watchdog.events import DirCreatedEvent
from watchdog.events import DirMovedEvent
import client_daemon
import httpretty
import unittest
import hashlib
import base64
import shutil
import copy
import json
import os

class TestEnvironment(object):

    def create(self):
        self.test_main_path = os.path.join(os.path.expanduser('~'), 'test_path')
        os.makedirs(self.test_main_path)
        self.test_share_dir = os.path.join(self.test_main_path, 'shared_dir')
        os.makedirs(self.test_share_dir)

        self.test_folder_1 = os.path.join(self.test_share_dir, 'sub_dir_1')
        self.test_folder_2 = os.path.join(self.test_share_dir, 'sub_dir_2')
        os.makedirs(self.test_folder_1)
        os.makedirs(self.test_folder_2)
        self.test_file_1 = os.path.join(self.test_share_dir, 'sub_dir_1', 'test_file_1.txt')
        self.test_file_2 = os.path.join(self.test_share_dir, 'sub_dir_2', 'test_file_2.txt')
        open(self.test_file_1, 'w').write('Lorem ipsum dolor sit amet')
        open(self.test_file_2, 'w').write('Integer non tincidunt dolor')

        self.conf_snap_path = os.path.join(self.test_main_path, 'snapshot_file.json')
        self.conf_snap_gen = {"timestamp": 123123, "snapshot": "ab8d6b3c332aa253bb2b471c57b73e27"}

        open(self.conf_snap_path, 'w').write(json.dumps(self.conf_snap_gen))

        return self.test_main_path, self.test_share_dir, self.test_folder_1, self.test_folder_2, self.test_file_1, self.test_file_2, self.conf_snap_path, self.conf_snap_gen


    def remove(self):
        shutil.rmtree(self.test_main_path)


class ServerCommunicatorTest(unittest.TestCase):

    def setUp(self):
        class DirSnapshotManager(object):

            def __init__(self):
                self.server_snapshot = False
                self.server_timestamp = False
                self.command_list = False
                self.action = False
                self.body = False

            def syncronize_dispatcher(self, server_timestamp, server_snapshot):
                self.server_timestamp = server_timestamp
                self.server_snapshot = server_snapshot
                return ['command']

            def save_snapshot(self, timestamp):
                self.timestamp = timestamp

            def update_snapshot(self, action, body):
                self.action = action
                self.body = body

            def save_timestamp(self, timestamp):
                self.server_timestamp = timestamp

            def update_snapshot_delete(self, body):
                self.update = body

        httpretty.enable()
        httpretty.register_uri(
            httpretty.POST,
            'http://127.0.0.1:5000/API/v1/files/f_for_cdaemon_test.txt')
        httpretty.register_uri(
            httpretty.PUT,
            'http://127.0.0.1:5000/API/v1/files/f_for_cdaemon_test.txt')
        httpretty.register_uri(
            httpretty.GET,
            'http://127.0.0.1:5000/API/v1/files/f_for_cdaemon_test.txt',
            body='[{"title": "Test"}]',
            content_type="text/txt")
        httpretty.register_uri(
            httpretty.POST,
            'http://127.0.0.1:5000/API/v1/actions/delete')
        httpretty.register_uri(
            httpretty.POST,
            'http://127.0.0.1:5000/API/v1/actions/move')
        httpretty.register_uri(
            httpretty.POST,
            'http://127.0.0.1:5000/API/v1/actions/copy')
        httpretty.register_uri(
            httpretty.POST,
            'http://127.0.0.1:5000/API/v1/create_user',
            status=201)
        httpretty.register_uri(httpretty.GET,
            'http://127.0.0.1:5000/API/v1/files',
            body=str({
                '9406539a103956dc36cb7ad35547198c': [{"path": u'/Users/marc0/progetto/prove_deamon\\bla.txt',"timestamp":123123}],
                'a8f5f167f44f4964e6c998dee827110c': [{"path": u'vecchio.txt',"timestamp":123122}], 
                'c21e1af364fa17cc80e0bbec2dd2ce5c': [{"path": u'/Users/marc0/progetto/prove_deamon\\asdas\\asdasd.txt',"timestamp":123123}], 
                'd41d8cd98f00b204e9800998ecf8427e': [{"path": u'/Users/marc0/progetto/prove_deamon\\dsa.txt',"timestamp":123122},#old timestamp 
                                                    {"path":  u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (2).txt',"timestamp":123123}, 
                                                    {"path":  u'server path in piu copiata',"timestamp":123123}],
                'a8f5f167f44f4964e6c998dee827110b': [{"path":  u'nuova path server con md5 nuovo',"timestamp":123123}],
                'a8f5f167f44f4964e6c998eee827110b': [{"path":  u'nuova path server con md5 nuovo e timestamp minore',"timestamp":123122}]}),
                content_type="application/json"
        )

        self.dir = "/tmp/home/test_rawbox/folder"
        client_daemon.CONFIG_DIR_PATH = self.dir
        self.another_dir = "/tmp/home/test_rawbox/folder/other_folder"
        file_name = "f_for_cdaemon_test.txt"
        if not os.path.exists(self.dir):
            os.makedirs(self.dir, 0755)
        if not os.path.exists(self.another_dir):
            os.makedirs(self.another_dir, 0775)
        self.file_path = os.path.join(self.dir, file_name)
        self.another_path = os.path.join(self.another_dir, file_name)
        with open(self.file_path, 'w') as temp_file:
                temp_file.write('test_file')
        self.username = "usernameFarlocco"
        self.password = "passwordSegretissima"
        snapshot_manager = DirSnapshotManager()
        self.server_comm = ServerCommunicator(
            'http://127.0.0.1:5000/API/v1',
            self.username,
            self.password,
            snapshot_manager)
        
    def tearDown(self):
        httpretty.disable()
        httpretty.reset()

    def test_setexecuter(self):
        executer = "executer"
        self.server_comm.setExecuter(executer)
        self.assertEqual(
            self.server_comm.executer,
            executer)

    def test_get_url_relpath(self):
        #Case: rigth separator
        os.path.sep = '/'
        test_path = "/test/path"
        result = self.server_comm.get_url_relpath(test_path)
        self.assertEqual(result, test_path)

        #Case: other os separator
        os.path.sep = "-"
        test_path = "-test-path"
        expected_result = "/test/path"
        result = self.server_comm.get_url_relpath(test_path)
        self.assertEqual(result, expected_result)

    def test_upload(self):
        put_file=True
        mock_auth_user = ":".join([self.username, self.password])
        self.server_comm.upload_file(self.file_path, put_file)
        encoded = httpretty.last_request().headers['authorization'].split()[1]
        authorization_decoded = base64.decodestring(encoded)
        path = httpretty.last_request().path
        host = httpretty.last_request().headers['host']
        method = httpretty.last_request().method

        #check if authorizations are equal
        self.assertEqual(authorization_decoded, mock_auth_user)
        #check if url and methods are equal
        self.assertEqual(path, '/API/v1/files/f_for_cdaemon_test.txt')
        self.assertEqual(host, '127.0.0.1:5000')
        self.assertEqual(method, 'PUT')

        put_file = False
        mock_auth_user = ":".join([self.username, self.password])
        self.server_comm.upload_file(self.file_path, put_file)
        encoded = httpretty.last_request().headers['authorization'].split()[1]
        authorization_decoded = base64.decodestring(encoded)
        path = httpretty.last_request().path
        host = httpretty.last_request().headers['host']
        method = httpretty.last_request().method

        #check if authorizations are equal
        self.assertEqual(authorization_decoded, mock_auth_user)
        #check if url and methods are equal
        self.assertEqual(path, '/API/v1/files/f_for_cdaemon_test.txt')
        self.assertEqual(host, '127.0.0.1:5000')
        self.assertEqual(method, 'POST')

        #Case: IOError for file
        filepath = "not/corret/path"
        self.assertFalse(self.server_comm.upload_file(filepath))

    def test_download(self):
        mock_auth_user = ":".join([self.username, self.password])
        response = self.server_comm.download_file(self.file_path)
        encoded = httpretty.last_request().headers['authorization'].split()[1]
        authorization_decoded = base64.decodestring(encoded)
        path = httpretty.last_request().path
        host = httpretty.last_request().headers['host']
        method = httpretty.last_request().method

        #check if authorization are equal
        self.assertEqual(authorization_decoded, mock_auth_user)
        #check if url and host are equal
        self.assertEqual(path, '/API/v1/files/f_for_cdaemon_test.txt')
        self.assertEqual(host, '127.0.0.1:5000')
        #check if methods are equal
        self.assertEqual(method, 'GET')
        #check response's body
        self.assertEqual(response[1], u'[{"title": "Test"}]')

        #Case: server bad request
        def _try_request(self, *args, **kwargs):
            class Response(object):
                def __init__(self):
                    self.status_code = 400
            response = Response()
            return response

        self.server_comm._try_request = _try_request
        response = self.server_comm.download_file(self.file_path)
        self.assertEqual(response, (False, False))

    def test_delete_file(self):
        mock_auth_user = ":".join([self.username, self.password])
        self.server_comm.delete_file(self.file_path)
        encoded = httpretty.last_request().headers['authorization'].split()[1]
        authorization_decoded = base64.decodestring(encoded)
        path = httpretty.last_request().path
        host = httpretty.last_request().headers['host']
        method = httpretty.last_request().method

        #check if authorization are equal
        self.assertEqual(authorization_decoded, mock_auth_user)
        #check if url and host are equal
        self.assertEqual(path, '/API/v1/actions/delete')
        self.assertEqual(host, '127.0.0.1:5000')
        #check if methods are equal
        self.assertEqual(method, 'POST')
        self.assertEqual(
            self.server_comm.snapshot_manager.update,
            {"src_path": self.file_path})

    def test_move_file(self):
        mock_auth_user = ":".join([self.username, self.password])
        self.server_comm.move_file(self.file_path, self.another_path)
        encoded = httpretty.last_request().headers['authorization'].split()[1]
        authorization_decoded = base64.decodestring(encoded)
        path = httpretty.last_request().path
        host = httpretty.last_request().headers['host']
        method = httpretty.last_request().method

        #check if authorization are equal
        self.assertEqual(authorization_decoded, mock_auth_user)
        #check if url and host are equal
        self.assertEqual(path, '/API/v1/actions/move')
        self.assertEqual(host, '127.0.0.1:5000')
        #check if methods are equal
        self.assertEqual(method, 'POST')

    def test_copy_file(self):
        mock_auth_user = ":".join([self.username, self.password])
        self.server_comm.copy_file(self.file_path, self.another_path)
        encoded = httpretty.last_request().headers['authorization'].split()[1]
        authorization_decoded = base64.decodestring(encoded)
        path = httpretty.last_request().path
        host = httpretty.last_request().headers['host']
        method = httpretty.last_request().method

        #check if authorization are equal
        self.assertEqual(authorization_decoded, mock_auth_user)
        #check if url and host are equal
        self.assertEqual(path, '/API/v1/actions/copy')
        self.assertEqual(host, '127.0.0.1:5000')
        #check if methods are equal
        self.assertEqual(method, 'POST')

    def test_create_user(self):
        test_username = "test_username"
        test_password = "test_password"
        mock_auth_user = ":".join([self.username, self.password])
        self.server_comm.create_user(test_username, test_password)
        encoded = httpretty.last_request().headers['authorization'].split()[1]
        authorization_decoded = base64.decodestring(encoded)
        path = httpretty.last_request().path
        host = httpretty.last_request().headers['host']
        method = httpretty.last_request().method

        #check if authorization are equal
        self.assertEqual(authorization_decoded, mock_auth_user)
        #check if url and host are equal
        self.assertEqual(path, '/API/v1/create_user')
        self.assertEqual(host, '127.0.0.1:5000')
        #check if methods are equal
        self.assertEqual(method, 'POST')
    
    def test_syncronize(self):
        def my_try_request(*args, **kwargs):
            class obj (object):
                text={
                    'timestamp': 123123,
                    'snapshot': u'1234uh34h5bhj124b',
                }
                status_code = 'boh'
                def json(self):
                    return self.text
            return obj()
        class Executer(object):
            def __init__(self):
                self.status=False

            def syncronize_executer(self, command_list):
                self.status=True

        executer = Executer()
        self.server_comm.executer = executer
        self.server_comm._try_request = my_try_request
        self.server_comm.synchronize("mock")
        self.assertEqual(executer.status, True)


class FileSystemOperatorTest(unittest.TestCase):

    def setUp(self):
        class DirSnapshotManager(object):
            def __init__(self):
                self.delete = False
                self.move = False
                self.copy = False
                self.upload = False

            def update_snapshot_delete(self, body):
                self.delete = body

            def update_snapshot_move(self, body):
                self.move = body

            def update_snapshot_copy(self, body):
                self.copy = body

            def update_snapshot_upload(self, body):
                self.upload = body

        self.client_path = '/tmp/user_dir'
        client_daemon.CONFIG_DIR_PATH = self.client_path
        self.filename = 'test_file_1.txt'
        if not os.path.exists(self.client_path):
            os.makedirs(self.client_path)
        httpretty.enable()
        httpretty.register_uri(httpretty.GET, 'http://localhost/api/v1/files/{}'.format(self.filename),
            body='this is a test',
            content_type='text/plain')
        self.snapshot_manager = DirSnapshotManager()
        self.server_com = ServerCommunicator(
            server_url='http://localhost/api/v1',
            username='usernameFarlocco',
            password='passwordSegretissima',
            snapshot_manager= self.snapshot_manager)
        self.event_handler = DirectoryEventHandler(self.server_com,
            self.snapshot_manager)
        self.file_system_op = FileSystemOperator(self.event_handler,
            self.server_com, snapshot_manager = self.snapshot_manager)

    def tearDown(self):
        httpretty.disable()

    def test_add_event_to_ignore(self):
        test_path = "/test/path"
        self.file_system_op.add_event_to_ignore(test_path)
        self.assertEqual(
            self.event_handler.paths_ignored,
            [test_path])

    def test_write_a_file(self):
        source_path = '{}/{}'.format(self.client_path, self.filename)
        self.file_system_op.write_a_file(source_path)
        written_file = open('{}/{}'.format(self.client_path,self.filename), 'rb').read()
        self.assertEqual('this is a test', written_file)
        self.assertEqual(
            self.snapshot_manager.upload,
            {"src_path": source_path})
        #check if source isadded by write_a_file
        self.assertEqual([source_path], self.event_handler.paths_ignored)

        #reset variable
        self.snapshot_manager.upload = False
        self.event_handler.paths_ignored = []

        #Case: file not found on server
        def download_file(path):
            return None, None
        self.server_com.download_file = download_file
        self.file_system_op.write_a_file(source_path)
        self.assertFalse(self.snapshot_manager.upload)
        self.assertEqual(self.event_handler.paths_ignored, [])
    def test_move_a_file(self):
        f_name = 'file_to_move.txt'
        file_to_move = open('{}/{}'.format(self.client_path, f_name), 'w')
        file_to_move.write('this is a test')
        source_path = file_to_move.name
        dest_path = '{}/{}.moved'.format(self.client_path, f_name)
        file_to_move.close()
        self.file_system_op.move_a_file(source_path, dest_path)
        written_file = open(dest_path, 'rb').read()
        self.assertEqual('this is a test', written_file)
        self.assertEqual(
            self.snapshot_manager.move,
            {"src_path": source_path, "dst_path": dest_path})
        #check if source and dest path are added by move_a_file
        self.assertEqual([source_path, dest_path], self.event_handler.paths_ignored)

    def test_copy_a_file(self):
        f_name = 'file_to_copy.txt'
        file_to_copy = open('{}/{}'.format(self.client_path, f_name), 'w')
        file_to_copy.write('this is a test')
        source_path = file_to_copy.name
        dest_path = '{}/{}.copy'.format(self.client_path, f_name)
        file_to_copy.close()
        self.file_system_op.copy_a_file(source_path, dest_path)
        copied_file = open(dest_path, 'rb').read()
        self.assertEqual('this is a test', copied_file)
        self.assertEqual(
            self.snapshot_manager.copy,
            {"src_path": source_path, "dst_path": dest_path})
        #check if only dest_path is added by copy_a_file
        self.assertEqual([dest_path], self.event_handler.paths_ignored)

    def test_delete_a_file(self):
        del_dir = 'to_delete'
        source_path = '{}/to_delete'.format(self.client_path)
        if not os.path.exists(source_path):
            os.makedirs('{}/{}'.format(self.client_path, del_dir))
        f_name = 'file_to_delete.txt'
        file_to_delete = open('{}/{}/{}'.format(self.client_path, del_dir, f_name), 'w')
        file_to_delete.write('delete me')
        file_to_delete.close()

        self.assertTrue(os.path.exists(file_to_delete.name))
        self.file_system_op.delete_a_file(file_to_delete.name)
        self.assertFalse(os.path.exists(file_to_delete.name))
        self.assertEqual(
            self.snapshot_manager.delete,
            {"src_path": file_to_delete.name})

        self.file_system_op.delete_a_file(source_path)
        self.assertFalse(os.path.exists(source_path))
        self.assertEqual(
            self.snapshot_manager.delete,
            {"src_path": source_path})
        #check if only source_path is added by delete_a_file in the 2 tested case
        self.assertEqual([file_to_delete.name, source_path], self.event_handler.paths_ignored)


class DirSnapshotManagerTest(unittest.TestCase):
    def setUp(self):
        #Generate test folder tree and configuration file
        self.environment = TestEnvironment()
        self.test_main_path, self.test_share_dir, self.test_folder_1, self.test_folder_2, self.test_file_1, self.test_file_2, self.conf_snap_path, self.conf_snap_gen = self.environment.create()
        client_daemon.CONFIG_DIR_PATH = self.test_share_dir

        self.true_snapshot= {
            '81bcb26fd4acfaa5d0acc7eef1d3013a': ['sub_dir_2/test_file_2.txt'],
            'fea80f2db003d4ebc4536023814aa885': ['sub_dir_1/test_file_1.txt'],
        }
        self.md5_snapshot = 'ab8d6b3c332aa253bb2b471c57b73e27'
        self.snapshot_manager = DirSnapshotManager(self.conf_snap_path)

    def tearDown(self):
        self.environment.remove()

    def test_diff_snapshot_paths(self):
        #server snapshot unsinket with local path:
        #   sub_dir_1/test_file_1.txt modified
        #   sub_dir_2/test_file_3.txt added
        #   sub_dir_2/test_file_3.txt deleted
        unsinked_server_snap = {
            'fea80f2db004d4ebc4536023814aa885': [{'path': u'sub_dir_1/test_file_1.txt', 'timestamp': 123124}],
            '456jk3b334bb33463463fbhj4b3534t3': [{'path': u'sub_dir_2/test_file_3.txt', 'timestamp': 123125}],
        }

        new_client, new_server, equal = self.snapshot_manager.diff_snapshot_paths(self.true_snapshot, unsinked_server_snap)

        self.assertEqual(['sub_dir_2/test_file_2.txt'], new_client)
        self.assertEqual(['sub_dir_2/test_file_3.txt'], new_server)
        self.assertEqual(['sub_dir_1/test_file_1.txt'], equal)

    def test_syncronize_dispatcher(self):
        #server snapshot sinked with local path
        sinked_server_snap = {
            '81bcb26fd4acfaa5d0acc7eef1d3013a': [
                {'path': u'sub_dir_2/test_file_2.txt', 'timestamp': 123123}],
            'fea80f2db003d4ebc4536023814aa885': [
                {'path': u'sub_dir_1/test_file_1.txt', 'timestamp': 123123}],
        }
        #server snapshot unsinket with local path:
        #   sub_dir_1/test_file_1.txt modified
        #   sub_dir_2/test_file_1.txt added
        unsinked_server_snap = {
            '81bcb26fd4acfaa5d0acc7eef1d3013a': [
                {'path': u'sub_dir_2/test_file_2.txt', 'timestamp': 123123}],
            'fea80f2db004d4ebc4536023814aa885': [
                {'path': u'sub_dir_1/test_file_1.txt', 'timestamp': 123124}],
            '456jk3b334bb33463463fbhj4b3534t3': [
                {'path': u'sub_dir_2/test_file_3.txt', 'timestamp': 123125}],
        }

        sinked_timestamp = 123123
        unsinked_timestamp = 123125

        #Case: no deamon internal conflicts == timestamp
        expected_result = []
        result = self.snapshot_manager.syncronize_dispatcher(
            server_timestamp=sinked_timestamp,
            server_snapshot=sinked_server_snap)
        self.assertEqual(result, expected_result)

        #Case: no deamon internal conflicts != timestamp
        expected_result = [
            {'local_download': ['sub_dir_2/test_file_3.txt']},
            {'local_download': ['sub_dir_1/test_file_1.txt']},
        ]
        result = self.snapshot_manager.syncronize_dispatcher(
            server_timestamp=unsinked_timestamp,
            server_snapshot=unsinked_server_snap)
        self.assertEqual(result, expected_result)

        #Case: deamon internal conflicts == timestamp
        self.snapshot_manager.last_status['snapshot'] = "21451512512512512"
        expected_result = []
        result = self.snapshot_manager.syncronize_dispatcher(
            server_timestamp=sinked_timestamp,
            server_snapshot=sinked_server_snap)
        self.assertEqual(result, expected_result)

        #Case: no deamon internal conflicts != timestamp
        expected_result = [
            {'local_download': ['sub_dir_2/test_file_3.txt']},
            {'local_copy': [
                'sub_dir_1/test_file_1.txt',
                'sub_dir_1/test_file_1.txt.conflicted']},
            {'remote_upload': ['sub_dir_1/test_file_1.txt.conflicted']},
        ]
        result = self.snapshot_manager.syncronize_dispatcher(
            server_timestamp=unsinked_timestamp,
            server_snapshot=unsinked_server_snap)
        self.assertEqual(result, expected_result)

    def test_local_check(self):
        self.assertEqual(self.snapshot_manager.local_check(), True)

        self.snapshot_manager.last_status['snapshot'] = 'faultmd5'
        self.assertEqual(self.snapshot_manager.local_check(), False)

    def test_is_syncro(self):
        test_srv_timestamp = '123123'
        self.assertTrue(self.snapshot_manager.is_syncro(test_srv_timestamp))
        test_srv_timestamp = '123124'
        self.assertFalse(self.snapshot_manager.is_syncro(test_srv_timestamp))

    def test_load_status(self):
        self.snapshot_manager._load_status()
        self.assertEqual(self.snapshot_manager.last_status, self.conf_snap_gen)

    def test_file_snapMd5(self):
        #Case: file md5
        filepath = self.test_file_1
        test_md5 = hashlib.md5(open(filepath).read()).hexdigest()
        self.assertEqual(self.snapshot_manager.file_snapMd5(filepath), test_md5)

        #Case: directory
        self.assertFalse(self.snapshot_manager.file_snapMd5(self.test_folder_1))

    def test_global_md5(self):
        self.assertEqual(self.snapshot_manager.global_md5(), self.md5_snapshot)

    def test_instant_snapshot(self):
        instant_snapshot = self.snapshot_manager.instant_snapshot()
        self.assertEqual(instant_snapshot, self.true_snapshot)

    def test_save_snapshot(self):
        test_timestamp = '1234'
        self.snapshot_manager.save_snapshot(test_timestamp)

        self.assertEqual(self.snapshot_manager.last_status['timestamp'], test_timestamp)
        self.assertEqual(self.snapshot_manager.last_status['snapshot'], self.md5_snapshot)

        expected_conf = {'timestamp': test_timestamp, 'snapshot': self.md5_snapshot,}
        new_conf = json.load(open(self.conf_snap_path))

        self.assertEqual(expected_conf, new_conf)

    def test_update_snapshot_upload(self):
        original_snapshot = copy.deepcopy(self.snapshot_manager.local_full_snapshot)
        del self.snapshot_manager.local_full_snapshot['fea80f2db003d4ebc4536023814aa885']
        self.snapshot_manager.update_snapshot_upload({"src_path": self.test_file_1})
        self.assertEqual(self.snapshot_manager.local_full_snapshot, original_snapshot)

    def test_update_snapshot_update(self):
        original_snapshot = copy.deepcopy(self.snapshot_manager.local_full_snapshot)
        mock_snapshot = copy.deepcopy(original_snapshot)
        mock_file_content = "test_content"
        with open(self.test_file_1, 'rb') as f:
            original_content = f.read()

        with open(self.test_file_1, 'wb') as f:
            f.write(mock_file_content)

        mock_file_content_md5 = hashlib.md5(mock_file_content).hexdigest()

        mock_snapshot[mock_file_content_md5] = [client_daemon.get_relpath(self.test_file_1)]
        del mock_snapshot['fea80f2db003d4ebc4536023814aa885']

        #------- update a file without copies -------#
        self.snapshot_manager.update_snapshot_update({"src_path":self.test_file_1})
        self.assertEqual(self.snapshot_manager.local_full_snapshot, mock_snapshot)
        #reset original condition
        self.snapshot_manager.local_full_snapshot = copy.deepcopy(original_snapshot)

        #------- update a file with copies -------#
        mock_copy_path = client_daemon.get_relpath(self.test_file_1 + "_copy")
        self.snapshot_manager.local_full_snapshot['fea80f2db003d4ebc4536023814aa885'].append(mock_copy_path)
        mock_snapshot = copy.deepcopy(self.snapshot_manager.local_full_snapshot)
        mock_snapshot['fea80f2db003d4ebc4536023814aa885'].remove(client_daemon.get_relpath(self.test_file_1))
        mock_snapshot[mock_file_content_md5] = [client_daemon.get_relpath(self.test_file_1)]

        self.snapshot_manager.update_snapshot_update({"src_path":self.test_file_1})
        self.assertEqual(self.snapshot_manager.local_full_snapshot, mock_snapshot)
        #reset original condition
        self.snapshot_manager.local_full_snapshot = copy.deepcopy(original_snapshot)

        #------- update a file like another -------#
        self.snapshot_manager.local_full_snapshot['fea80f2db003d4ebc4536023814aa885'].append(mock_copy_path)
        self.snapshot_manager.local_full_snapshot[mock_file_content_md5] = [mock_copy_path + "_another"]
        self.snapshot_manager.update_snapshot_update({"src_path":self.test_file_1})
        mock_snapshot = {
            '81bcb26fd4acfaa5d0acc7eef1d3013a': ['sub_dir_2/test_file_2.txt'],
            'fea80f2db003d4ebc4536023814aa885': ['sub_dir_1/test_file_1.txt_copy'],
            '27565f9a57c128674736aa644012ce67': [
                'sub_dir_1/test_file_1.txt_copy_another',
                'sub_dir_1/test_file_1.txt'
                ]
        }
        self.assertEqual(self.snapshot_manager.local_full_snapshot, mock_snapshot)
        #reset original condition
        self.snapshot_manager.local_full_snapshot = original_snapshot
        with open(self.test_file_1,'w') as f:
            f.write(original_content)

    def test_update_snapshot_copy(self):
        mock_snapshot = copy.deepcopy(self.snapshot_manager.local_full_snapshot)
        original_snapshot = copy.deepcopy(mock_snapshot)
        mock_copy_path = self.test_file_1 + "_copy"
        mock_snapshot['fea80f2db003d4ebc4536023814aa885'].append(client_daemon.get_relpath(mock_copy_path))
        self.snapshot_manager.update_snapshot_copy({
            "src_path": self.test_file_1,
            "dst_path": self.test_file_1 + "_copy",
            })
        self.assertEqual(self.snapshot_manager.local_full_snapshot ,mock_snapshot)
        self.snapshot_manager.local_full_snapshot = original_snapshot

    def test_update_snapshot_move(self):
        original_snapshot = copy.deepcopy(self.snapshot_manager.local_full_snapshot)
        mock_snapshot = copy.deepcopy(original_snapshot)
        mock_new_dest = self.test_file_1 + "_new_dest"
        with open(self.test_file_1, 'rb') as f:
            file_1_content = f.read()
        with open(mock_new_dest, "wb") as f:
            f.write(file_1_content)
        mock_snapshot['fea80f2db003d4ebc4536023814aa885'][0] = client_daemon.get_relpath(mock_new_dest)
        self.snapshot_manager.update_snapshot_move({'src_path':self.test_file_1, 'dst_path' :mock_new_dest})
        self.assertEqual(self.snapshot_manager.local_full_snapshot, mock_snapshot)
        #reset origial confition
        self.snapshot_manager.local_full_snapshot = original_snapshot
        os.remove(mock_new_dest)

    def test_update_snapshot_delete(self):
        mock_snapshot = copy.deepcopy(self.snapshot_manager.local_full_snapshot)
        original_snapshot = copy.deepcopy(mock_snapshot)
        del mock_snapshot['fea80f2db003d4ebc4536023814aa885']
        self.snapshot_manager.update_snapshot_delete({'src_path':self.test_file_1})
        #delete a file without copies
        self.assertEqual(self.snapshot_manager.local_full_snapshot, mock_snapshot)

        #reset original condition
        self.snapshot_manager.local_full_snapshot = copy.deepcopy(original_snapshot)

        mock_copy_path = self.test_file_1 + "_copy"
        self.snapshot_manager.local_full_snapshot['fea80f2db003d4ebc4536023814aa885'].append(client_daemon.get_relpath(mock_copy_path))
        self.snapshot_manager.update_snapshot_delete({"src_path": mock_copy_path})
        #delete a file with copies
        self.assertEqual(self.snapshot_manager.local_full_snapshot, original_snapshot)

    def test_save_timestamp(self):
        #Case: timestamp not correct
        test_timestamp = 123122
        expected_snap = self.conf_snap_gen
        self.snapshot_manager.save_timestamp(test_timestamp)
        new_snap_conf = json.load(open(self.conf_snap_path))
        self.assertEqual(new_snap_conf, expected_snap)
        self.assertEqual(
            self.snapshot_manager.last_status,
            self.conf_snap_gen)

        #Case: timestamp correct
        test_timestamp = 123124
        expected_snap = {
            "timestamp": 123124,
            "snapshot": "ab8d6b3c332aa253bb2b471c57b73e27"
        }
        self.snapshot_manager.save_timestamp(test_timestamp)
        new_snap_conf = json.load(open(self.conf_snap_path))
        self.assertEqual(new_snap_conf, expected_snap)
        self.assertEqual(
            self.snapshot_manager.last_status,
            expected_snap)


class DirectoryEventHandlerTest(unittest.TestCase):

    def setUp(self):

        #def mock class
        class ServerCommunicator(object):
            def __init__(self):
                self.cmd = {
                    'move': False,
                    'copy': False,
                    'upload': False,
                    'delete': False
                }

            def move_file(self, src_path, dst_path):
                self.cmd['move'] = True

            def copy_file(self, copy, src_path):
                self.cmd['copy'] = True

            def upload_file(self, src_path, put_file=False):
                self.cmd['upload'] = {'path': True, 'put': put_file}

            def delete_file(self, src_path):
                self.cmd['delete'] = True

        class SnapshotManager(object):
            def __init__(self):
                self.local_full_snapshot = {'test_MD5': ['path']}

            def file_snapMd5(self, *args, **kwargs):
                return 'MD5'

        #Generate test folder tree
        self.test_src = '/test/subdir1/file'
        self.test_dst = '/test/subdir2/file'
        self.test_dir_src = '/test/subdir1/dir/'
        self.test_dir_dst = '/test/subdir2/dir/'
        self.snapshot_manager = SnapshotManager()
        self.server_comm = ServerCommunicator()

        self.event_handler = DirectoryEventHandler(
            self.server_comm,
            self.snapshot_manager)

    def test__is_copy(self):
        #Case: is file not in snapshot
        response = self.event_handler._is_copy('path')
        self.assertFalse(response)

        #Case: is file in snapshot
        self.snapshot_manager.local_full_snapshot = {'MD5': ['path']}
        response = self.event_handler._is_copy('path')
        self.assertEqual(response, 'path')

        #Case: is folder
        def file_snapMd5(self, *args, **kwargs):
                return False
        self.snapshot_manager.file_snapMd5 = file_snapMd5
        response = self.event_handler._is_copy('path')
        self.assertFalse(response)

    def test_on_moved(self):
        move_file_event = FileMovedEvent(self.test_src, self.test_dst)
        move_dir_event = DirMovedEvent(self.test_dir_src, self.test_dir_dst)

        #Case: move file event
        self.event_handler.on_moved(move_file_event)
        self.assertTrue(self.server_comm.cmd["move"])

        #reset initial condition
        self.server_comm.cmd["move"] = False

        #Case: move file event in ignored directory
        self.event_handler.paths_ignored.append(self.test_src)
        self.event_handler.paths_ignored.append(self.test_dst)
        self.event_handler.on_moved(move_file_event)
        self.assertFalse(self.server_comm.cmd["move"])
        self.assertFalse(self.test_src in self.event_handler.paths_ignored)
        self.assertFalse(self.test_dst in self.event_handler.paths_ignored)

        #Case: directory move event
        self.event_handler.on_moved(move_dir_event)
        self.assertFalse(self.server_comm.cmd["move"])

    def test_on_created(self):
        create_file_event = FileCreatedEvent(self.test_src)
        create_dir_event = DirCreatedEvent(self.test_dir_src)
        copy_file_event = FileCreatedEvent(self.test_src)

        #Case: create file event
        self.event_handler.on_created(create_file_event)
        self.assertEqual(
            self.server_comm.cmd["upload"],
            {'path': True, 'put': False})

        #reset initial condition
        self.server_comm.cmd["upload"] = False
        self.server_comm.cmd["copy"] = False

        #Case: dir create event
        self.event_handler.on_created(create_dir_event)
        self.assertFalse(self.server_comm.cmd["upload"])
        self.assertFalse(self.server_comm.cmd["copy"])

        #reset initial condition
        self.server_comm.cmd["upload"] = False
        self.server_comm.cmd["copy"] = False

        #Case: create file event for copy action
        self.snapshot_manager.local_full_snapshot = {'MD5': ['path']}
        self.event_handler.on_created(copy_file_event)
        self.assertFalse(self.server_comm.cmd["upload"])
        self.assertTrue(self.server_comm.cmd["copy"])

        #reset initial condition
        self.server_comm.cmd["upload"] = False
        self.server_comm.cmd["copy"] = False

        #Case: create file in ignored directory
        self.event_handler.paths_ignored.append(self.test_src)
        self.event_handler.on_created(create_file_event)
        self.assertFalse(self.server_comm.cmd["upload"])
        self.assertFalse(self.test_src in self.event_handler.paths_ignored)

        #reset initial condition
        self.server_comm.cmd["upload"] = False

        #Case: copy file and ignore the path
        self.snapshot_manager.local_full_snapshot = {'MD5': ['path']}
        self.event_handler.paths_ignored.append(self.test_src)
        self.event_handler.on_created(copy_file_event)
        self.assertFalse(self.server_comm.cmd["upload"])
        self.assertFalse(self.test_src in self.event_handler.paths_ignored)
        self.assertFalse(self.test_dst in self.event_handler.paths_ignored)

    def test_on_deleted(self):
        delete_file_event = FileDeletedEvent(self.test_src)
        delete_dir_event = DirDeletedEvent(self.test_dir_src)

        #Case: delete file event
        self.event_handler.on_deleted(delete_file_event)
        self.assertTrue(self.server_comm.cmd["delete"])

        #reset initial condition
        self.server_comm.cmd["delete"] = False

        #Case: delete dir event
        self.event_handler.on_deleted(delete_dir_event)
        self.assertFalse(self.server_comm.cmd["delete"])

        #Case: delete file in ignored directory
        self.event_handler.paths_ignored.append(self.test_src)
        self.event_handler.on_created(delete_file_event)
        self.assertFalse(self.server_comm.cmd["delete"])
        self.assertFalse(self.test_src in self.event_handler.paths_ignored)

    def test_on_modified(self):
        modify_file_event = FileModifiedEvent(self.test_src)
        modify_dir_event = DirModifiedEvent(self.test_dir_src)

        #Case: modify file event
        self.event_handler.on_modified(modify_file_event)
        self.assertEqual(
            self.server_comm.cmd["upload"],
            {'path': True, 'put': True})

        #reset initial condition
        self.server_comm.cmd["upload"] = False

        #Case: modify dir event
        self.event_handler.on_modified(modify_dir_event)
        self.assertFalse(self.server_comm.cmd["upload"])

        #Case: modify file in ignored directory
        self.event_handler.paths_ignored.append(self.test_src)
        self.event_handler.on_modified(modify_file_event)
        self.assertFalse(self.server_comm.cmd["upload"])
        self.assertFalse(self.test_src in self.event_handler.paths_ignored)


class CommandExecuterTest(unittest.TestCase):

    def setUp(self):
        class FileSystemOperator(object):
            def __init__(self):
                self.copy = False
                self.write = False
                self.delete = False

            def copy_a_file(self, origin_path, dst_path):
                self.copy = [origin_path, dst_path]

            def write_a_file(self, path):
                self.write = path

            def delete_a_file(self, dst_path):
                self.delete = dst_path

        class ServerCommunicator(object):
            def __init__(self):
                self.upload = False
                self.delete = False

            def upload_file(self, dst_path):
                self.upload = dst_path

            def delete_file(self, dst_path):
                self.delete = dst_path

        self.file_system_op = FileSystemOperator()
        self.server_comm = ServerCommunicator()
        self.executer = CommandExecuter(
            self.file_system_op,
            self.server_comm)

    def test_syncronize_executer(self):
        #Case: remote and local command error

        error_command_list = [
            {'local_errorcommand': 'sub_dir_2/test_file_3.txt'},
            {'remote_errorcommand': 'sub_dir_1/test_file_1.txt'},
        ]

        self.executer.syncronize_executer(error_command_list)

        self.assertFalse(self.file_system_op.copy)
        self.assertFalse(self.file_system_op.write)
        self.assertFalse(self.file_system_op.delete)
        self.assertFalse(self.server_comm.upload)
        self.assertFalse(self.server_comm.delete)

        #Case: remote and local command

        command_list = [
            {'local_download': ['download/test/path']},
            {'local_copy': [
                'src/copy/test/path',
                'src/copy/test/path']},
            {'local_delete': ['delete/test/path']},
            {'remote_delete': ['delete/test/path']},
            {'remote_upload': ['upload/test/path']},
        ]

        self.executer.syncronize_executer(command_list)

        self.assertEqual(
            self.file_system_op.copy,
            ['src/copy/test/path', 'src/copy/test/path'])
        self.assertEqual(
            self.file_system_op.write,
            'download/test/path')
        self.assertEqual(
            self.file_system_op.delete,
            'delete/test/path')
        self.assertEqual(
            self.server_comm.upload,
            'upload/test/path')
        self.assertEqual(
            self.server_comm.delete,
            'delete/test/path')


class FunctionTest(unittest.TestCase):

    def setUp(self):
        client_daemon.CONFIG_DIR_PATH = '/home/user/test_shared_dir'

    def test_get_abspath(self):
        expected_result = '/home/user/test_shared_dir/folder/file.txt'

        #Case: relative path
        path = 'folder/file.txt'
        self.assertEqual(get_abspath(path), expected_result)

        #Case: absolute path
        path = '/home/user/test_shared_dir/folder/file.txt'
        self.assertEqual(get_abspath(path), expected_result)

    def test_get_relpath(self):
        expected_result = 'folder/file.txt'

        #Case: absolute path
        path = '/home/user/test_shared_dir/folder/file.txt'
        self.assertEqual(get_relpath(path), expected_result)

        #Case: relarive path
        path = 'folder/file.txt'
        self.assertEqual(get_relpath(path), expected_result)

    def test_load_config(self):
        expected_conf = {
            'config': 'test configuration'
        }
        open('config.json', 'w').write(json.dumps(expected_conf))

        #Case: test config file
        config, is_new = load_config()
        self.assertFalse(is_new)
        self.assertEqual(config, expected_conf)

        #reset
        os.remove('config.json')

        #Case: IOError
        expected_conf = {
            "server_url": "http://{}:{}/{}".format(
                client_daemon.SERVER_URL,
                client_daemon.SERVER_PORT,
                client_daemon.API_PREFIX
            ),
            "dir_path": os.path.join(os.path.expanduser("~"), "RawBox"),
            "snapshot_file_path": 'snapshot_file.json',
            "cmd_host": "localhost",
            "cmd_port": "6666",
            "username": 'username',
            "password": 'password',
        }
        expected_snap = {
            "timestamp": 0,
            "snapshot": "",
        }
        config, is_new = load_config()
        self.assertTrue(is_new)
        self.assertTrue(os.path.exists('config.json'))
        self.assertEqual(config, expected_conf)
        self.assertTrue(os.path.exists('snapshot_file.json'))
        snap = json.loads(open('snapshot_file.json').read())
        self.assertEqual(snap, expected_snap)


if __name__ == '__main__':
    unittest.main()
