from httmock import all_requests, HTTMock
import client_daemon
import unittest
import requests
import sys
import os


@all_requests
def response_xxx(url, request):
	return {'status_code': 201}

class ClientDaemonTest(unittest.TestCase):
	def setup(self):
		pass

	def test_upload(self):
		def mock_req_post(*args, **kwargs):
			global upload_auth, upload_data, upload_url
			upload_auth = kwargs['auth']
			upload_data = kwargs['data']
			upload_url = args[0]

		client_daemon.req_post = mock_req_post

		password = "passwordSegretissima"
		username = "usernameFarlocco"
		
		path = os.path.join("test_mock", "prova.txt")

		mock_file_content = open(path, 'r').read()
		mock_auth_user = client_daemon.base64.encodestring(username)
		mock_auth_psw = client_daemon.base64.encodestring(password)
		mock_url = 'http://127.0.0.1:5000/API/v1/files/test_mock/prova.txt' 
		mock_data = {
				'file_name': 'prova.txt', 
				'file_content': mock_file_content
			}


		client_daemon.ServerCommunicator(
			'http://127.0.0.1:5000/API/v1', 
			username, 
			password).post(path)
		
		#check if username is equals
		self.assertEqual(upload_auth.username, mock_auth_user)
		#check if password is equals
		self.assertEqual(upload_auth.password, mock_auth_psw)
		#check if data is equals
		self.assertEqual(upload_data, mock_data) 
		#check if url is equals
		self.assertEqual(upload_url, mock_url)   

	def test_put(self):
		pass

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

