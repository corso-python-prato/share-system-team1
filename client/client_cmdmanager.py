#!/usr/bin/env python
#-*- coding: utf-8 -*-

from communication_system import CmdMessageClient
from colorMessage import Message
import ConfigParser
import platform
import getpass
import cmd
import re
import os

FILE_CONFIG = "config.ini"


def take_input(message, password=False):
    if not password:
        return raw_input(message)
    else:
        return getpass.getpass(message)


class RawBoxExecuter(object):

    def __init__(self, comm_sock):
        self.comm_sock = comm_sock

    def _create_user(self, username=None):
        """ create user if not exists """
        command_type = 'create_user'

        if not username:
            username = take_input('insert your email: ')
        email_regex = re.compile('[^@]+@[^@]+\.[^@]+')
        while not email_regex.match(username):
            Message('WARNING', 'invalid email')
            username = take_input('insert your email: ')

        password = take_input('insert your password: ', password=True)
        rpt_password = take_input('Repeat your password: ', password=True)
        while password != rpt_password:
            Message('WARNING', 'password not matched')
            password = take_input('insert your password: ', password=True)
            rpt_password = take_input('Repeat your password: ', password=True)

        param = {
            'user': username,
            'psw': password
        }

        self.comm_sock.send_message(command_type, param)
        self.print_response(self.comm_sock.read_message())

    def _activate_user(self, username=None, code=None):
        """ activate user previously created """
        command_type = 'activate_user'

        if not username:
            username = take_input('insert your email: ')
        email_regex = re.compile('[^@]+@[^@]+\.[^@]+')
        while not email_regex.match(username):
            Message('WARNING', 'invalid email')
            username = take_input('insert your email: ')

        if not code:
            code = take_input('insert your code: ')
        while len(code) != 32:
            Message('WARNING', 'invalid code must be 32 character')
            code = take_input('insert your code: ')

        param = {
            'user': username,
            'code': code
        }

        self.comm_sock.send_message(command_type, param)
        self.print_response(self.comm_sock.read_message())

    def _delete_user(self, username=None):
        """ delete user if is logged """
        command_type = 'delete_user'

        if not username:
            username = take_input('insert your email: ')
        email_regex = re.compile('[^@]+@[^@]+\.[^@]+')
        while not email_regex.match(username):
            Message('WARNING', 'invalid email')
            username = take_input('insert your email: ')
        param = {
            'user': username
        }
        self.comm_sock.send_message(command_type, param)
        self.print_response(self.comm_sock.read_message())

    def _add_user(self, *args):
        """add user/s to a group """
        command_type = 'add_to_group'
        args = args[0]
        users = args[:-1]
        try:
            group = args[-1].split("group=")[1]
            if group.strip() == "":
                raise IndexError
        except IndexError:
            Message('WARNING', '\nyou must specify a group for example \
                add user marco luigi group=your_group')
            return False

        for user in users:
            #call socket message
            print "add user ", user, " to group ", group
            param = {
                'user': user,
                'group': group,
            }
            self.comm_sock.send_message(command_type, param)
            self.print_response(self.comm_sock.read_message())

    def print_response(self, response):
        ''' print response from the daemon.
            the response is a dictionary as:
            {
                'request': type of command
                'body':
                    'result': result for command
                    'details': list of eventual detail for command
            }
        '''
        print 'Response for "{}" command'.format(response['request'])
        print 'result: {}'.format(response['body']['result'])
        if response['body']['details']:
            print 'details:'
            for detail in response['body']['details']:
                print '\t{}'.format(detail)


class RawBoxCmd(cmd.Cmd):
    """RawBox command line interface"""

    intro = Message().color('INFO', '##### Hello guy!... or maybe girl, \
    welcome to RawBox ######\ntype ? to see help\n\n')
    doc_header = Message().color('INFO', "command list, type ? <topic> \
        to see more :)")
    prompt = Message().color('HEADER', '(RawBox) ')
    ruler = Message().color('INFO', '~')

    def __init__(self, executer):
        cmd.Cmd.__init__(self)
        self.executer = executer

    def error(self, message=None):
        if message:
            print message
        else:
            print "hum... unknown command, please type help"

    def do_create(self, line):
        """
        create a new RawBox user
        create user <email>
        """
        try:
            command = line.split()[0]
            arguments = line.split()[1]
            if command != 'user':
                self.error("error, wrong command. Use 'create user'")
            else:
                self.executer._create_user(arguments)
        except IndexError:
            self.error("error, must use command user")
            Message('INFO', self.do_create.__doc__)

    def do_activate(self, line):
        """
        activate a new RawBox user previously created
        activate <email> <code>
        """
        user = None
        try:
            user = line.split()[0]
            code = line.split()[1]
            self.executer._activate_user(user, code)
        except IndexError:
            if not user:
                Message('INFO', self.do_activate.__doc__)
            else:
                self.error("You have to specify: <your email> <your activation code>")

    def do_delete(self, line):
        """
        delete a RawBox user if He is logged
        """
        if line:
            user = line.split()[0]
            self.executer._delete_user(user)
        else:
            Message('INFO', self.do_delete.__doc__)

    def do_q(self, line=None):
        """ exit from RawBox"""
        if take_input('[Exit] are you sure? y/n ') == 'y':
            return True

    def do_quit(self, line=None):
        """ exit from RawBox"""
        if take_input('[Exit] are you sure? y/n ') == 'y':
            return True


def main():
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')

    config = ConfigParser.ConfigParser()
    config.read(FILE_CONFIG)
    host = config.get('cmd', 'host')
    port = config.get('cmd', 'port')
    comm_sock = CmdMessageClient(host, int(port))
    try:
        RawBoxCmd(RawBoxExecuter(comm_sock)).cmdloop()
    except KeyboardInterrupt:
        print "[exit]"

if __name__ == '__main__':
    main()
