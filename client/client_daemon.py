#!/usr/bin/env python
#-*- coding: utf-8 -*-


# inotify observer unable to detect 'dragging file to trash' events
# from https://github.com/gorakhargosh/watchdog/issues/46 use polling solution

# from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
from requests.auth import HTTPBasicAuth
import requests
import base64
import time
import json
import os

def req_post(*args, **kwargs):
	return requests.post(*args, **kwargs)


class ServerCommunicator(object):

	def __init__(self, server_url, username, password):
		self.server_url = server_url
		self.auth = HTTPBasicAuth(
			base64.encodestring(username), 
			base64.encodestring(password))

	def get(self, dst_path):
		r = requests.get(self.server_url)
	
	def post(self, dst_path):
		file_name = dst_path.split(os.path.sep)[-1]
		file_content = ''
		
		try:
			with open(dst_path, 'r') as f:
				file_content =  f.read()
		except IOError:
			#Atomic create and delete error!
			return False

		upload = {
					'file_name': file_name,
					'file_content': file_content
				 }

		server_url = "{}/files/{}".format(
				self.server_url, 
				dst_path.replace(os.path.sep, '/'))

		req_post(server_url, data = upload, auth = self.auth)

	def put(self, dst_path):
		r = requests.get(self.server_url)

	def delete(self, dst_path):
		r = requests.get(self.server_url)


def load_config():
	with open('config.json', 'r') as config_file:
		config = json.load(config_file)
	return config


class DirectoryEventHandler(FileSystemEventHandler):

	def __init__(self, cmd):
		self.cmd = cmd
		
	# def on_any_event(self, event):
		# request = requests.get(self.server_url)

	def on_moved(self, event):
		"""Called when a file or a directory is moved or renamed.

		:param event:
			Event representing file/directory movement.
		:type event:
			:class:`DirMovedEvent` or :class:`FileMovedEvent`
		"""
		self.cmd.delete(event.src_path)
		self.cmd.post(event.dest_path)

	def on_created(self, event):
		"""Called when a file or directory is created.

		:param event:
			Event representing file/directory creation.
		:type event:
			:class:`DirCreatedEvent` or :class:`FileCreatedEvent`
		"""
		self.cmd.post(event.src_path)

	def on_deleted(self, event):
		"""Called when a file or directory is deleted.

		:param event:
			Event representing file/directory deletion.
		:type event:
			:class:`DirDeletedEvent` or :class:`FileDeletedEvent`
		"""
		self.cmd.delete(event.src_path)

	def on_modified(self, event):
		"""Called when a file or directory is modified.

		:param event:
			Event representing file/directory modification.
		:type event:
			:class:`DirModifiedEvent` or :class:`FileModifiedEvent`
		"""
		if not event.is_directory:
			self.cmd.put(event.src_path)


def main():
	config = load_config()

	server_com = ServerCommunicator(
		server_url = config['server_url'], 
		username = config['username'],
		password = config['password'])

	event_handler = DirectoryEventHandler(server_com)
	observer = Observer()
	observer.schedule(event_handler, config['dir_path'], recursive=True)
	observer.start()
	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		observer.stop()
	observer.join()

if __name__ == '__main__':
	main()
