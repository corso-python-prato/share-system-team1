from client_daemon import DirSnapshotManager
from client_daemon import DirectoryEventHandler
from client_daemon import ServerCommunicator
from watchdog.observers.polling import PollingObserver as Observer
import httpretty
import unittest
import requests
import hashlib
import base64
import shutil
import json
import sys
import os
import time


class ServerCommunicatorTest(unittest.TestCase):

    def setUp(self):
        class DirSnapshotManager(object):

            def syncronize_dispatcher(self, server_timestamp, server_snapshot):
                self.server_timestamp = server_timestamp
                self.server_snapshot = server_snapshot
                return ['command']

            def syncronize_executer(self, command_list):
                self.command_list = command_list


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
            'http://127.0.0.1:5000/API/v1/create_user')
        httpretty.register_uri(httpretty.GET,
            'http://127.0.0.1:5000/API/v1/files',
            body=str({
        '9406539a103956dc36cb7ad35547198c': [{"path": u'/Users/marc0/progetto/prove_deamon\\bla.txt',"timestamp":123123}],
        'a8f5f167f44f4964e6c998dee827110c': [{"path": u'vecchio.txt',"timestamp":123122}], 
        'c21e1af364fa17cc80e0bbec2dd2ce5c': [{"path": u'/Users/marc0/progetto/prove_deamon\\asdas\\asdasd.txt',"timestamp":123123}], 
        'd41d8cd98f00b204e9800998ecf8427e': [{"path": u'/Users/marc0/progetto/prove_deamon\\dsa.txt',"timestamp":123122},#old timestamp 
                                            {"path":  u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (2).txt',"timestamp":123123}, 
                                            {"path":  u'server path in piu copiata',"timestamp":123123}],
        'a8f5f167f44f4964e6c998dee827110b':[{"path":  u'nuova path server con md5 nuovo',"timestamp":123123}],
        'a8f5f167f44f4964e6c998eee827110b':[{"path":  u'nuova path server con md5 nuovo e timestamp minore',"timestamp":123122}]}),
            content_type="application/json"
        )

        self.dir = "/tmp/home/test_rawbox/folder"
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
            self.dir,
            snapshot_manager)
        
    def tearDown(self):
        httpretty.disable()
        httpretty.reset()
    
    def test_upload(self, put_file=True):
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
        if put_file:
            self.assertEqual(method, 'PUT')
        else:
            self.assertEqual(method, 'POST')

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
                def json(self):
                    return self.text
            return obj()

        self.server_comm._try_request = my_try_request
        self.server_comm.synchronize("mock")


class DirSnapshotManagerTest(unittest.TestCase):
    def setUp(self):
        #Generate test folder tree and configuration file
        self.test_main_path = os.path.join(os.path.expanduser('~'), 'test_path')
        os.makedirs(self.test_main_path)
        self.test_share_dir = os.path.join(self.test_main_path, 'shared_dir')
        os.makedirs(self.test_share_dir)
        self.conf_snap_path = os.path.join(self.test_main_path, 'snapshot_file.json')
        self.conf_snap_gen = {"timestamp": 123123, "snapshot": "ab8d6b3c332aa253bb2b471c57b73e27"}

        open(self.conf_snap_path, 'w').write(json.dumps(self.conf_snap_gen))

        os.makedirs(os.path.join(self.test_share_dir, 'sub_dir_1'))
        os.makedirs(os.path.join(self.test_share_dir, 'sub_dir_2'))
        open(os.path.join(self.test_share_dir, 'sub_dir_1', 'test_file_1.txt'), 'w').write('Lorem ipsum dolor sit amet')
        open(os.path.join(self.test_share_dir, 'sub_dir_2', 'test_file_2.txt'), 'w').write('Integer non tincidunt dolor')

        self.true_snapshot= {
            '81bcb26fd4acfaa5d0acc7eef1d3013a': ['sub_dir_2/test_file_2.txt'],
            'fea80f2db003d4ebc4536023814aa885': ['sub_dir_1/test_file_1.txt'],
        }
        self.md5_snapshot = 'ab8d6b3c332aa253bb2b471c57b73e27'

        self.snapshot_manager = DirSnapshotManager(self.test_share_dir, self.conf_snap_path)


    def tearDown(self):
        shutil.rmtree(self.test_main_path)

    def test_local_check(self):
        self.assertEqual(self.snapshot_manager.local_check(), True)

        self.snapshot_manager.last_status['snapshot'] = 'faultmd5'
        self.assertEqual(self.snapshot_manager.local_check(), False)

    def server_check(self):
        server_timestamp = 123123
        self.assertEqual(self.snapshot_manager.server_check(server_timestamp), True)

        server_timestamp = 1
        self.assertEqual(self.snapshot_manager.server_check(server_timestamp), False)

    def test_load_status(self):
        self.snapshot_manager._load_status()
        self.assertEqual(self.snapshot_manager.last_status, self.conf_snap_gen)

    def test_file_snapMd5(self):

        filepath = os.path.join(self.test_share_dir, 'sub_dir_1', 'test_file_1.txt')
        test_md5 = hashlib.md5(open(filepath).read()).hexdigest()
        self.assertEqual(self.snapshot_manager.file_snapMd5(filepath), test_md5)

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

class DirectoryEventHandlerTest(unittest.TestCase):

    def setUp(self):

        #def mock class
        class ServerCommunicator(object):
            def __init__(self, var):
                self.cmd = var

            def move_file(self, src_path):
                self.cmd['move'] = True

            def copy_file(self, copy, src_path):
                self.cmd['copy'] = True

            def upload_file(self, src_path, put_file = False):
                self.cmd['upload'] = {'path': True, 'put': put_file}


            def delete_file(self, src_path):
                self.cmd['delete'] = True

        class SnapshotManager(object):
            def __init__(self):
                self.local_full_snapshot = {'test_MD5': ['path']}

            def file_snapMd5(self, *args, **kwargs):
                return 'MD5'


        #Generate test folder tree
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

        srvcomm_return_var = {'move': False, 'copy': False, 'upload': False, 'delete': False}

        self.snapshot_manager = SnapshotManager()
        self.server_comm = ServerCommunicator(srvcomm_return_var)

        self.event_handler = DirectoryEventHandler(self.server_comm, self.snapshot_manager)
        self.observer = Observer(timeout=0.1)
        self.observer.schedule(self.event_handler, self.test_share_dir, recursive=True)
        self.observer.start()

    def tearDown(self):
        self.observer.stop()
        self.observer.join()
        shutil.rmtree(self.test_main_path)

    def test__is_copy(self):
        response = self.event_handler._is_copy('path')

        self.assertEqual(response, False)

        self.snapshot_manager.local_full_snapshot = {'MD5': ['path']}
        response = self.event_handler._is_copy('path')

        self.assertEqual(response, 'path')

    def test_on_moved(self):
        shutil.move(self.test_file_1, self.test_folder_2)
        time.sleep(0.5)

        self.observer.stop()
        self.observer.join()
        self.assertEqual(self.server_comm.cmd["move"], True)
        self.assertEqual(self.server_comm.cmd["copy"], False)
        self.assertEqual(self.server_comm.cmd["upload"], False)
        self.assertEqual(self.server_comm.cmd["delete"], False)

    def test_on_created_create(self):
        open(os.path.join(self.test_folder_1, 'test_file_3'), 'w').write('Vivamus eget lobortis massa')
        time.sleep(0.5)

        self.observer.stop()
        self.observer.join()
        self.assertEqual(self.server_comm.cmd["move"], False)
        self.assertEqual(self.server_comm.cmd["copy"], False)
        self.assertEqual(self.server_comm.cmd["upload"], {'path': True, 'put': False})
        self.assertEqual(self.server_comm.cmd["delete"], False)

    def test_on_created_copy(self):
        self.snapshot_manager.local_full_snapshot = {'MD5': ['path']}
        shutil.copy(self.test_file_1, self.test_folder_2)
        time.sleep(0.5)

        self.observer.stop()
        self.observer.join()
        self.assertEqual(self.server_comm.cmd["move"], False)
        self.assertEqual(self.server_comm.cmd["copy"], True)
        self.assertEqual(self.server_comm.cmd["upload"], False)
        self.assertEqual(self.server_comm.cmd["delete"], False)

    def test_on_deleted(self):
        os.remove(self.test_file_1)
        time.sleep(0.5)

        self.observer.stop()
        self.observer.join()
        self.assertEqual(self.server_comm.cmd["move"], False)
        self.assertEqual(self.server_comm.cmd["copy"], False)
        self.assertEqual(self.server_comm.cmd["upload"], False)
        self.assertEqual(self.server_comm.cmd["delete"], True)

    def test_on_modified(self):
        open(os.path.join(self.test_file_1), 'w').write('Vivamus eget lobortis massa')
        time.sleep(3)

        self.observer.stop()
        self.observer.join()
        self.assertEqual(self.server_comm.cmd["move"], False)
        self.assertEqual(self.server_comm.cmd["copy"], False)
        self.assertEqual(self.server_comm.cmd["upload"], {'path': True, 'put': True})
        self.assertEqual(self.server_comm.cmd["delete"], False)

if __name__ == '__main__':
    unittest.main()
