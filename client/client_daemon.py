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
	return requests.post(*args, **kwargs)

def req_get(*args, **kwargs):
	return requests.get(*args, **kwargs)

def req_put(*args, **kwargs):
	return requests.put(*args, **kwargs)

def req_delete(*args, **kwargs):
	return requests.delete(*args, **kwargs)



class ServerCommunicator(object):

	def __init__(self, server_url, username, password, dir_path):
		self.auth = HTTPBasicAuth(username, password)
		self.server_url = server_url
		self.dir_path = dir_path
		self.retry_delay = 2 
		self.timestamp = None 	#timestamp for Synchronization
		try:
			with open('timestamp.json', 'r') as timestamp_file:
				self.timestamp = timestamp_file.load()[0]
		except IOError:
			print "There's no timestamp saved."

	def _try_request(self, callback, success = '', error = '', *args, **kwargs):
		""" try a request until it's a success """
		while True:
			try:
				request_result = callback(*args, **kwargs)
				print success
				return request_result
			except requests.exceptions.RequestException:
				time.sleep(self.retry_delay)
				print error

	def synchronize(self):
		""" 
		Requests if client is synchronized with server with a continuous iteration
		If client isn't synchronized, the server answers with a json object containing
		a series of timestamp, path and type of request.
		If client is synchronized, the server answers with code 204.
		"""

		server_url = "{}/diffs".format(self.server_url)
		request_sync = {
			"url": server_url,
			"data": self.timestamp,
			"auth": self.auth
		}
		sync = self._try_request(req_get, success_log, error_log, **request_sync) 	
		if sync.status_code != 204:
			diffs = json.load(sync.text)
			for tstamp, obj in diffs.iteritems():
				self.timestamp = tstamp #update self timestamp
				req = obj[0]
				args = obj[1]
				{
					'req_get': self.operator.write_a_file,
					'req_delete': self.operator._delete_a_file,
					'req_move': self.operator.move_a_file,
					'req_copy': self.operator.copy_a_file
				}.get(req)(args)	


	def download_file(self, dst_path):
		""" download a file from server"""

		error_log = "ERROR on download request " + dst_path
		success_log = "file downloaded! " + dst_path

		server_url = "{}/files/{}".format(self.server_url, dst_path)

		request = {
			"url": server_url,
			"data": self.timestamp, #TODO
			"auth": self.auth
		}

		r = self._try_request(req_get, success_log, error_log, **request)
		
		local_path = os.path.join(self.dir_path, dst_path)

		#create a directory chain without file name
		os.makedirs(local_path[-1], 0755 )
		#create a downloaded file
		with open(local_path, 'w') as f:
			f.write(r.text)

	def upload_file(self, dst_path, put_file = False):
		""" upload a file to server """

		file_name = dst_path.split(os.path.sep)[-1]
		path = os.path.join(*(dst_path.split(os.path.sep)[0:-1]))
		file_content = ''
		
		try:
			with open(dst_path, 'r') as f:
				file_content =  f.read()
		except IOError:
			return False #Atomic create and delete error!

		upload = {
					'file_name': file_name,
					'file_content': file_content
				 }

		server_url = "{}/files/{}".format(self.server_url, path)

		error_log = "ERROR upload request " + dst_path
		success_log = "file uploaded! " + dst_path
		
		request = {
			"url": server_url,
			"data": upload,
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

	def move_file(self, src_path, dst_path):
		pass

	def copy_file(self, dst_path):
		pass

	def create_user(self, username, password):
		
		error_log = "User creation error"
		success_log = "user created!" 

		server_url = "{}/create_user".format(self.server_url)

		request = {
			"url": server_url,
			"data":{
					"user": username,
					"psw": password
			}
		}
		
		self._try_request(req_post, success_log, error_log, **request)

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
		self.cmd.delete_file(event.src_path)
		self.cmd.upload_file(event.dest_path)

	def on_created(self, event):
		"""Called when a file or directory is created.

		:param event:
			Event representing file/directory creation.
		:type event:
			:class:`DirCreatedEvent` or :class:`FileCreatedEvent`
		"""
		self.cmd.upload_file(event.src_path)

	def on_deleted(self, event):
		"""Called when a file or directory is deleted.

		:param event:
			Event representing file/directory deletion.
		:type event:
			:class:`DirDeletedEvent` or :class:`FileDeletedEvent`
		"""
		self.cmd.delete_file(event.src_path)

	def on_modified(self, event):
		"""Called when a file or directory is modified.

		:param event:
			Event representing file/directory modification.
		:type event:
			:class:`DirModifiedEvent` or :class:`FileModifiedEvent`
		"""
		if not event.is_directory:
			self.cmd.upload_file(event.src_path, put_file = True)




def main():
	config = load_config()

	server_com = ServerCommunicator(
		server_url = config['server_url'], 
		username = config['username'],
		password = config['password'],
		dir_path = config['dir_path'])


	#server_com.create_user("usernameFarlocco", "passwordSegretissima")
	server_com.download_file('bla.txt')

	event_handler = DirectoryEventHandler(server_com)
	observer = Observer()
	observer.schedule(event_handler, config['dir_path'], recursive=True)
	observer.start()

	try:
		while True:
			server_com.synchronize()
			time.sleep(1)
	except KeyboardInterrupt:
		observer.stop()
	observer.join()


if __name__ == '__main__':
	main()
