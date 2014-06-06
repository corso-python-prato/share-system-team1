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

    def test_correct_data_format_post(self):
        def mock_req_post(*args, **kwargs):
            global content
            content = args

        client_daemon.req_post = mock_req_post
        login = {"psw": "marco", "user": "marco"}
        path = "mock_file/prova.txt"
        mock_result = (
            'http://www.mioserver.it/files/mock_file/prova.txt', 
            {
                'username': 'marco', 
                'file_name': 'prova.txt', 
                'password': 'marco', 
                'file_content': 'LOREM IPSIUM!'
            })

        client_daemon.ServerCommunicator("http://www.mioserver.it").post(path, login)
        self.assertEqual(content, mock_result) 

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

