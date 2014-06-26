from client_daemon import DirectoryEventHandler
from watchdog.observers.polling import PollingObserver as Observer
import client_daemon
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


class ClientDaemonTest(unittest.TestCase):
    def setUp(self):
        httpretty.enable()
        httpretty.register_uri(
            httpretty.POST,
            'http://127.0.0.1:5000/API/v1/files/bla.txt',
            data={"response": "ok"})

    def tearDown(self):
        httpretty.disable()
        httpretty.reset()
    
    def test_upload(self, put_file=False):
        password = "passwordSegretissima"
        username = "usernameFarlocco"
        
        file_path = '/Users/marc0/progetto/prove_deamon/bla.txt'
        mock_file_content = open(file_path, 'r')

        mock_auth_user = ":".join([username, password])
        mock_data = 'asdasd'
        client_daemon.ServerCommunicator(
            'http://127.0.0.1:5000/API/v1',
            username,
            password,
            "/Users/marc0/progetto/prove_deamon").upload_file(file_path, put_file)
        encoded = httpretty.last_request().headers['authorization'].split()[1]
        authorization_decoded = base64.decodestring(encoded)
        #data = httpretty.last_request().parsed_body
        path = httpretty.last_request().path
        host = httpretty.last_request().headers['host']
        method = httpretty.last_request().method
        
        #check if authorization is equals
        self.assertEqual(authorization_decoded, mock_auth_user)
        #check if data is equals
        #self.assertEqual(data, mock_data)
        #check if url and method is equals

        self.assertEqual(path, '/API/v1/files/bla.txt')
        self.assertEqual(host, '127.0.0.1:5000')
        if put_file:
            self.assertEqual(method, 'PUT')
        else:
            self.assertEqual(method, 'POST')

    def init_snapshot(self):
        config = client_daemon.load_config()
        return client_daemon.DirSnapshotManager(config['dir_path'], config['snapshot_file_path'])
        
    def test_syncronize_dispatcher(self):
        snapshot_manager = self.init_snapshot()

        mock_snapshot_1 = {
            '12345a': [u'/Users/marc0/progetto/prove_deamon\\bla.txt'],
            '12345b': [u'/Users/marc0/progetto/prove_deamon\\asdas\\gbla.txt'],
            '12345c': [u'/Users/marc0/progetto/prove_deamon\\asdas\\asdasd.txt'],
            '12345d': [u'/Users/marc0/progetto/prove_deamon\\dsa.txt',
                u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (2).txt',
                u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (3).txt',
                u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (4).txt'],
            '12345e': [u'farlocco_2'],
        }
        
        mock_snapshot_2 = {
            '12345a': [u'/Users/marc0/progetto/prove_deamon\\bla.txt'],
            '12345b': [u'/Users/marc0/progetto/prove_deamon\\asdas\\gbla.txt'],
            '12345c': [u'/Users/marc0/progetto/prove_deamon\\asdas\\asdasd.txt'],
            '12345d': [u'/Users/marc0/progetto/prove_deamon\\dsa.txt',
                u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (2).txt',
                u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (3).txt',
                u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (4).txt'],
            '12345e': [u'farlocco_2'],
        }

        mock_snap_local = mock_snapshot_1
        mock_snap_server = mock_snapshot_1


        print "\n{:*^60}\n".format("\nno deamon internal conflicts == timestamp\n")
        snapshot_manager.syncronize_dispatcher(
            server_timestamp=123123,
            server_snapshot=mock_snap_server)

        print "\n{:*^60}\n".format("\nno deamon internal conflicts != timestamp\n")
        snapshot_manager.syncronize_dispatcher(
            server_timestamp=123124,
            server_snapshot=mock_snap_server)
        
        snapshot_manager.last_status['snapshot'] = "21451512512512512"

        print "\n{:*^60}\n".format("\ndeamon internal conflicts == timestamp\n")
        snapshot_manager.syncronize_dispatcher(
            server_timestamp=123123,
            server_snapshot=mock_snap_server)

        print "\n{:*^60}\n".format("\nno deamon internal conflicts != timestamp\n")
        snapshot_manager.syncronize_dispatcher(
            server_timestamp=123124,
            server_snapshot=mock_snap_server)

    def diff_snapshot_paths(self):
        snapshot_manager = self.init_snapshot()
        #mock_equal = """[u'/Users/marc0/progetto/prove_deamon/asdas/asdasd.txt', u'/Users/marc0/progetto/prove_deamon/asdas/Nuovo documento di testo.txt', u'/Users/marc0/progetto/prove_deamon/dsa.txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documento di testo (4).txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documentodi testo (3).txt', u'/Users/marc0/progetto/prove_deamon/bla.txt', u'/Users/marc0/progetto/prove_deamon/asdas/sdadsda.txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documento di testo (5).txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documento di testo.txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documento di testo (2).txt']"""
        #mock_new_client = """[u'/Users/marc0/progetto/prove_deamon/asdas/bla.txt', u'/Users/marc0/progetto/prove_deamon/asd/gbla.txt', u'/Users/marc0/progetto/prove_deamon/asdas/gbla.txt']"""
        #mock_new_server= """['path_farlocca']"""

        snap_client = snapshot_manager.local_full_snapshot
        snap_server = {
                    '9406539a103956dc36cb7ad35547198c': [u'/Users/marc0/progetto/prove_deamon\\bla.txt'],
                    'a8f5f167f44f4964e6c998dee827110c': [
                                                    u'/Users/marc0/progetto/prove_deamon\\asd\\gbla.txt',
                                                    u'/Users/marc0/progetto/prove_deamon\\asdas\\bla.txt',
                                                    u'/Users/marc0/progetto/prove_deamon\\asdas\\gbla.txt'],
                    'c21e1af364fa17cc80e0bbec2dd2ce5c': [u'/Users/marc0/progetto/prove_deamon\\asdas\\asdasd.txt'],
                    'd41d8cd98f00b204e9800998ecf8427e': [
                                                    u'/Users/marc0/progetto/prove_deamon\\dsa.txt',
                                                    u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (2).txt',
                                                    u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (3).txt',
                                                    u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (4).txt',
                                                    u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (5).txt',
                                                    u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo.txt',
                                                    u'/Users/marc0/progetto/prove_deamon\\asdas\\Nuovo documento di testo.txt',
                                                    u'/Users/marc0/progetto/prove_deamon\\asdas\\sdadsda.txt',
                                                    u'path_farlocca']
                }
        new_client, new_server, equal = snapshot_manager.diff_snapshot_paths(snap_client, snap_server)
        
        #new_client = str(new_client).replace('\\\\','/')
        #new_server = str(new_server).replace('\\\\','/')
        #equal = str(equal).replace('\\\\','/')
from client_daemon import DirSnapshotManager

class DirSnapshotManagerTest(unittest.TestCase):
    def setUp(self):
        #Generate test folder tree and configuration file
        self.test_main_path = os.path.join(os.path.expanduser('~'), 'test_path')
        os.makedirs(self.test_main_path)
        self.test_share_dir = os.path.join(self.test_main_path, 'shared_dir')
        os.makedirs(self.test_share_dir)
        self.conf_snap_path = os.path.join(self.test_main_path, 'snapshot_file.json')
        self.conf_snap_gen = {"timestamp": 123123, "snapshot": "669aa28a0c11a4969de101c7dae9cc52"}

        open(self.conf_snap_path, 'w').write(json.dumps(self.conf_snap_gen))

        os.makedirs(os.path.join(self.test_share_dir, 'sub_dir_1'))
        os.makedirs(os.path.join(self.test_share_dir, 'sub_dir_2'))
        open(os.path.join(self.test_share_dir, 'sub_dir_1', 'test_file_1.txt'), 'w').write('Lorem ipsum dolor sit amet')
        open(os.path.join(self.test_share_dir, 'sub_dir_2', 'test_file_2.txt'), 'w').write('Integer non tincidunt dolor')

        self.true_snapshot= {
            'fea80f2db003d4ebc4536023814aa885': ['sub_dir_1/test_file_1.txt'],
            '81bcb26fd4acfaa5d0acc7eef1d3013a': ['sub_dir_2/test_file_2.txt'],
        }
        self.md5_snapshot = '669aa28a0c11a4969de101c7dae9cc52'

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
        test_md5 = hashlib.md5(str(self.snapshot_manager.local_full_snapshot)).hexdigest()
        self.assertEqual(self.snapshot_manager.global_md5(), test_md5)

    def test_instant_snapshot(self):
        instant_snapshot = self.snapshot_manager.instant_snapshot()

        print instant_snapshot

        self.assertEqual(instant_snapshot, self.true_snapshot)

    def test_save_snapshot(self):
        test_timestamp = '1234'
        self.snapshot_manager.save_snapshot(test_timestamp)

        self.assertEqual(self.snapshot_manager.last_status['timestamp'], test_timestamp)
        self.assertEqual(self.snapshot_manager.last_status['snapshot'], self.md5_snapshot)

        new_conf = json.load(open(self.conf_snap_path))

        self. assertEqual({'timestamp': test_timestamp, 'snapshot': self.md5_snapshot,}, new_conf)

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
        time.sleep(0.5)

        self.observer.stop()
        self.observer.join()
        self.assertEqual(self.server_comm.cmd["move"], False)
        self.assertEqual(self.server_comm.cmd["copy"], False)
        self.assertEqual(self.server_comm.cmd["upload"], {'path': True, 'put': True})
        self.assertEqual(self.server_comm.cmd["delete"], True)

if __name__ == '__main__':
    unittest.main()
