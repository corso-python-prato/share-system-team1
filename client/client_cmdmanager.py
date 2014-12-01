#!/usr/bin/env python
#-*- coding: utf-8 -*-

import ConfigParser
import platform
import getpass
import cmd
import re
import os

from communication_system import CmdMessageClient
from colorMessage import Message


FILE_CONFIG = "config.ini"
CONFIG = ConfigParser.ConfigParser()
CONFIG.read(FILE_CONFIG)
EMAIL_REGEX = re.compile('[^@]+@[^@]+\.[^@]+')


def take_input(message, password=False):
    """This function takes input data from console.
    @param message This is the input parameter
    @param password This is a flag set to False as default. If it is true,
        the message is taken with getpass method
    @return The input of the message with the right method (raw_input()
        or getpass.getpass())
    """

    if not password:
        return raw_input(message)
    else:
        return getpass.getpass(message)


def take_valid_username(username=None):
    """This function takes username as input and check it
    with EMAIL_REGEX.match.
    @param username This is the username, set to None as default.
    If it is none, it is requested with take_input method
    @return Username taken
    """

    if not username:
        username = take_input('insert your email: ')
    while not EMAIL_REGEX.match(username):
        Message('WARNING', 'invalid email')
        username = take_input('insert your email: ')
    return username


def check_shareable_path(path):
    """This function checks if the path is the RawBox root.
    @param path The path to check
    @return True or False
    """

    if len(path.split("/")) != 1:
        Message(
            "WARNING",
            ("A shared resource has to be in the RawBox root."
             "Please do not use '/'")
        )
        return False

    # check if the resource exists
    dir_path = CONFIG.get("daemon_communication", "dir_path")
    if not os.path.exists(os.path.join(dir_path, path)):
        Message(
            "WARNING",
            "The specified resource doesn't exist"
        )
        return False
    return True


class RawBoxExecuter(object):
    """This class contains all RawBox's functions that are called by the
    user using the command line interface."""

    def __init__(self, comm_sock):
        """The constructor.
        @param comm_sock Socket used by the Communication System to
        communicate with daemon.
        """

        self.comm_sock = comm_sock

    def _create_user(self, username=None):
        """This method is used to create a new user. It sends a message to
        the Communication System.
        @param username The new user's username, set to None as default.
        If it is None, it is requested with take_input method.
        """

        command_type = 'create_user'

        username = take_valid_username(username)
        password = take_input("\n"
                "The password should be a combination of numbers with "
                "a mix of uppercase, lowercase and special characters."
                "\nPassword example = Rawbox1.0\n\n"
                "Insert your password:", password=True)
        rpt_password = take_input('Repeat your password: ', password=True)
        while password != rpt_password:
            Message('WARNING', 'password not matched')
            password = take_input('insert your password: ', password=True)
            rpt_password = take_input('Repeat your password: ', password=True)

        param = {
            'user': username,
            'psw': password,
            'reset': 'False'
        }

        self.comm_sock.send_message(command_type, param)
        self.print_response(self.comm_sock.read_message())

    def _activate_user(self, username=None, code=None):
        """This method is used to activate a user previously created.
        It sends a message to the Communication System.
        @param username The new user's username, set to None as default.
        If it is None, it is requested with take_input method.
        @param code Activation code, set to None as default.
        If it is None, it is requested with take_input method.
        """

        command_type = 'activate_user'

        username = take_valid_username(username)
        if not code:
            code = take_input('insert your code: ')
        while len(code) != 32:
            Message('WARNING', 'invalid code must be 32 character')
            code = take_input('insert your code: ')

        param = {
            'user': username,
            'code': code,
            'reset': 'False'
        }

        self.comm_sock.send_message(command_type, param)
        self.print_response(self.comm_sock.read_message())

    def _delete_user(self):
        """This method is used to delete a user. It sends a message to
        the Communication System."""

        command_type = 'delete_user'

        self.comm_sock.send_message(command_type, {})
        self.print_response(self.comm_sock.read_message())

    def _add_user(self, *args):
        """This method is used to add one or more users to a group.
        It sends a message to the Communication System.
         @param *args One or more users
        """

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

    def _reset_password(self, username=None):
        """This method is used to send a reset request for the password.
        It sends a message to the Communication System.
        @param username Username of the user the sends the reset request.
        If it is None, it is requested with take_input method.
        """

        if not username:
            username = take_input('insert your email: ')
        email_regex = re.compile('[^@]+@[^@]+\.[^@]+')
        while not email_regex.match(username):
            Message('WARNING', 'invalid email')
            username = take_input('insert your email: ')

        param = {
            'user': username,
            'reset': 'True'
        }

        self.comm_sock.send_message('reset_password', param)
        self.print_response(self.comm_sock.read_message())

    def _set_password(self, username=None, code=None):
        """This method is used to set a new password after a reset request.
        It sends a message to the Communication System.
        @param username Username of the user that set a new password.
        If it is None, it is requested with take_input method.
        @param code Activation code necessary to set a new password.
        If it is None, it is requested with take_input method.
        """

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

        password = take_input('insert your password: ', password=True)
        rpt_password = take_input('Repeat your password: ', password=True)
        while password != rpt_password:
            Message('WARNING', 'password not matched')
            password = take_input('insert your password: ', password=True)
            rpt_password = take_input('Repeat your password: ', password=True)

        param = {
            'user': username,
            'reset': 'True',
            'code': code,
            'psw': password
        }

        self.comm_sock.send_message("set_password", param)
        self.print_response(self.comm_sock.read_message())

    def _add_share(self, path, beneficiary):
        """This method is used to create a share. It sends a message to the
        Communication System.
        @param path The path used to create a share.
        @param beneficiary User beneficiary of sharing
        """

        param = {
            'path': path,
            'beneficiary': beneficiary
        }
        self.comm_sock.send_message("add_share", param)
        self.print_response(self.comm_sock.read_message())

    def _remove_share(self, path):
        """This method is used to remove a share. It sends a message to the
        Communication System.
        @param path Share's path to remove.
        """

        param = {
            'path': path,
        }
        self.comm_sock.send_message("remove_share", param)
        self.print_response(self.comm_sock.read_message())

    def _remove_beneficiary(self, path, beneficiary):
        """This method is used to remove a beneficiary from the share.
        It sends a message to the Communication System.
        @param path Share's path.
        @param beneficiary Beneficiary to remove.
        """

        param = {
            'path': path,
            'beneficiary': beneficiary,
        }
        self.comm_sock.send_message("remove_beneficiary", param)
        self.print_response(self.comm_sock.read_message())

    def _get_shares_list(self):
        """This method is used to get the list of shares"""

        command_type = 'get_shares_list'

        self.comm_sock.send_message(command_type)
        self.print_response(self.comm_sock.read_message())

    def print_response(self, response):
        """This method print response from the daemon.
        The response is a dictionary as:
            {
                'request': type of command
                'body':
                    'result': result for command
                    'details': list of eventual detail for command
            }
        @param response Response from the daemon.
        """

        print 'Response for "{}" command'.format(response['request'])
        print 'result: {}'.format(response['body']['result'])
        if response['body']['details']:
            print 'details:'
            for detail in response['body']['details']:
                print '\t{}'.format(detail)


class RawBoxCmd(cmd.Cmd):
    """This class contains the RawBox command line interface."""

    intro = Message().color('INFO', '##### Hello guy!... or maybe girl, \
    welcome to RawBox ######\ntype ? to see help\n\n')
    doc_header = Message().color('INFO', "command list, type ? <topic> \
        to see more :)")
    prompt = Message().color('HEADER', '(RawBox) ')
    ruler = Message().color('INFO', '~')

    def __init__(self, executer):
        """The constructor.
        @param executer An instance of RawBoxExecuter that contains all
        RawBox's functions.
        """

        cmd.Cmd.__init__(self)
        self.executer = executer

    def error(self, message=None):
        if message:
            print message
        else:
            print "hum... unknown command, please type help"

    def do_create(self, line):
        """
        It is the user creation command available for the user.
        create user <name>  (create a new RawBox user)
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
        """It is the user activation command available for the user,
        previously creation.
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
                self.error("You have to specify:"
                    "<your email><your activation code>")

    def do_delete(self, line):
        """It is the user deletion command available for the user."""

        if line:
            self.error("Delete command don't takes parameters")
        else:
            if take_input("Are you sure to delete your account?"
                          "[yes/no] ") == "yes":
                self.executer._delete_user()

    def do_add_share(self, line):
        """It is the share creation command available for the user.
        It shares a resource with a beneficiary.
        Expected: add_share <path> <beneficiary>
        (the path starts from the RawBox root)
        """

        try:
            path, beneficiary = line.split()
            # check if the user try to share with himself
            if beneficiary != CONFIG.get('daemon_user_data', 'username'):
                if check_shareable_path(path):
                    self.executer._add_share(path, beneficiary)
            else:
                Message("INFO", self.do_add_share.__doc__)

        except ValueError:
            Message("INFO", self.do_add_share.__doc__)

    def do_remove_share(self, path):
        """It is the share deletion command available for the user.
        Expected: remove_share <path>
        (the path starts from the RawBox root)
        """

        try:
            if check_shareable_path(path):
                self.executer._remove_share(path)

        except ValueError:
            Message("INFO", self.do_remove_share.__doc__)

    def do_remove_beneficiary(self, line):
        """It is the command for the removal of a beneficiary from a share
        available for the user.
        Expected: remove_beneficiary <path> <beneficiary>
        """

        try:
            path, beneficiary = line.split()
            if beneficiary != CONFIG.get('daemon_user_data', 'username'):
                if check_shareable_path(path):
                    if take_input(
                            ('User {} will be removed from the share,'
                            ' are you sure? y/n ').format(beneficiary)) == 'y':
                        self.executer._remove_beneficiary(path, beneficiary)
            else:
                Message('INFO', self.do_remove_beneficiary.__doc__)
        except (IndexError, ValueError):
            Message('INFO', self.do_remove_beneficiary.__doc__)

    def do_get_shares_list(self, line=None):
        """This command lets user to visualize all his shares list."""

        self.executer._get_shares_list()

    def do_q(self, line=None):
        """This command lets user to exit from RawBox typing 'q'."""

        if take_input('[Exit] are you sure? y/n ') == 'y':
            return True

    def do_quit(self, line=None):
        """This command lets user to exit from RawBox typing 'quit'."""

        if take_input('[Exit] are you sure? y/n ') == 'y':
            return True

    def do_reset_password(self, line):
        """This command lets user to do a reset password request.
        Expected: <reset_password> <email_user>
        """

        user = None
        try:
            user = line.split()[0]
            self.executer._reset_password(user)
        except IndexError:
            if not user:
                Message('INFO', self.do_reset_password.__doc__)

    def do_set_password(self, line):
        """This command lets user to set a new password after a reset request.
        Expected: <set_password> <email_user> <code>
        """

        user = None
        code = None
        try:
            user = line.split()[0]
            code = line.split()[1]
            self.executer._set_password(user, code)
        except IndexError:
            if not user or not code:
                Message('INFO', self.do_set_password.__doc__)


def main():
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')

    host = CONFIG.get('cmd', 'host')
    port = CONFIG.get('cmd', 'port')
    comm_sock = CmdMessageClient(host, int(port))
    try:
        RawBoxCmd(RawBoxExecuter(comm_sock)).cmdloop()
    except KeyboardInterrupt:
        print "[exit]"

if __name__ == '__main__':
    main()
