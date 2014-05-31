#!/usr/bin/env python
#-*- coding: utf-8 -*-

import platform
import getpass
import cmd
import sys
import re
import os

sys.path.insert(0, 'test/')
import fakerequests as requests

sys.path.insert(0, 'utility/')
from colorMessage import Message

class RawBoxCmd(cmd.Cmd):
	"""RawBox command line interface"""

	intro = Message().color('INFO','##### Hello guy!... or maybe girl, welcome to RawBox ######\ntype ? to see help\n\n')
	doc_header = Message().color('INFO',"command list, type ? <topic> to see more :)")
	prompt = Message().color('HEADER', '(RawBox) ')
	ruler = Message().color('INFO','~')


	def _create_user(self, username = None):
		"""create user if not exists"""
		  
		if not username:
			username  = raw_input('insert your user name: ')

		password = getpass.getpass('insert your password: ')
		rpt_password = getpass.getpass('Repeat your password: ')
		
		while password != rpt_password:	
			Message('WARNING', 'password not matched')
			password = getpass.getpass('insert your password: ')
			rpt_password = getpass.getpass('Repeat your password: ')

		email_regex = re.compile('[^@]+@[^@]+\.[^@]+')
		email = raw_input('insert your user email: ')
		
		while not email_regex.match(email):
			Message('WARNING', 'invalid email')
			email = raw_input('insert your user email: ')

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
	add user <*user_list> group=<group_name> (add a new RawBox user to the group)
	add admin <*user_list> group=<group_name> (add a new RawBox user as admin to the group)
		"""
		if line:
			command = line.split()[0]
			arguments = line.split()[1:]
			{
				'user': self._add_user,
				'admin': self._add_admin,
			}.get(command, self.error)(arguments)
		else: 
			Message('INFO', self.do_add.__doc__)

	def do_create(self, line):
		""" 
	create user <name>  (create a new RawBox user)
	create group <name> (create a new shareable folder with your friends)	
		"""
		if line:
			command = line.split()[0]
			arguments = line.split()[1:]
			{
				'user': self._create_user,
			 	'group': self._create_group,
			}.get(command, self.error)(arguments)
		else: 
			Message('INFO', self.do_create.__doc__)

	def do_q(self, line = None):
		""" exit from RawBox"""
		if raw_input('[Exit] are you sure? y/n ') == 'y':
			return True

	def do_quit(self, line = None):
		""" exit from RawBox"""
		if raw_input('[Exit] are you sure? y/n ') == 'y':
			return True

def main():
	if platform.system() == 'Windows':
		os.system('cls')
	else:
		os.system('clear')

	try:
		RawBoxCmd().cmdloop()
	except KeyboardInterrupt:
		print RawBoxCmd().do_quit()

if __name__ == '__main__':
	main()
