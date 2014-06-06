import unittest
import sys

sys.path.insert(0, '../../client')
from client_cmdmanager import RawBoxCmd 

class CmdManagerTest(unittest.TestCase):

    def setUp(self):
        self.seq = range(10)

    def test_do_create(self):
       RawBoxCmd.do_create('user marco')

if __name__ == '__main__':
    unittest.main()