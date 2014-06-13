#!/usr/bin/env python
#-*- coding: utf-8 -*-


# inotify observer unable to detect 'dragging file to trash' events
# from https://github.com/gorakhargosh/watchdog/issues/46 use polling solution

# from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
from requests.auth import HTTPBasicAuth
import requests
import shutil
import base64
import time
import json
import os

def req_post(*args, **kwargs):
	try:
		return requests.post(*args, **kwargs)
	except requests.exceptions.RequestException:
		return True # TODO True x test | use False

def req_get(*args, **kwargs):
	try:
		return requests.get(*args, **kwargs)
	except requests.exceptions.RequestException:
		return False # TODO True x test | use False

def req_put(*args, **kwargs):
	try:
		return requests.put(*args, **kwargs)
	except requests.exceptions.RequestException:
		return True # TODO True x test | use False

def req_delete(*args, **kwargs):
	try:
		return requests.delete(*args, **kwargs)
	except requests.exceptions.RequestException:
		return True # TODO True x test | use False


class ServerCommunicator(object):

	def __init__(self, server_url, username, password, dir_path):
		self.auth = HTTPBasicAuth(username, password)
		self.server_url = server_url
		self.dir_path = dir_path
		self.retry_delay = 2

	def _try_request(self, callback, success = '', error = '', *args, **kwargs):
		""" try a request until it's a success """

		request_result = callback(*args, **kwargs)
		while not request_result:
			print error
			time.sleep(self.retry_delay)
			request_result = callback(*args, **kwargs)

		print success
		return request_result

	def get_fullpath(self, dst_path):
		return os.path.join(self.dir_path, dst_path)

	def download_file(self, dst_path):
		""" download a file from server"""

		error_log = "ERROR on download request " + dst_path
		success_log = "file downloaded! " + dst_path

		server_url = "{}/files/{}".format(self.server_url, dst_path)

		request = {
			"url": server_url,
			"auth": self.auth
		}
		r = self._try_request(req_get, success_log, error_log, **request)
		local_path = self.get_fullpath(dst_path)
		return local_path, r.text
	

	def upload_file(self, dst_path, put_file = False):
		""" upload a file to server """

		path = os.path.join(*(dst_path.split(os.path.sep)))
		file_content = ''
		try:
			file_content = open(dst_path, 'rb')
		except IOError:
			return False #Atomic create and delete error!

		server_url = "{}/files/{}".format(self.server_url, path)

		error_log = "ERROR upload request " + dst_path
		success_log = "file uploaded! " + dst_path
		request = {
			"url": server_url,
			"files": {'file_content':file_content},
			"auth": self.auth
		}
		if put_file:
			self._try_request(req_put, success_log, error_log, **request)
		else:
			self._try_request(req_post, success_log, error_log, **request)

	def delete_file(self, dst_path):
		""" send to server a message of file delete """

		error_log = "ERROR delete request " + dst_path
		success_log = "file deleted! " + dst_path

		server_url = "{}/files/{}".format(
				self.server_url, 
				dst_path.replace(os.path.sep, '/'))

		request = {
			"url": server_url,
			"auth": self.auth
		}
		self._try_request(req_delete, success_log, error_log, **request)

	def create_user(self, username, password):
		
		error_log = "User creation error"
		success_log = "user created!" 

		server_url = "{}/user/create".format(self.server_url)

		request = {
			"url": server_url,
			"data":{
					"user": username,
					"psw": password
			}
		}
		self._try_request(req_post, success_log, error_log, **request)

class FileSystemOperator(object):
	
	def __init__(self, event_handler, server_com):
		self.event_handler = event_handler
		self.server_com = server_com

	def send_lock(self, path):
		self.event_handler.path_ignored = path

	def send_unlock(self):
		self.event_handler.path_ignored = None

	def write_a_file(self, path):
		"""
		write a file (download if exist or not [get and put])

			send lock to watchdog
			download the file from server
			create directory chain
			create file
			send unlock to watchdog
		"""
		full_path = self.server_com.get_fullpath(path)
		self.send_lock(full_path)
		fullpath, content = self.server_com.download_file(path)
		try:
			os.makedirs(os.path.split(fullpath)[0], 0755 )
		except OSError:
			pass
		with open(fullpath, 'w') as f:
			f.write(content)
		time.sleep(3)
		self.send_unlock()

	def move_a_file(self, origin_path, dst_path):
		""" 
		move a file 

			send lock to watchdog
			create directory chain for dst_path
			move the file from origin_path to dst_path
			send unlock to watchdog
		"""
		self.send_lock(origin_path)
		try:
			os.makedirs(os.path.split(dst_path)[0], 0755 )
		except OSError:
			pass
		shutil.move(origin_path, dst_path)
		self.send_unlock()

	def copy_a_file(self, origin_path, dst_path):
		""" copy a file 

			send lock to watchdog
			create directory chain for dst_path
			copy the file from origin_path to dst_path
			send unlock to watchdog
		"""
		self.send_lock(origin_path)
		try:
			os.makedirs(os.path.split(dst_path)[0], 0755 )
		except OSError:
			pass
		shutil.copyfile(origin_path, dst_path)
		self.send_unlock()

	def delete_a_file(self, path):
		""" 
		delete a file 
			send lock to watchdog
			delete file
			send unlock to watchdog
		"""
		self.send_lock(origin_path)
		try:
			shutil.rmtree(path)
		except IOError:
			pass
		self.send_unlock

def load_config():
	with open('config.json', 'r') as config_file:
		config = json.load(config_file)
	return config


class DirectoryEventHandler(FileSystemEventHandler):

	def __init__(self, cmd):
		self.cmd = cmd
		self.path_ignored = None
		
	def on_moved(self, event):
		"""Called when a file or a directory is moved or renamed.

		:param event:
			Event representing file/directory movement.
		:type event:
			:class:`DirMovedEvent` or :class:`FileMovedEvent`
		"""
		if self.path_ignored != event.src_path:
			self.cmd.delete_file(event.src_path)
			self.cmd.upload_file(event.dest_path)
		else:
			print "ingnored move on ", event.src_path

	def on_created(self, event):
		"""Called when a file or directory is created.

		:param event:
			Event representing file/directory creation.
		:type event:
			:class:`DirCreatedEvent` or :class:`FileCreatedEvent`
		"""
		if self.path_ignored != event.src_path:
			self.cmd.upload_file(event.src_path)
		else:
			print "ingnored create on ", event.src_path

	def on_deleted(self, event):
		"""Called when a file or directory is deleted.

		:param event:
			Event representing file/directory deletion.
		:type event:
			:class:`DirDeletedEvent` or :class:`FileDeletedEvent`
		"""
		if self.path_ignored != event.src_path:
			self.cmd.delete_file(event.src_path)
		else:
			print "ingnored deletion on ", event.src_path

	def on_modified(self, event):
		"""Called when a file or directory is modified.

		:param event:
			Event representing file/directory modification.
		:type event:
			:class:`DirModifiedEvent` or :class:`FileModifiedEvent`
		"""
		print self.path_ignored,event.src_path
		if self.path_ignored != event.src_path:
			if not event.is_directory:
				self.cmd.upload_file(event.src_path, put_file = True)
		else:
			print "ingnored modified on ", event.src_path




def main():
	config = load_config()

	server_com = ServerCommunicator(
		server_url = config['server_url'], 
		username = config['username'],
		password = config['password'],
		dir_path = config['dir_path'])


	event_handler = DirectoryEventHandler(server_com)
	file_system_op = FileSystemOperator(event_handler, server_com)
	observer = Observer()
	observer.schedule(event_handler, config['dir_path'], recursive=True)

	observer.start()
	#server_com.create_user("usernameFarlocco", "passwordSegretissima")
	#file_system_op.write_a_file('pippo/pippo/pluto/bla.txt') #test
	#server_com.upload_file("/home/user/prove/bho/ciao.js")

	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		observer.stop()
	observer.join()

if __name__ == '__main__':
	main()
