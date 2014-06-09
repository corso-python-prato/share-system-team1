from client_cmdmanager import RawBoxCmd 
import unittest
import sys

class CmdManagerTest(unittest.TestCase):

    def setUp(self):
        self.command_user = "user"
        self.username = "marco"

    def test_do_create(self):
        RawBoxCmd().do_create(self.command_user)
        RawBoxCmd().do_create(self.command_user + " " + self.username)


if __name__ == '__main__':
    unittest.main()