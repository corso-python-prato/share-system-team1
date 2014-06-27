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
<<<<<<< HEAD
            'http://127.0.0.1:5000/API/v1/create_user')
=======
            'http://127.0.0.1:5000/API/v1/create_user',
            status=201)
>>>>>>> cd1a2b50ecb77df903b358206961fabb0c3b7a81
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

<<<<<<< HEAD
=======
        def my_global_md5():
            return "52a0b3003d798aaec3be2e85dcf6d024"

        snapshot_manager = self.init_snapshot()
        snapshot_manager.global_md5 = my_global_md5
        snapshot_manager.last_status = {"timestamp": 123123, "snapshot": "52a0b3003d798aaec3be2e85dcf6d024"}
        snapshot_manager.local_full_snapshot = {
                '9406539b203956dc36cb7ad35547198c': [u'/Users/marc0/progetto/prove_deamon\\bla.txt'],#new md5
                'a8f5f167f44f4964e6c998dee827110c': [u'vecchio.txt'], 
                'c21e1af364fa17cc80e0bbec2dd2ce5c': [u'/Users/marc0/progetto/prove_deamon\\asdas\\asdasd.txt'], 
                'd41d8cd98f00b204e9899998ecf89999': [u'/Users/marc0/progetto/prove_deamon\\dsa.txt',#new md5 
                                                     u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (2).txt'],
                'abcdefghilmnopqrstuvwyzabcdefghi': [u'new path client']}
        
        mock_snap_server = {
                '9406539a103956dc36cb7ad35547198c': [{"path": u'/Users/marc0/progetto/prove_deamon\\bla.txt',"timestamp":123123}],
                'a8f5f167f44f4964e6c998dee827110c': [{"path": u'vecchio.txt',"timestamp":123122}], 
                'c21e1af364fa17cc80e0bbec2dd2ce5c': [{"path": u'/Users/marc0/progetto/prove_deamon\\asdas\\asdasd.txt',"timestamp":123123}], 
                'd41d8cd98f00b204e9800998ecf8427e': [{"path": u'/Users/marc0/progetto/prove_deamon\\dsa.txt',"timestamp":123122},#old timestamp 
                                                    {"path":  u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (2).txt',"timestamp":123123}, 
                                                    {"path":  u'server path in piu copiata',"timestamp":123123}],
                'a8f5f167f44f4964e6c998dee827110b':[{"path":  u'nuova path server con md5 nuovo',"timestamp":123123}],
                'a8f5f167f44f4964e6c998eee827110b':[{"path":  u'nuova path server con md5 nuovo e timestamp minore',"timestamp":123122}]}
        
        print "\n{:*^60}\n".format("\nno deamon internal conflicts == timestamp\n")
        print snapshot_manager.syncronize_dispatcher(
            server_timestamp = 123123,
            server_snapshot = mock_snap_server)

        print "\n{:*^60}\n".format("\nno deamon internal conflicts != timestamp\n")
        print snapshot_manager.syncronize_dispatcher(
            server_timestamp = 123124,
            server_snapshot = mock_snap_server)
        
        snapshot_manager.last_status['snapshot'] = "21451512512512512"

        print "\n{:*^60}\n".format("\ndeamon internal conflicts == timestamp\n")
        print snapshot_manager.syncronize_dispatcher(
            server_timestamp = 123123,
            server_snapshot = mock_snap_server)

        print "\n{:*^60}\n".format("\nno deamon internal conflicts != timestamp\n")
        print snapshot_manager.syncronize_dispatcher(
            server_timestamp = 123124,
            server_snapshot = mock_snap_server)

    def diff_snapshot_paths(self):
        snapshot_manager = self.init_snapshot()
        #mock_equal = [u'/Users/marc0/progetto/prove_deamon/asdas/asdasd.txt', u'/Users/marc0/progetto/prove_deamon/asdas/Nuovo documento di testo.txt', u'/Users/marc0/progetto/prove_deamon/dsa.txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documento di testo (4).txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documentodi testo (3).txt', u'/Users/marc0/progetto/prove_deamon/bla.txt', u'/Users/marc0/progetto/prove_deamon/asdas/sdadsda.txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documento di testo (5).txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documento di testo.txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documento di testo (2).txt']
        #mock_new_client = [u'/Users/marc0/progetto/prove_deamon/asdas/bla.txt', u'/Users/marc0/progetto/prove_deamon/asd/gbla.txt', u'/Users/marc0/progetto/prove_deamon/asdas/gbla.txt']
        #mock_new_server= ['path_farlocca']

        snap_client = snapshot_manager.local_full_snapshot
        snap_server = {
                    '9406539a103956dc36cb7ad35547198c': [u'/Users/marc0/progetto/prove_deamon\\bla.txt'],
                    'a8f5f167f44f4964e6c998dee827110c': [u'/Users/marc0/progetto/prove_deamon\\asd\\gbla.txt',
                                                        u'/Users/marc0/progetto/prove_deamon\\asdas\\bla.txt',
                                                        u'/Users/marc0/progetto/prove_deamon\\asdas\\gbla.txt'],
                    'c21e1af364fa17cc80e0bbec2dd2ce5c': [u'/Users/marc0/progetto/prove_deamon\\asdas\\asdasd.txt'],
                    'd41d8cd98f00b204e9800998ecf8427e': [u'/Users/marc0/progetto/prove_deamon\\dsa.txt',
                                                        u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (2).txt',
                                                        u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (3).txt',
                                                        u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (4).txt',
                                                        u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (5).txt',
                                                        u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo.txt',
                                                        u'/Users/marc0/progetto/prove_deamon\\asdas\\Nuovo documento di testo.txt',
                                                        u'/Users/marc0/progetto/prove_deamon\\asdas\\sdadsda.txt', 
                                                        u'path_farlocca']}
        new_client, new_server, equal = snapshot_manager.diff_snapshot_paths(snap_client, snap_server)

        
         #new_client = str(new_client).replace('\\\\','/')
         #new_server = str(new_server).replace('\\\\','/')
         #equal = str(equal).replace('\\\\','/')

         #self.assertEqual(str(new_client), mock_new_client)
         #self.assertEqual(str(equal), mock_equal)
         #self.assertEqual(str(new_server), mock_new_server)

class FileSystemOperatorTest(unittest.TestCase):

    def setUp(self):
        self.client_path = '/tmp/user_dir'
        self.filename = 'test_file.txt'
        if not os.path.exists(self.client_path):
            os.makedirs(self.client_path)
        httpretty.enable()
        httpretty.register_uri(httpretty.GET, 'http://localhost/api/v1/files/{}'.format(self.filename),
            body='this is a test',
            content_type='text/plain')
        self.snapshot_manager = client_daemon.DirSnapshotManager(self.client_path, 
            snapshot_file_path='snapshot_file.json')
        self.server_com = client_daemon.ServerCommunicator(
            server_url='http://localhost/api/v1',
            username='usernameFarlocco',
            password='passwordSegretissima',
            dir_path=self.client_path)
        self.event_handler = client_daemon.DirectoryEventHandler(self.server_com, 
            self.snapshot_manager)
        self.file_system_op = client_daemon.FileSystemOperator(self.event_handler, 
            self.server_com)

    def tearDown(self):
        httpretty.disable()

    def test_write_a_file(self):
        self.file_system_op.write_a_file('{}/{}'.format(self.client_path, self.filename))
        written_file = open('{}/{}'.format(self.client_path,self.filename), 'rb').read()
        self.assertEqual('this is a test', written_file)

    def test_move_a_file(self):
        f_name = 'file_to_move.txt'
        file_to_move = open('{}/{}'.format(self.client_path, f_name), 'w')
        file_to_move.write('this is a test')
        source_path = file_to_move.name
        dest_path = '{}/dir1/{}'.format(self.client_path, f_name)
        file_to_move.close()
        self.file_system_op.move_a_file(source_path, dest_path)
        written_file = open(dest_path, 'rb').read()
        self.assertEqual('this is a test', written_file)

    def test_copy_a_file(self):
        f_name = 'file_to_copy.txt'
        file_to_copy = open('{}/{}'.format(self.client_path, f_name), 'w')
        file_to_copy.write('this is a test')
        source_path = file_to_copy.name
        dest_path = '{}/copy_dir/{}'.format(self.client_path, f_name)
        file_to_copy.close()
        self.file_system_op.copy_a_file(source_path, dest_path)
        copied_file = open(dest_path, 'rb').read()
        self.assertEqual('this is a test', copied_file)

    def test_delete_a_file(self):
        del_dir = 'to_delete'
        path_to_del = '{}/to_delete'.format(self.client_path)
        if not os.path.exists(path_to_del):
            os.makedirs('{}/{}'.format(self.client_path, del_dir))
        f_name = 'file_to_delete.txt'
        file_to_delete = open('{}/{}/{}'.format(self.client_path, del_dir, f_name), 'w')
        file_to_delete.write('delete me')
        file_to_delete.close()
        self.assertTrue(os.path.exists(file_to_delete.name))
        self.file_system_op.delete_a_file(file_to_delete.name)
        self.assertFalse(os.path.exists(file_to_delete.name))
        self.file_system_op.delete_a_file(path_to_del)
        self.assertFalse(os.path.exists(path_to_del))


>>>>>>> cd1a2b50ecb77df903b358206961fabb0c3b7a81

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
            '81bcb26fd4acfaa5d0acc7eef1d3013a': [{'path': u'sub_dir_2/test_file_2.txt', 'timestamp': 123123}],
            'fea80f2db003d4ebc4536023814aa885': [{'path': u'sub_dir_1/test_file_1.txt', 'timestamp': 123123}],
        }
        #server snapshot unsinket with local path:
        #   sub_dir_1/test_file_1.txt modified
        #   sub_dir_2/test_file_1.txt added
        unsinked_server_snap = {
            '81bcb26fd4acfaa5d0acc7eef1d3013a': [{'path': u'sub_dir_2/test_file_2.txt', 'timestamp': 123123}],
            'fea80f2db004d4ebc4536023814aa885': [{'path': u'sub_dir_1/test_file_1.txt', 'timestamp': 123124}],
            '456jk3b334bb33463463fbhj4b3534t3': [{'path': u'sub_dir_2/test_file_3.txt', 'timestamp': 123125}],
        }

        sinked_timestamp = 123123
        unsinked_timestamp = 123125

        #Case: no deamon internal conflicts == timestamp
        expected_result = []
        result = self.snapshot_manager.syncronize_dispatcher(
            server_timestamp = sinked_timestamp,
            server_snapshot = sinked_server_snap)
        self.assertEqual(result, expected_result)

        #Case: no deamon internal conflicts != timestamp
        expected_result = [
            {'sub_dir_2/test_file_3.txt': 'remote_download'},
            {'sub_dir_1/test_file_1.txt': 'remote_download'},
        ]
        result = self.snapshot_manager.syncronize_dispatcher(
            server_timestamp = unsinked_timestamp,
            server_snapshot = unsinked_server_snap)
        self.assertEqual(result, expected_result)

        #Case: deamon internal conflicts == timestamp
        self.snapshot_manager.last_status['snapshot'] = "21451512512512512"
        expected_result = []
        result = self.snapshot_manager.syncronize_dispatcher(
            server_timestamp = sinked_timestamp,
            server_snapshot = sinked_server_snap)
        self.assertEqual(result, expected_result)

        #Case: no deamon internal conflicts != timestamp
        expected_result = [
            {'sub_dir_2/test_file_3.txt': 'remote_download'},
            {'sub_dir_1/test_file_1.txt.conflicted': 'remote_upload'},
            {'sub_dir_1/test_file_1.txt': 'local_copy_and_rename:sub_dir_1/test_file_1.txt.conflicted'},
        ]
        result = self.snapshot_manager.syncronize_dispatcher(
            server_timestamp = unsinked_timestamp,
            server_snapshot = unsinked_server_snap)
        self.assertEqual(result, expected_result)

    def test_local_check(self):
        self.assertEqual(self.snapshot_manager.local_check(), True)

        self.snapshot_manager.last_status['snapshot'] = 'faultmd5'
        self.assertEqual(self.snapshot_manager.local_check(), False)

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

            def move_file(self, src_path, dst_path):
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
        time.sleep(0.5)
        open(os.path.join(self.test_file_1), 'w').write('Vivamus eget lobortis massa')
        time.sleep(0.5)

        self.observer.stop()
        self.observer.join()
        self.assertEqual(self.server_comm.cmd["move"], False)
        self.assertEqual(self.server_comm.cmd["copy"], False)
        self.assertEqual(self.server_comm.cmd["upload"], {'path': True, 'put': True})
        self.assertEqual(self.server_comm.cmd["delete"], False)


if __name__ == '__main__':
    unittest.main()
