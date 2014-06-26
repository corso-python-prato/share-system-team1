import client_daemon
import httpretty
import unittest
import requests
import base64
import json
import sys
import os


# class ClientDaemonTest(unittest.TestCase):
#     def setUp(self):
#         httpretty.enable()
#         httpretty.register_uri(
#             httpretty.POST,
#             'http://127.0.0.1:5000/API/v1/files/bla.txt',
#             data={"response": "ok"})

#     def tearDown(self):
#         httpretty.disable()
#         httpretty.reset()
    
#     def test_upload(self, put_file=False):
#         password = "passwordSegretissima"
#         username = "usernameFarlocco"
        
#         file_path = '/Users/marc0/progetto/prove_deamon/bla.txt'
#         mock_file_content = open(file_path, 'r')

#         mock_auth_user = ":".join([username, password])
#         mock_data = 'asdasd'
#         client_daemon.ServerCommunicator(
#             'http://127.0.0.1:5000/API/v1',
#             username,
#             password,
#             "/Users/marc0/progetto/prove_deamon").upload_file(file_path, put_file)
#         encoded = httpretty.last_request().headers['authorization'].split()[1]
#         authorization_decoded = base64.decodestring(encoded)
#         #data = httpretty.last_request().parsed_body
#         path = httpretty.last_request().path
#         host = httpretty.last_request().headers['host']
#         method = httpretty.last_request().method
        
#         #check if authorization is equals
#         self.assertEqual(authorization_decoded, mock_auth_user)
#         #check if data is equals
#         #self.assertEqual(data, mock_data)
#         #check if url and method is equals

#         self.assertEqual(path, '/API/v1/files/bla.txt')
#         self.assertEqual(host, '127.0.0.1:5000')
#         if put_file:
#             self.assertEqual(method, 'PUT')
#         else:
#             self.assertEqual(method, 'POST')

#     def init_snapshot(self):
#         config = client_daemon.load_config()
#         return client_daemon.DirSnapshotManager(config['dir_path'], config['snapshot_file_path'])
        
#     def test_syncronize_dispatcher(self):
#         snapshot_manager = self.init_snapshot()

#         mock_snapshot_1 = {
#             '12345a': [u'/Users/marc0/progetto/prove_deamon\\bla.txt'],
#             '12345b': [u'/Users/marc0/progetto/prove_deamon\\asdas\\gbla.txt'],
#             '12345c': [u'/Users/marc0/progetto/prove_deamon\\asdas\\asdasd.txt'],
#             '12345d': [u'/Users/marc0/progetto/prove_deamon\\dsa.txt',
#                 u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (2).txt',
#                 u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (3).txt',
#                 u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (4).txt'],
#             '12345e': [u'farlocco_2'],
#         }
        
#         mock_snapshot_2 = {
#             '12345a': [u'/Users/marc0/progetto/prove_deamon\\bla.txt'],
#             '12345b': [u'/Users/marc0/progetto/prove_deamon\\asdas\\gbla.txt'],
#             '12345c': [u'/Users/marc0/progetto/prove_deamon\\asdas\\asdasd.txt'],
#             '12345d': [u'/Users/marc0/progetto/prove_deamon\\dsa.txt',
#                 u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (2).txt',
#                 u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (3).txt',
#                 u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (4).txt'],
#             '12345e': [u'farlocco_2'],
#         }

#         mock_snap_local = mock_snapshot_1
#         mock_snap_server = mock_snapshot_1


#         print "\n{:*^60}\n".format("\nno deamon internal conflicts == timestamp\n")
#         snapshot_manager.syncronize_dispatcher(
#             server_timestamp=123123,
#             server_snapshot=mock_snap_server)

#         print "\n{:*^60}\n".format("\nno deamon internal conflicts != timestamp\n")
#         snapshot_manager.syncronize_dispatcher(
#             server_timestamp=123124,
#             server_snapshot=mock_snap_server)
        
#         snapshot_manager.last_status['snapshot'] = "21451512512512512"

#         print "\n{:*^60}\n".format("\ndeamon internal conflicts == timestamp\n")
#         snapshot_manager.syncronize_dispatcher(
#             server_timestamp=123123,
#             server_snapshot=mock_snap_server)

#         print "\n{:*^60}\n".format("\nno deamon internal conflicts != timestamp\n")
#         snapshot_manager.syncronize_dispatcher(
#             server_timestamp=123124,
#             server_snapshot=mock_snap_server)

#     def diff_snapshot_paths(self):
#         snapshot_manager = self.init_snapshot()
#         #mock_equal = """[u'/Users/marc0/progetto/prove_deamon/asdas/asdasd.txt', u'/Users/marc0/progetto/prove_deamon/asdas/Nuovo documento di testo.txt', u'/Users/marc0/progetto/prove_deamon/dsa.txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documento di testo (4).txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documentodi testo (3).txt', u'/Users/marc0/progetto/prove_deamon/bla.txt', u'/Users/marc0/progetto/prove_deamon/asdas/sdadsda.txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documento di testo (5).txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documento di testo.txt', u'/Users/marc0/progetto/prove_deamon/Nuovo documento di testo (2).txt']"""
#         #mock_new_client = """[u'/Users/marc0/progetto/prove_deamon/asdas/bla.txt', u'/Users/marc0/progetto/prove_deamon/asd/gbla.txt', u'/Users/marc0/progetto/prove_deamon/asdas/gbla.txt']"""
#         #mock_new_server= """['path_farlocca']"""

#         snap_client = snapshot_manager.local_full_snapshot
#         snap_server = {
#                     '9406539a103956dc36cb7ad35547198c': [u'/Users/marc0/progetto/prove_deamon\\bla.txt'],
#                     'a8f5f167f44f4964e6c998dee827110c': [
#                                                     u'/Users/marc0/progetto/prove_deamon\\asd\\gbla.txt',
#                                                     u'/Users/marc0/progetto/prove_deamon\\asdas\\bla.txt',
#                                                     u'/Users/marc0/progetto/prove_deamon\\asdas\\gbla.txt'],
#                     'c21e1af364fa17cc80e0bbec2dd2ce5c': [u'/Users/marc0/progetto/prove_deamon\\asdas\\asdasd.txt'],
#                     'd41d8cd98f00b204e9800998ecf8427e': [
#                                                     u'/Users/marc0/progetto/prove_deamon\\dsa.txt',
#                                                     u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (2).txt',
#                                                     u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (3).txt',
#                                                     u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (4).txt',
#                                                     u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo (5).txt',
#                                                     u'/Users/marc0/progetto/prove_deamon\\Nuovo documento di testo.txt',
#                                                     u'/Users/marc0/progetto/prove_deamon\\asdas\\Nuovo documento di testo.txt',
#                                                     u'/Users/marc0/progetto/prove_deamon\\asdas\\sdadsda.txt',
#                                                     u'path_farlocca']
#                 }
#         new_client, new_server, equal = snapshot_manager.diff_snapshot_paths(snap_client, snap_server)
        
#         #new_client = str(new_client).replace('\\\\','/')
#         #new_server = str(new_server).replace('\\\\','/')
#         #equal = str(equal).replace('\\\\','/')

#         #self.assertEqual(str(new_client), mock_new_client)
#         #self.assertEqual(str(equal), mock_equal)
#         #self.assertEqual(str(new_server), mock_new_server)

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
        file_to_move = open('{}/file_to_move.txt'.format(self.client_path), 'w')
        file_to_move.write('this is a test')
        #source_path = '{}/{}'.format(self.client_path, self.filename)
        source_path = file_to_move.name
        dest_path = '{}/dir1/{}'.format(self.client_path, self.filename)
        #dest_path = '/tmp/Folder/{}'.format(self.filename)
        file_to_move.close()
        self.file_system_op.move_a_file(source_path, dest_path)
        written_file = open(dest_path, 'rb').read()
        self.assertEqual('this is a test', written_file)




if __name__ == '__main__':
    unittest.main()
