#!/usr/bin/env python
#-*- coding: utf-8 -*-


# inotify observer unable to detect 'dragging file to trash' events
# from https://github.com/gorakhargosh/watchdog/issues/46 use polling solution

# from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
from requests.auth import HTTPBasicAuth
import requests
import hashlib
import shutil
import base64
import time
import json
import os

class ServerCommunicator(object):

    def __init__(self, server_url, username, password, dir_path):
        self.auth = HTTPBasicAuth(username, password)
        self.server_url = server_url
        self.dir_path = dir_path
        self.timestamp = None   #timestamp for Synchronization
        try:
            with open('timestamp.json', 'r') as timestamp_file:
                self.timestamp = timestamp_file.load()[0]
        except IOError:
            print "There's no timestamp saved."

    def _try_request(self, callback, success = '', error = '',retry_delay = 2, *args, **kwargs):
        """ try a request until it's a success """
        while True:
            try:
                request_result = callback(
                    auth = self.auth,
                    *args, **kwargs)
                print success
                return request_result
            except requests.exceptions.RequestException:
                time.sleep(retry_delay)
                print error

    def synchronize(self, operation_handler):
        """Synchronize client and server"""

        server_url = "{}/files".format(self.server_url)
        request = {"url": server_url}
        sync = self._try_request(requests.get, "Success", "Fail", **request)
        with open("timestamp.json", "w") as timestamp_file:
            timestamp_file.dump(sync.text.load()[0])
        diffs = diff_snapshots(sync.text)
        for tstamp, obj in diffs.iteritems():
            req = obj[0]
            args = obj[1]
            {
                'req_get': operation_handler.write_a_file,
                'req_delete': operation_handler.delete_a_file,
                'req_move': operation_handler.move_a_file,
                'req_copy': operation_handler.copy_a_file
            }.get(req)(args)

    def get_abspath(self, dst_path):
        """ from relative path return absolute path """
        return os.path.join(self.dir_path, dst_path)

    def get_relpath(self, abs_path):
        """form absolute path return relative path """
        return abs_path[len(self.dir_path) + 1:]

    def get_url_relpath(self, abs_path):
        """ form get_abspath return the relative path for url """
        return self.get_relpath(abs_path).replace(os.path.sep, '/')

    def download_file(self, dst_path):
        """ download a file from server"""

        error_log = "ERROR on download request " + dst_path
        success_log = "file downloaded! " + dst_path

        server_url = "{}/files/{}".format(
            self.server_url, 
            self.get_url_relpath(dst_path))

        request = {"url": server_url}
        
        r = self._try_request(requests.get, success_log, error_log, **request)
        local_path = self.get_abspath(dst_path)
        return local_path, r.text
    

    def upload_file(self, dst_path, put_file = False):
        """ upload a file to server """

        file_content = ''
        try:
            file_content = open(dst_path, 'rb')
        except IOError:
            return False #Atomic create and delete error!

        server_url = "{}/files/{}".format(
            self.server_url, 
            self.get_url_relpath(dst_path))

        error_log = "ERROR upload request " + dst_path
        success_log = "file uploaded! " + dst_path
        request = {
            "url": server_url,
            "files": {'file_content':file_content}
        }

        if put_file:
            self._try_request(requests.put, success_log, error_log, **request)
        else:
            self._try_request(requests.post, success_log, error_log, **request)

    def delete_file(self, dst_path):
        """ send to server a message of file delete """

        error_log = "ERROR delete request " + dst_path
        success_log = "file deleted! " + dst_path

        server_url = "{}/actions/delete".format(self.server_url)

        request = {
            "url": server_url,
            "data": self.get_url_relpath(dst_path)
        }

        self._try_request(requests.post, success_log, error_log, **request)

    def move_file(self, src_path, dst_path):
        """ send to server a message of file moved """
        
        error_log = "ERROR move request " + dst_path
        success_log = "file moved! " + dst_path

        server_url = "{}/actions/move".format(self.server_url)
        src_path = self.get_url_relpath(src_path)
        dst_path = self.get_url_relpath(dst_path)

        request = {
            "url": server_url,
            "data": {"src": src_path, "dst": dst_path}
        }
        self._try_request(requests.post, success_log, error_log, **request)

    def copy_file(self, src_path, dst_path):
        """ send to server a message of copy file"""

        error_log = "ERROR copy request " + dst_path
        success_log = "file copied! " + dst_path

        server_url = "{}/actions/copy".format(self.server_url)
        src_path = self.get_url_relpath(src_path)
        dst_path = self.get_url_relpath(dst_path)

        request = {
            "url": server_url,
            "data": {"src": src_path, "dst": dst_path}
        }
        self._try_request(requests.post, success_log, error_log, **request)

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
        self._try_request(requests.post, success_log, error_log, **request)

class FileSystemOperator(object):
    
    def __init__(self, event_handler, server_com):
        self.event_handler = event_handler
        self.server_com = server_com

    def send_lock(self, path):
        self.event_handler.path_ignored.append(path)

    def send_unlock(self):
        self.event_handler.path_ignored = []

    def write_a_file(self, path):
        """
        write a file (download if exist or not [get and put])

            send lock to watchdog
            download the file from server
            create directory chain
            create file
            send unlock to watchdog
        """
        self.send_lock(self.server_com.get_abspath(path))
        abs_path, content = self.server_com.download_file(path)
        try:
            os.makedirs(os.path.split(abs_path)[0], 0755 )
        except OSError:
            pass
        with open(abs_path, 'w') as f:
            f.write(content)
        time.sleep(3)
        self.send_unlock()

    def move_a_file(self, origin_path, dst_path):
        """ 
        move a file 

            send lock to watchdog for origin and dst path
            create directory chain for dst_path
            move the file from origin_path to dst_path
            send unlock to watchdog
        """
        self.send_lock(self.server_com.get_abspath(origin_path))
        self.send_lock(self.server_com.get_abspath(dst_path))
        try:
            os.makedirs(os.path.split(dst_path)[0], 0755 )
        except OSError:
            pass
        shutil.move(origin_path, dst_path)
        self.send_unlock()

    def copy_a_file(self, origin_path, dst_path):
        """ copy a file 

            send lock to watchdog for origin and dest path
            create directory chain for dst_path
            copy the file from origin_path to dst_path
            send unlock to watchdog
        """
        self.send_lock(self.server_com.get_abspath(origin_path))
        self.send_lock(self.server_com.get_abspath(dst_path))
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
        self.send_lock(self.server_com.get_abspath(path))
        try:
            shutil.rmtree(path)
        except IOError:
            pass
        self.send_unlock()

def load_config():
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
    return config


class DirectoryEventHandler(FileSystemEventHandler):

    def __init__(self, cmd, snap):
        self.cmd = cmd
        self.snap = snap
        self.path_ignored = []
        
    def _is_copy(self, abs_path):
        """ 
        check if a file_md5 already exists in my local snapshot 
        IF IS A COPY : return the first path of already exists file
        ELSE: return False
        """
        file_md5 = self.snap.file_snapMd5(abs_path)
        if file_md5 in self.snap.snapshot:
            return self.snap.snapshot[file_md5][0]
        return False

    def on_moved(self, event):
        """Called when a file or a directory is moved or renamed.

        :param event:
            Event representing file/directory movement.
        :type event:
            :class:`DirMovedEvent` or :class:`FileMovedEvent`
        """
        if event.src_path not in self.path_ignored:
            self.cmd.move_file(event.src_path)
        else:
            print "ingnored move on ", event.src_path

    def on_created(self, event):
        """Called when a file or directory is created.

        :param event:
            Event representing file/directory creation.
        :type event:
            :class:`DirCreatedEvent` or :class:`FileCreatedEvent`
        """
       
        if event.src_path not in self.path_ignored:
            copy = self._is_copy(event.src_path)
            if copy:
                self.cmd.copy_file(copy, event.src_path)
            else:
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
        if event.src_path not in self.path_ignored:
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
        
        if event.src_path not in self.path_ignored:
            if not event.is_directory:
                self.cmd.upload_file(event.src_path, put_file = True)
        else:
            print "ingnored modified on ", event.src_path


class DirSnapshotManager(object):
    def __init__(self, dir_path, snapshot_file):
        self.dir_path = dir_path
        self.snapshot_file = snapshot_file
        self.snapshot = self._load_snapshot()
        diff = self.diff_snapthot(self.instant_snapshot())

    def _load_snapshot(self):
        """ load from file the last snapshot """
        with open(self.snapshot_file) as f:
            return json.load(f)

    def file_snapMd5(self, file_path):
        file_md5 = hashlib.md5()
        with open(file_path, 'rb') as afile:
            buf = afile.read(2048)
            while len(buf) > 0:
                file_md5.update(buf)
                buf = afile.read(2048)
        return file_md5.hexdigest()

    def instant_snapshot(self):
        """ create a snapshot of directory """

        dir_snapshot = {}
        for root, dirs, files in os.walk(self.dir_path):
            for f in files:
                full_path = os.path.join(root, f)
                file_md5 = self.file_snapMd5(full_path)
                if file_md5 in dir_snapshot:
                    dir_snapshot[file_md5].append(full_path)
                else:
                    dir_snapshot[file_md5] = [full_path]
        return dir_snapshot

    def _save_snapshot(self):
        with open(self.snapshot_file, 'w') as f:
            f.write(json.dumps(self.snapshot))

    def diff_snapthot(self, server_snapshot):
        """ return the list of conflict """
        return "diff_list"


def main():
    config = load_config()
    snapshot_manager = DirSnapshotManager(config['dir_path'], config['snapshot_file'])

    server_com = ServerCommunicator(
        server_url = config['server_url'], 
        username = config['username'],
        password = config['password'],
        dir_path = config['dir_path'])

    event_handler = DirectoryEventHandler(server_com, snapshot_manager)
    file_system_op = FileSystemOperator(event_handler, server_com)
    observer = Observer()
    observer.schedule(event_handler, config['dir_path'], recursive=True)

    observer.start()
    #server_com.create_user("usernameFarlocco", "passwordSegretissima")
    #file_system_op.write_a_file('pippo/pippo/pluto/bla.txt') #test
    #server_com.upload_file("/home/user/prove/bho/ciao.js")

    try:
        while True:
            #server_com.synchronize(file_system_op)
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    main()
