from httmock import all_requests, HTTMock
import unittest
import requests
import sys

sys.path.insert(0, '../../client')
import client_daemon

@all_requests
def response_201(url, request):
	"""Upload OK"""

	return {'status_code': 201}

def response_300(url, request):
	"""Access Denied"""
	return {'status_code': 300}


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

		login = {"psw": "pswMarco", "user": "userMarco"}
		path = "mock_file/prova.txt"
		
		mock_auth_user = 'userMarco'
		mock_auth_psw = 'pswMarco'
		mock_url = 'http://www.mioserver.it/files/mock_file/prova.txt' 
		mock_data = {
				'file_name': 'prova.txt', 
				'file_content': 'LOREM IPSIUM!'
			}

		client_daemon.ServerCommunicator("http://www.mioserver.it").post(path, login)

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

