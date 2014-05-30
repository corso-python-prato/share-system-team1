#!/usr/bin/env python
#-*- coding: utf-8 -*-

import getpass
import cmd
import sys
import re

sys.path.insert(0, 'test/')
import fakerequests as requests

class Message(object):
	_message_type = {
	 	'HEADER': '\033[95m',
		'INFO': '\033[94m',
		'SUCCESS': '\033[92m',
		'WARNING': '\033[93m',
		'ERROR': '\033[91m',
		'ENDC': '\033[0m',
	}

	def __init__(self, color = None, message = None):
		if color and message:
			if color in Message._message_type:
				print Message._message_type[color] , message , Message._message_type['ENDC']
			else: print message

	def color(self, color, message):
		if color in Message._message_type:
			return Message._message_type[color] + message + Message._message_type['ENDC']
		else: print message

class RowBoxCmd(cmd.Cmd):
	"""RowBox command line interface."""

	def _create_user(self, username = None):
		"""create user if not exists"""
		  
		if not username:
			username  = raw_input('insert your user name ->\t')

		password = getpass.getpass('insert your password: ')
		rpt_password = getpass.getpass('Repeat your password: ')
		
		while password != rpt_password:	
			Message('WARNING', 'password not matched')
			password = getpass.getpass('insert your password: ')
			rpt_password = getpass.getpass('Repeat your password: ')

		email_regex = re.compile('[^@]+@[^@]+\.[^@]+')
		email = raw_input('insert your user email ->\t')
		
		while not email_regex.match(email):
			Message('WARNING', 'invalid email')
			email = raw_input('insert your user email ->\t')

		user = 	{	
					'user': username, 
					'psw': password, 
					'email': email
				}

		r = requests.post("http://httpbin.org/post", data=user)
		
		if r.status_code == 201:
			Message('SUCCESS','User created')
		elif r.status_code == 409:
			Message('WARNING','\nUser already exists\n')
		elif r.status_code == 400:
			Message('WARNING','\nIncorrect data format')
		else:
			Message('ERROR','Oops.. error ' + str(r.status_code) + ' please retry later')


	def _create_group(self, *args):
		"""create group/s"""
		print "create group/s ", args

	def _add_user(self, *args):
		"""add user/s to a group """
		print "add user/s to a group", args

	def _add_admin(self, *args):
		"""add admin/s to a group """
		print "add user/s to a group as admin/s", args

	def error(self, *args):
		print "hum... unknown command, please type help"

	def do_add(self, line):
		"""
		add <user> <user_list> group=<group_name> (add a new RawBox user to the group)
		add <admin> <user_list> group=<group_name> (add a new RawBox user as admin to the group)
		"""
		command = line.split()[0]
		arguments = line.split()[1:]
		{
			'user': self._add_user,
			'admin': self._add_admin,
		}.get(command, self.error)(arguments)


	def do_create(self, line):
		""" 
		create <user> (create a new RawBox user)
		create <group> (create a new shareable folder with your friends)	
		"""
		command = line.split()[0]
		arguments = line.split()[1:]
		{
			'user': self._create_user,
		 	'group': self._create_group,
		}.get(command, self.error)(arguments)

	def do_q(self, line):
		""" exit from RawBox"""
		return True

	def do_quit(self, line):
		""" exit from RawBox"""
		return True   

def main():
	intro = Message().color('INFO','##### Hello guy!... or maybe girl, welcome to RawBox ######\ntype help to start\n\n')
	try:
		rowboxcmd = RowBoxCmd()
		rowboxcmd.prompt = Message().color('HEADER', '(RowBox) ')
		rowboxcmd.cmdloop(intro = intro)
	except KeyboardInterrupt:
		print 'Exit.'

if __name__ == '__main__':
	main()
