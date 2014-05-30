#!/usr/bin/env python
#-*- coding: utf-8 -*-
#	30/05/2014
#
#	(c) marco p , francesco m
#

import cmd

class HelloWorld(cmd.Cmd):
	"""Simple command processor example."""
	
	def _create_user(self, *args):
		"""create user/s"""
		print "create user/s ", args

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
	intro = "##### Hello guy!... or maybe girl, welcome to RawBox ######\ntype help to start\n\n"
	try:
		HelloWorld().cmdloop(intro = intro)
	except KeyboardInterrupt:
		print 'Exit'

if __name__ == '__main__':
	main()
