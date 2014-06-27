import client_daemon
import httpretty
import unittest
import requests
import base64
import json
import sys
import os


class ClientDaemonTest(unittest.TestCase):

    def setUp(self):
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
        httpretty.register_uri(
            httpretty.GET,
            'http://127.0.0.1:5000/API/v1/files/',
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
        
    def tearDown(self):
        httpretty.disable()
        httpretty.reset()
    
    def test_upload(self, put_file=True):
        mock_auth_user = ":".join([self.username, self.password])
        client_daemon.ServerCommunicator(
            'http://127.0.0.1:5000/API/v1',
            self.username,
            self.password,
            self.dir).upload_file(self.file_path, put_file)
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
        response = client_daemon.ServerCommunicator(
                        'http://127.0.0.1:5000/API/v1',
                        self.username,
                        self.password,
                        self.dir).download_file(self.file_path)
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
        client_daemon.ServerCommunicator(
                    'http://127.0.0.1:5000/API/v1',
                    self.username,
                    self.password,
                    self.dir).delete_file(self.file_path)
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
        client_daemon.ServerCommunicator(
                    'http://127.0.0.1:5000/API/v1',
                    self.username,
                    self.password,
                    self.dir).move_file(self.file_path, self.another_path)
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
        client_daemon.ServerCommunicator(
                    'http://127.0.0.1:5000/API/v1',
                    self.username,
                    self.password,
                    self.dir).copy_file(self.file_path, self.another_path)
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
        client_daemon.ServerCommunicator(
                    'http://127.0.0.1:5000/API/v1',
                    self.username,
                    self.password,
                    self.dir).create_user(test_username, test_password)
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

    def init_snapshot(self):
        config = client_daemon.load_config()
        return client_daemon.DirSnapshotManager(config['dir_path'], config['snapshot_file_path'])
    
    def test_syncronize(self):
        client_daemon.ServerCommunicator(
            'http://127.0.0.1:5000/API/v1', 
            'username', 
            'password',
            "/home/user/prove").synchronize("mock",self.init_snapshot())

    def test_syncronize_dispatcher(self):

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

if __name__ == '__main__':
    unittest.main()
