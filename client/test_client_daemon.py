import client_daemon
import httpretty
import unittest
import requests
import base64
import sys
import os
import json

class ClientDaemonTest(unittest.TestCase):
	def setUp(self):
		httpretty.enable()
		httpretty.register_uri(httpretty.POST,
		'http://127.0.0.1:5000/API/v1/files/test_mock/prova.txt',
		data = {"response":"ok"})

	def tearDown(self):
		httpretty.disable()
		httpretty.reset()
    
	def test_upload(self, put_file = False):
		password = "passwordSegretissima"
		username = "usernameFarlocco"
		
		path = os.path.join("test_mock", "sub_folder",  "prova.txt")

		mock_file_content = open(path, 'r').read()
		mock_auth_user = ":".join([username, password])
		mock_path = '/API/v1/files/test_mock/sub_folder' 
		mock_data = {
				u'file_name': [u'prova.txt'], 
				u'file_content': [unicode(mock_file_content)]
			}

		client_daemon.ServerCommunicator(
			'http://127.0.0.1:5000/API/v1', 
			username, 
			password).upload_file(path, put_file)
		
		encoded = httpretty.last_request().headers['authorization'].split()[1]
		authorization_decoded = base64.decodestring(encoded)
		data = httpretty.last_request().parsed_body
		path = httpretty.last_request().path
		
		#check if authorization is equals
		self.assertEqual(authorization_decoded, mock_auth_user)
		#check if data is equals
		self.assertEqual(data, mock_data) 
		#check if url is equals
		self.assertEqual(path, mock_path)

	def test_download(self):
		   pass

	def test_upload_put(self):
		self.test_upload(put_file = True)

	def test_synchronize(self):
		status_code = 200

		def fakewrite_a_file(*args):
			return 'Writing a file'

		def fakedelete_a_file(*args):
			return 'Deleting a file'

		def fakemove_a_file(*args):
			return 'Moving a file'

		def fakecopy_a_file(*args):
			return 'Coping a file'

		if status_code != 204:
			diffs = json.load(open('test_mock/sync.json', 'r'))
			for tstamp, obj in diffs.iteritems():
				self.timestamp = tstamp #update self timestamp
				print 'Timestamp op: ', tstamp
				req = obj[0]
				print 'Request: ', req
				args = obj[1]
				print 'Arguments: ', args
				{
					'req_get': fakewrite_a_file,
					'req_delete': fakedelete_a_file,
					'req_move': fakemove_a_file,
					'req_copy': fakecopy_a_file
				}.get(req)(args) 

	def test_delete(self):
		pass

	def test_on_moved(self):
		pass

	def test_on_created(self):
		pass

	def test_on_deleted(self):
		pass

	def test_on_modified(self):
		pass


if __name__ == '__main__':
	unittest.main()
