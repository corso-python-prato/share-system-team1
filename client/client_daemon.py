#!/usr/bin/env python
#-*- coding: utf-8 -*-


# inotify observer unable to detect 'dragging file to trash' events
# from https://github.com/gorakhargosh/watchdog/issues/46 use polling solution

# from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
from requests.auth import HTTPBasicAuth
import ConfigParser
import requests
import argparse
import hashlib
import logging
import shutil
import time
import json
import os

from communication_system import CmdMessageServer
import asyncore

SERVER_URL = "localhost"
SERVER_PORT = "5000"
API_PREFIX = "API/v1"
CONFIG_DIR_PATH = ""
FILE_CONFIG = "config.ini"

logger = logging.getLogger('RawBox')
logger.setLevel(logging.DEBUG)


def get_relpath(abs_path):
    """form absolute path return relative path """
    if abs_path.startswith(CONFIG_DIR_PATH):
        return abs_path[len(CONFIG_DIR_PATH) + 1:]
    return abs_path


def get_abspath(rel_path):
    """form relative path return relative absolute """
    if not rel_path.startswith(CONFIG_DIR_PATH):
        return "/".join([CONFIG_DIR_PATH, rel_path])
    return rel_path


class ServerCommunicator(object):

    def __init__(self, server_url, username, password, snapshot_manager):
        if username and password:
            self.auth = HTTPBasicAuth(username, password)
        else:
            self.auth = None
        self.server_url = server_url
        self.snapshot_manager = snapshot_manager
        self.msg = {
            "result": "",
            "details": []
        }

    def write_user_data(self, user=None, psw=None, activate=False):
        config_ini = ConfigParser.ConfigParser()
        config_ini.read(FILE_CONFIG)
        if not activate:
            config_ini.set("daemon_user_data", "username", user)
            config_ini.set("daemon_user_data", "password", psw)

        else:
            config_ini.set("daemon_user_data", "active", True)
        with open(FILE_CONFIG, "wb") as config_file:
            config_ini.write(config_file)

    def setExecuter(self, executer):
        self.executer = executer

    def _try_request(self, callback, success='', error='', retry_delay=2, *args, **kwargs):
        """ try a request until it's a success """
        while True:
            try:
                request_result = callback(
                    auth=self.auth,
                    *args, **kwargs
                )
                if request_result.ok:
                    logger.info(success)
                else:
                    logger.error(request_result.reason)
                return request_result

            except requests.exceptions.RequestException:
                time.sleep(retry_delay)
                logger.warning(error)

    def synchronize(self, operation_handler):
        """Synchronize client and server"""

        server_url = "{}/files/".format(self.server_url)
        request = {"url": server_url}
        sync = self._try_request(
            requests.get, "getFile success", "getFile fail", **request)

        if sync.status_code != 401:
            server_snapshot = sync.json()['snapshot']

            server_timestamp = float(sync.json()['timestamp'])
            logger.debug("".format("SERVER SAY: ", server_snapshot, server_timestamp, "\n"))
            command_list = self.snapshot_manager.syncronize_dispatcher(server_timestamp, server_snapshot)
            self.executer.syncronize_executer(command_list)
            self.snapshot_manager.save_timestamp(server_timestamp)

    def get_url_relpath(self, abs_path):
        """ form get_abspath return the relative path for url """
        return get_relpath(abs_path).replace(os.path.sep, '/')

    def download_file(self, dst_path):
        """ download a file from server"""
        error_log = "ERROR on download request " + dst_path
        success_log = "file downloaded! " + dst_path

        server_url = "{}/files/{}".format(
            self.server_url,
            self.get_url_relpath(dst_path))

        request = {"url": server_url}

        r = self._try_request(requests.get, success_log, error_log, **request)
        local_path = get_abspath(dst_path)

        if r.status_code == 200:
            return local_path, r.text
        else:
            return False, False

    def upload_file(self, dst_path, put_file=False):
        """ upload a file to server """

        file_object = ''
        try:
            file_object = open(get_abspath(dst_path), 'rb')
            file_content = open(get_abspath(dst_path), 'rb').read()
        except IOError:
            return False  # Atomic create and delete error!

        server_url = "{}/files/{}".format(
            self.server_url,
            self.get_url_relpath(dst_path))

        error_log = "ERROR upload request " + dst_path
        success_log = "file uploaded! " + dst_path
        request = {
            "url": server_url,
            "files": {'file_content': file_object},
            "data": {'file_md5': hashlib.md5(file_content).hexdigest()}
        }

        if put_file:
            r = self._try_request(
                requests.put, success_log, error_log, **request)
        else:
            r = self._try_request(
                requests.post, success_log, error_log, **request)
        if r.status_code == 409:
            logger.error("file {} already exists on server".format(dst_path))
        elif r.status_code == 201:
            if put_file:
                self.snapshot_manager.update_snapshot_update({"src_path": dst_path})
            else:
                self.snapshot_manager.update_snapshot_upload({"src_path": dst_path})
            self.snapshot_manager.save_snapshot(r.text)

    def delete_file(self, dst_path):
        """ send to server a message of file delete """

        error_log = "ERROR delete request " + dst_path
        success_log = "file deleted! " + dst_path

        server_url = "{}/actions/delete".format(self.server_url)
        request = {
            "url": server_url,
            "data": {"path": self.get_url_relpath(dst_path)}
        }
        r = self._try_request(requests.post, success_log, error_log, **request)
        if r.status_code == 404:
            logger.error("DELETE REQUEST file {} not found on server".format(dst_path))
        elif r.status_code == 200:
            self.snapshot_manager.update_snapshot_delete({"src_path": dst_path})
            self.snapshot_manager.save_snapshot(r.text)

    def move_file(self, src_path, dst_path):
        """ send to server a message of file moved """

        error_log = "ERROR move request " + dst_path
        success_log = "file moved! " + dst_path

        server_url = "{}/actions/move".format(self.server_url)
        request = {
            "url": server_url,
            "data": {
                "file_src": self.get_url_relpath(src_path),
                "file_dest": self.get_url_relpath(dst_path),
            }
        }

        r = self._try_request(requests.post, success_log, error_log, **request)
        if r.status_code == 404:
            logger.error("MOVE REQUEST file {} not found on server".format(src_path))
        elif r.status_code == 201:
            self.snapshot_manager.update_snapshot_move({"src_path": src_path, "dst_path": dst_path})
            self.snapshot_manager.save_snapshot(r.text)

    def copy_file(self, src_path, dst_path):
        """ send to server a message of copy file"""

        error_log = "ERROR copy request " + dst_path
        success_log = "file copied! " + dst_path

        server_url = "{}/actions/copy".format(self.server_url)

        request = {
            "url": server_url,
            "data": {
                "file_src": self.get_url_relpath(src_path),
                "file_dest": self.get_url_relpath(dst_path),
            }
        }
        r = self._try_request(requests.post, success_log, error_log, **request)
        if r.status_code == 404:
            logger.error("COPY REQUEST file {} not found on server".format(src_path))
        elif r.status_code == 201:
            self.snapshot_manager.update_snapshot_copy({"src_path": src_path, "dst_path": dst_path})
            self.snapshot_manager.save_snapshot(r.text)

    def create_user(self, param):

        self.msg["details"] = []
        error_log = "User creation error"
        success_log = "user created!"
        username = param["user"]
        password = param["psw"]

        server_url = "{}/Users/{}".format(self.server_url, param["user"])

        request = {
            "url": server_url,
            "data": {
                "psw": param["psw"]
            }
        }

        response = self._try_request(
            requests.post, success_log, error_log, **request)

        self.msg["result"] = response.status_code

        if response.status_code == 201:
            self.msg["details"].append(
                "Check your email for the activation code")
            logger.info("user: {} psw: {} created!".format(username, password))
            self.write_user_data(param["user"], param["psw"], activate=False)
        elif response.status_code == 409:
            logger.warning("user: {} psw: {} already exists!".format(username, password))
            self.msg["details"].append("User already exists")
        else:
            error = "on create user:\t email: {}\n\nsend message:\t{}\nresponse is:\t{}".format(username, request, response.text)
            logger.critical("\nbad request on user creation, report this crash to RawBox_team@gmail.com\n {}\n\n".format(error))
            self.msg["details"].append("Bad request")
        return self.msg

    def get_user(self, param):

        self.msg["details"] = []
        error_log = "cannot get user data"
        success_log = "user data retrived"

        server_url = "{}/user".format(self.server_url)

        request = {
            "url": server_url,
            "data": {
                "user": param["user"],
                "psw": param["psw"]
            }
        }

        response = self._try_request(
            requests.get, success_log, error_log, **request)

        self.msg["result"] = response.status_code
        self.msg["details"].append(eval(response.text))

        if response.status_code == 200:
            self.msg["details"].append("User data retrived")
        elif response.status_code == 404:
            self.msg["details"].append("User not found")
        else:
            self.msg["details"].append("Bad request")

        return self.msg

    def delete_user(self, param):

        self.msg["details"] = []
        error_log = "Cannot delete user"
        success_log = "Usere deleted"

        server_url = "{}/Users/{}".format(self.server_url, param["user"])

        request = {
            "url": server_url,
            "data": {}
        }

        response = self._try_request(
            requests.delete, success_log, error_log, **request)

        self.msg["result"] = response.status_code

        if response.status_code == 200:
            self.msg["details"].append("User deleted")
        elif response.status_code == 401:
            self.msg["details"].append("Access denied")
        else:
            self.msg["details"].append("Bad request")

        return self.msg

    def activate_user(self, param):

        self.msg["details"] = []
        error_log = "Cannot activate user"
        success_log = "User activated"

        server_url = "{}/Users/{}".format(self.server_url, param["user"])

        request = {
            "url": server_url,
            "data": {
                "code": param["code"]
            }
        }

        response = self._try_request(
            requests.put, success_log, error_log, **request)

        self.msg["result"] = response.status_code

        if response.status_code == 201:
            self.write_user_data(activate=True)
            self.msg["details"].append("You have now entered RawBox")
        elif response.status_code == 404:
            self.msg["details"].append("User not found")
        else:
            self.msg["details"].append("Bad request")

        return self.msg

    def add_share(self, param):
        """ Called by cmdmanager.
        Share a resource with a beneficiary """
        self.msg["details"] = []
        request = {
            "url": "{}/shares/{}/{}".format(
                self.server_url, param["path"], param["ben"]
            )
        }
        
        success_log = "share added with {}!".format(param["ben"])
        error_log = "ERROR in adding a share with {}".format(param["ben"])

        
        r = self._try_request(requests.post, success_log, error_log, **request)

        self.msg["result"] = r.status_code
        
        if r.status_code == 400:
            self.msg["details"].append("Bad request")
        elif r.status_code == 201:
            self.msg["details"].append("Added share!")
        return self.msg

    def remove_share(self, param):
        """Remove all the share"""
        self.msg["details"] = []
        request = {
            "url" : "{}/share/{}".format(self.server_url,
                param["path"]),
            "data" : {}
        }

        success_log = "The resource is no more shared"
        error_log = "ERROR on removing all the shares"

        response = self._try_request(requests.delete, success_log,
            error_log, **request)

        self.msg["result"] = response.status_code

        if response.status_code == 200:
            self.msg["details"].append("Shares removed")
        elif response.status_code == 400:
            self.msg["details"].append("Error, shares not removed")

        return self.msg

    def remove_beneficiary(self, param):
        """Remove user from share"""
        self.msg["details"] = []
        request = {
            "url" : "{}/share/{}/{}".format(self.server_url,
                param["path"], param["ben"]),
            "data" : {}
        }

        success_log = "Removed user {} from shares".format(param["ben"])
        error_log = "ERROR on removing user {} from shares".format(param["ben"])

        response = self._try_request(requests.delete, success_log,
            error_log, **request)

        self.msg["result"] = response.status_code

        if response.status_code == 200:
            self.msg["details"].append("User removed from sahres")
        elif response.status_code == 400:
            self.msg["details"].append("Cannot remove user from shares")

        return self.msg


class FileSystemOperator(object):

    def __init__(self, event_handler, server_com, snapshot_manager):
        self.snapshot_manager = snapshot_manager
        self.event_handler = event_handler
        self.server_com = server_com

    def add_event_to_ignore(self, path):
        self.event_handler.paths_ignored.append(path)

    def write_a_file(self, path):
        """
        write a file (download if exist or not [get and put])

            send a path to ignore to watchdog
            download the file from server
            create directory chain
            create file
            when watchdog see the first event on this path ignore it
        """
        abs_path, content = self.server_com.download_file(path)
        if abs_path and content:
            self.add_event_to_ignore(get_abspath(path))
            try:
                os.makedirs(os.path.split(abs_path)[0], 0755)
            except OSError:
                pass
            with open(abs_path, 'wb') as f:
                f.write(content)
            self.snapshot_manager.update_snapshot_upload({"src_path": get_abspath(abs_path)})
        else:
            logger.error("DOWNLOAD REQUEST for file {} , not found on server".format(path))

    def move_a_file(self, origin_path, dst_path):
        """
        move a file

            send a path to ignore to watchdog for origin and dst path
            create directory chain for dst_path
            move the file from origin_path to dst_path
            when watchdog see the first event on this path ignore it
        """
        self.add_event_to_ignore(get_abspath(origin_path))
        self.add_event_to_ignore(get_abspath(dst_path))
        try:
            os.makedirs(os.path.split(dst_path)[0], 0755)
        except OSError:
            pass
        shutil.move(origin_path, dst_path)
        self.snapshot_manager.update_snapshot_move({"src_path": get_abspath(origin_path), "dst_path": get_abspath(dst_path)})

    def copy_a_file(self, origin_path, dst_path):
        """
        copy a file

            send a path to ignore to watchdog for dest path (because copy is a creation event)
            create directory chain for dst_path
            copy the file from origin_path to dst_path
            when watchdog see the first event on this path ignore it
        """
        self.add_event_to_ignore(get_abspath(dst_path))
        origin_path = get_abspath(origin_path)
        dst_path = get_abspath(dst_path)
        try:
            os.makedirs(os.path.split(dst_path)[0], 0755)
        except OSError:
            pass
        shutil.copyfile(origin_path, dst_path)
        self.snapshot_manager.update_snapshot_copy({"src_path": get_abspath(origin_path), "dst_path": get_abspath(dst_path)})

    def delete_a_file(self, dst_path):
        """
        delete a file

            send a dst_path to ignore to watchdog
            delete file
            when watchdog see the first event on this dst_path ignore it
        """
        self.add_event_to_ignore(get_abspath(dst_path))
        dst_path = get_abspath(dst_path)
        if os.path.isdir(dst_path):
            shutil.rmtree(dst_path)
        else:
            try:
                os.remove(dst_path)
            except OSError:
                pass
        self.snapshot_manager.update_snapshot_delete({"src_path": get_abspath(dst_path)})


def load_config():

    abs_path = os.path.dirname(os.path.abspath(__file__))
    crash_log_path = os.path.join(abs_path, 'RawBox_crash_report.log')
    config_ini = ConfigParser.ConfigParser()
    config_ini.read(FILE_CONFIG)
    user_exists = True
    config = None

    try:
        config = {
            "host": config_ini.get('cmd', 'host'),
            "port": config_ini.get('cmd', 'port'),
            "server_url": "http://{}:{}/{}".format(
                config_ini.get('daemon_communication', 'server_url'),
                config_ini.get('daemon_communication', 'server_port'),
                config_ini.get('daemon_communication', 'api_prefix'),
            ),

            "crash_repo_path": config_ini.get('daemon_communication', 'crash_repo_path'),
            "stdout_log_level": config_ini.get('daemon_communication', 'stdout_log_level'),
            "file_log_level": config_ini.get('daemon_communication', 'file_log_level'),
            "dir_path": config_ini.get('daemon_communication', 'dir_path'),
            "snapshot_file_path": config_ini.get('daemon_communication', 'snapshot_file_path')
        }
    except ConfigParser.NoSectionError:
        dir_path = os.path.join(os.path.expanduser("~"), "RawBox")
        config_ini.add_section('daemon_communication')
        config_ini.set('daemon_communication', 'snapshot_file_path', 'snapshot_file.json')
        config_ini.set('daemon_communication', 'dir_path', dir_path)
        config_ini.set('daemon_communication', 'server_url', SERVER_URL)
        config_ini.set('daemon_communication', 'server_port', SERVER_PORT)
        config_ini.set('daemon_communication', 'api_prefix', API_PREFIX)
        config_ini.set('daemon_communication', 'crash_repo_path', crash_log_path)
        config_ini.set('daemon_communication', 'stdout_log_level', "DEBUG")
        config_ini.set('daemon_communication', 'file_log_level', "ERROR")

        snapshot_file = config_ini.get('daemon_communication', 'snapshot_file_path')
        config = {
            "host": config_ini.get('cmd', 'host'),
            "port": config_ini.get('cmd', 'port'),
            "server_url": "http://{}:{}/{}".format(
                config_ini.get('daemon_communication', 'server_url'),
                config_ini.get('daemon_communication', 'server_port'),
                config_ini.get('daemon_communication', 'api_prefix')
            ),
            "crash_repo_path": config_ini.get('daemon_communication', 'crash_repo_path'),
            "stdout_log_level": config_ini.get('daemon_communication', 'stdout_log_level'),
            "file_log_level": config_ini.get('daemon_communication', 'file_log_level'),
            "dir_path": config_ini.get('daemon_communication', 'dir_path'),
            "snapshot_file_path": snapshot_file
        }
        try:
            os.makedirs(dir_path)
        except OSError:
            pass
        with open(snapshot_file, 'w') as snapshot:
            json.dump({"timestamp": 0, "snapshot": ""}, snapshot)

    try:
        config["username"] = config_ini.get('daemon_user_data', 'username')
        config["password"] = config_ini.get('daemon_user_data', 'password')
        config_ini.get('daemon_user_data', 'active')
    except ConfigParser.NoSectionError:
        user_exists = False
        config_ini.add_section('daemon_user_data')
        config_ini.set('daemon_user_data', 'username')
        config_ini.set('daemon_user_data', 'password')
    except ConfigParser.NoOptionError:
        user_exists = False  # in this case the user is created but not activated

    with open(FILE_CONFIG, 'wb') as config_file:
        config_ini.write(config_file)
    return config, user_exists


class DirectoryEventHandler(FileSystemEventHandler):

    def __init__(self, cmd, snap):
        self.cmd = cmd
        self.snap = snap
        self.paths_ignored = []

    def _is_copy(self, abs_path):
        """
        check if a file_md5 already exists in my local snapshot
        IF IS A COPY : return the first path of already exists file
        ELSE: return False
        """
        file_md5 = self.snap.file_snapMd5(abs_path)
        if not file_md5:
            return False
        if file_md5 in self.snap.local_full_snapshot:
            return self.snap.local_full_snapshot[file_md5][0]
        return False

    def on_moved(self, event):
        """Called when a file or a directory is moved or renamed.

        :param event:
            Event representing file/directory movement.
        :type event:
            :class:`DirMovedEvent` or :class:`FileMovedEvent`
        """
        if event.src_path not in self.paths_ignored:
            if not event.is_directory:
                self.cmd.move_file(event.src_path, event.dest_path)
        else:
            logger.debug("".format("ignored move on ", event.src_path))
            self.paths_ignored.remove(event.src_path)
            self.paths_ignored.remove(event.dest_path)

    def on_created(self, event):
        """Called when a file or directory is created.

        :param event:
            Event representing file/directory creation.
        :type event:
            :class:`DirCreatedEvent` or :class:`FileCreatedEvent`
        """
        copy = False
        if event.src_path not in self.paths_ignored:
            if not event.is_directory:
                copy = self._is_copy(event.src_path)
                if copy:
                    self.cmd.copy_file(copy, event.src_path)
                else:
                    self.cmd.upload_file(event.src_path)
        else:
            if copy:
                logger.debug("".format("ignored copy on ", event.src_path))
            else:
                logger.debug("".format("ignored creation on ", event.src_path))
            self.paths_ignored.remove(event.src_path)

    def on_deleted(self, event):
        """Called when a file or directory is deleted.

        :param event:
            Event representing file/directory deletion.
        :type event:
            :class:`DirDeletedEvent` or :class:`FileDeletedEvent`
        """
        if event.src_path not in self.paths_ignored:
            if not event.is_directory:
                self.cmd.delete_file(event.src_path)
        else:
            logger.debug("".format("ignored deletion on ", event.src_path))
            self.paths_ignored.remove(event.src_path)

    def on_modified(self, event):
        """Called when a file or directory is modified.

        :param event:
            Event representing file/directory modification.
        :type event:
            :class:`DirModifiedEvent` or :class:`FileModifiedEvent`
        """

        if event.src_path not in self.paths_ignored:
            if not event.is_directory:
                self.cmd.upload_file(event.src_path, put_file=True)
        else:
            logger.debug("".format("ignored modified on ", event.src_path))
            self.paths_ignored.remove(event.src_path)


class DirSnapshotManager(object):
    def __init__(self, snapshot_file_path):
        """ load the last global snapshot and create a instant_snapshot of local directory"""
        self.snapshot_file_path = snapshot_file_path
        self.last_status = self._load_status()
        self.local_full_snapshot = self.instant_snapshot()

    def local_check(self):
        """ check id daemon is synchronized with local directory """
        local_global_snapshot = self.global_md5()
        if self.last_status['snapshot'] == "":
            return True
        last_global_snapthot = self.last_status['snapshot']
        return local_global_snapshot == last_global_snapthot

    def is_syncro(self, server_timestamp):
        """ check if daemon timestamp is synchronized with server timestamp"""
        server_timestamp = server_timestamp
        client_timestamp = self.last_status['timestamp']
        return server_timestamp == client_timestamp

    def _load_status(self):
        """ load from file the last snapshot """
        with open(self.snapshot_file_path) as f:
            return json.load(f)

    def file_snapMd5(self, file_path):
        """ calculate the md5 of a file """
        file_path = get_abspath(file_path)
        file_md5 = hashlib.md5()
        if os.path.isdir(file_path):
            return False
        with open(file_path, 'rb') as afile:
            buf = afile.read(2048)
            while len(buf) > 0:
                file_md5.update(buf)
                buf = afile.read(2048)
        return file_md5.hexdigest()

    def global_md5(self):
        """ calculate the global md5 of local_full_snapshot """
        for k, v in self.local_full_snapshot.items():
            v.sort()
        snap_list = sorted(list(self.local_full_snapshot.items()))
        return hashlib.md5(str(snap_list)).hexdigest()

    def instant_snapshot(self):
        """ create a snapshot of directory """

        dir_snapshot = {}
        for root, dirs, files in os.walk(CONFIG_DIR_PATH):
            for f in files:
                full_path = os.path.join(root, f)
                file_md5 = self.file_snapMd5(full_path)
                rel_path = get_relpath(full_path)
                if file_md5 in dir_snapshot:
                    dir_snapshot[file_md5].append(rel_path)
                else:
                    dir_snapshot[file_md5] = [rel_path]
        return dir_snapshot

    def save_snapshot(self, timestamp):
        """ save snapshot to file """
        self.last_status['timestamp'] = timestamp
        self.last_status['snapshot'] = self.global_md5()

        with open(self.snapshot_file_path, 'w') as f:
            f.write(
                json.dumps({"timestamp": timestamp, "snapshot": self.last_status['snapshot']}))

    def update_snapshot_upload(self, body):
        """ update of local full snapshot by upload request"""
        self.local_full_snapshot[self.file_snapMd5(body['src_path'])] = [get_relpath(body["src_path"])]

    def update_snapshot_update(self, body):
        """ update of local full snapshot by update request"""
        #delete the old path from full snapshot
        self.update_snapshot_delete(body)
        new_file_md5 = self.file_snapMd5(body['src_path'])
        if new_file_md5 in self.local_full_snapshot:
            #is a copy of another file
            self.local_full_snapshot[new_file_md5].append(get_relpath(body['src_path']))
        else:
            #else create a new md5
            self.local_full_snapshot[new_file_md5] = [get_relpath(body['src_path'])]

    def update_snapshot_copy(self, body):
        """ update of local full snapshot by copy request"""
        self.local_full_snapshot[self.file_snapMd5(body['src_path'])].append(get_relpath(body["dst_path"]))

    def update_snapshot_move(self, body):
        """ update of local full snapshot by move request"""
        paths_of_file = self.local_full_snapshot[self.file_snapMd5(get_abspath(body["dst_path"]))]
        paths_of_file.remove(get_relpath(body["src_path"]))
        paths_of_file.append(get_relpath(body["dst_path"]))

    def update_snapshot_delete(self, body):
        """ update of local full snapshot by delete request"""
        md5_file = self.find_file_md5(self.local_full_snapshot, get_relpath(body['src_path']), False)
        logger.debug("find md5: " + md5_file)
        if len(self.local_full_snapshot[md5_file]) == 1:
            del self.local_full_snapshot[md5_file]
        else:
            self.local_full_snapshot[md5_file].remove(get_relpath(body['src_path']))
        logger.debug("path deleted: " + get_relpath(body['src_path']))

    def save_timestamp(self, timestamp):
        """
            save timestamp to file only if getfile
            timestamp is < than the last timestamp saved
        """
        if self.last_status['timestamp'] < timestamp:
            self.last_status['timestamp'] = timestamp
            with open(self.snapshot_file_path, 'w') as f:
                f.write(json.dumps(self.last_status, f))

    def diff_snapshot_paths(self, snap_client, snap_server):
        """
            from 2 snapshot return 3 list of path difference:
            list of new server path
            list of new client path
            list of equal path
        """
        client_paths = [val for subl in snap_client.values() for val in subl]
        server_paths = [val['path']
                        for subl in snap_server.values() for val in subl]
        new_server_paths = list(set(server_paths) - set(client_paths))
        new_client_paths = list(set(client_paths) - set(server_paths))
        equal_paths = list(set(client_paths).intersection(set(server_paths)))

        return new_client_paths, new_server_paths, equal_paths

    def find_file_md5(self, snapshot, new_path, is_server=True):
        """ from snapshot and a path find the md5 of file inside snapshot"""
        for md5, paths in snapshot.items():
            for path in paths:
                if is_server:
                    if path['path'] == new_path:
                        return md5
                else:
                    if path == new_path:
                        return md5

    def check_files_timestamp(self, snapshot, new_path):
        paths_timestamps = [val for subl in snapshot.values() for val in subl]
        for path_timestamp in paths_timestamps:
            if path_timestamp['path'] == new_path:
                return path_timestamp['timestamp'] < self.last_status['timestamp']

    def syncronize_dispatcher(self, server_timestamp, server_snapshot):
        """ return the list of command to do """
        new_client_paths, new_server_paths, equal_paths = self.diff_snapshot_paths(
            self.local_full_snapshot, server_snapshot)
        command_list = []
        #NO internal conflict
        if self.local_check():  # 1)
            if not self.is_syncro(server_timestamp):  # 1) b.
                for new_server_path in new_server_paths:  # 1) b 1
                    server_md5 = self.find_file_md5(server_snapshot, new_server_path)
                    if not server_md5 in self.local_full_snapshot:  # 1) b 1 I
                        logger.debug("download:\t" + new_server_path)
                        command_list.append({'local_download': [new_server_path]})
                    else:  # 1) b 1 II
                        logger.debug("copy or rename:\t" + new_server_path)
                        src_local_path = self.local_full_snapshot[server_md5][0]
                        command_list.append({'local_copy': [src_local_path, new_server_path]})

                for equal_path in equal_paths:  # 1) b 2
                    client_md5 = self.find_file_md5(self.local_full_snapshot, equal_path, False)
                    if client_md5 != self.find_file_md5(server_snapshot, equal_path):
                        #in this case i have a simple download because the update is a overwritten
                        logger.debug("update download:\t" + equal_path)
                        command_list.append({'local_download': [equal_path]})
                    else:
                        logger.debug("no action:\t" + equal_path)

                for new_client_path in new_client_paths:  # 1) b 3
                    logger.debug("remove local:\t" + new_client_path)
                    command_list.append({'local_delete': [new_client_path]})
            else:
                logger.debug("synchronized")

        #internal conflicts
        else:  # 2)
            if self.is_syncro(server_timestamp):  # 2) a
                logger.debug("****\tpush all\t****")
                for new_server_path in new_server_paths:  # 2) a 1
                    logger.debug("remove:\t" + new_server_path)
                    command_list.append({'remote_delete': [new_server_path]})
                for equal_path in equal_paths:  # 2) a 2
                    if self.find_file_md5(self.local_full_snapshot, equal_path, False) != self.find_file_md5(server_snapshot, equal_path):
                        logger.debug("update:\t" + equal_path)
                        command_list.append({'remote_update': [equal_path, True]})
                    else:
                        logger.debug("no action:\t" + equal_path)
                for new_client_path in new_client_paths:  # 2) a 3
                    logger.debug("upload:\t" + new_client_path)
                    command_list.append({'remote_upload': [new_client_path]})

            elif not self.is_syncro(server_timestamp):  # 2) b
                for new_server_path in new_server_paths:  # 2) b 1
                    server_md5 = self.find_file_md5(server_snapshot, new_server_path)
                    if self.check_files_timestamp(server_snapshot, new_server_path):
                        logger.debug("delete remote:\t" + new_server_path)
                        command_list.append({'remote_delete': [new_server_path]})
                    else:
                        if not server_md5 in self.local_full_snapshot:  # 2) b 1 I
                                logger.debug("download local:\t" + new_server_path)
                                command_list.append({'local_download': [new_server_path]})
                        else:  # 2) b 1 II
                            logger.debug("copy or rename:\t" + new_server_path)
                            src_local_path = self.local_full_snapshot[server_md5][0]
                            command_list.append({'local_copy': [src_local_path, new_server_path]})

                for equal_path in equal_paths:  # 2) b 2
                    if self.find_file_md5(self.local_full_snapshot, equal_path, False) != self.find_file_md5(server_snapshot, equal_path):
                        if self.check_files_timestamp(server_snapshot, equal_path):  # 2) b 2 I
                            logger.debug("server push:\t" + equal_path)
                            command_list.append({'remote_upload': [equal_path]})
                        else:  # 2) b 2 II
                            logger.debug("create.conflicted:\t" + equal_path)
                            conflicted_path = "{}/{}.conflicted".format(
                                "/".join(equal_path.split('/')[:-1]),
                                "".join(equal_path.split('/')[-1])
                            )
                            command_list.append({'local_copy': [equal_path, conflicted_path]})
                            command_list.append({'remote_upload': [conflicted_path]})
                    else:
                        logger.debug("no action:\t" + equal_path)
                for new_client_path in new_client_paths:  # 2) b 3
                    logger.debug("remove remote\t" + new_client_path)
                    command_list.append({'remote_delete': [new_client_path]})

        return command_list


class CommandExecuter(object):

    """Execute a list of commands"""

    def __init__(self, file_system_op, server_com):
        self.local = file_system_op
        self.remote = server_com

    def syncronize_executer(self, command_list):
        logger.debug("EXECUTER\n")

        def error(*args, **kwargs):
            return False

        logger.debug(command_list)

        for command_row in command_list:
            for command in command_row:
                command_dest = command.split('_')[0]
                command_type = command.split('_')[1]
                if command_dest == 'remote':
                    {
                        'upload': self.remote.upload_file,
                        'update': self.remote.upload_file,
                        'delete': self.remote.delete_file,
                    }.get(command_type, error)(*(command_row[command]))
                else:
                    {
                        'copy': self.local.copy_a_file,
                        'download': self.local.write_a_file,
                        'delete': self.local.delete_a_file,
                    }.get(command_type, error)(*(command_row[command]))


def logger_init(crash_repo_path, stdout_level, file_level, disabled=False):
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    stdout_level = log_levels[stdout_level]
    file_level = log_levels[file_level]

    # create formatter for crash file logging
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    logger = logging.getLogger()

    # create file handler which logs even debug messages
    if crash_repo_path:
        crash_logger = logging.FileHandler(crash_repo_path)
        crash_logger.setLevel(file_level)
        crash_logger.setFormatter(formatter)
        logger.addHandler(crash_logger)
    # create console handler with a low log level
    print_logger = logging.StreamHandler()
    print_logger.setLevel(stdout_level)
    # add the handlers to logger
    logger.addHandler(print_logger)
    if disabled:
        logging.disable(logging.CRITICAL)


def args_parse_init(stdout_level, file_level):
    parser = argparse.ArgumentParser(description='RawBox client daemon', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--std-log-level", required=False, help="set the logging level to std out. this argument accept:\n\tDEBUG\n\tINFO\n\tWARNING\n\tERROR\n\tCRITICAL", default=stdout_level)
    parser.add_argument("--file-log-level", required=False, help="set the logging level to file. this argument accept:\n\tDEBUG\n\tINFO\n\tWARNING\n\tERROR\n\tCRITICAL", default=file_level)
    parser.add_argument("--no-log", action="store_true", required=False, help="disable all log", default=False)
    parser.add_argument("--no-repo", action="store_true", required=False, help="disable the creation of a crash file", default=False)
    args = parser.parse_args()
    return args


def main():

    global CONFIG_DIR_PATH

    config, user_exists = load_config()
    CONFIG_DIR_PATH = config['dir_path']
    args = args_parse_init(
        stdout_level=config['stdout_log_level'],
        file_level=config['file_log_level'],
    )
    report_file = config['crash_repo_path']
    if args.no_repo:
        report_file = False
    logger_init(
        crash_repo_path=report_file,
        stdout_level=args.std_log_level,
        file_level=args.file_log_level,
        disabled=args.no_log,
    )

    snapshot_manager = DirSnapshotManager(
        snapshot_file_path=config['snapshot_file_path'],
    )

    server_com = ServerCommunicator(
        server_url=config['server_url'],
        username=None,
        password=None,
        snapshot_manager=snapshot_manager)

    client_command = {
        "create_user": server_com.create_user,
        "activate_user": server_com.activate_user,
        "delete_user": server_com.delete_user,
        "add_share": server_com.add_share,
        "remove_share": server_com.remove_share,
        "remove_beneficiary": server_com.remove_beneficiary
    }
    sock_server = CmdMessageServer(
        config['host'],
        int(config['port']),
        client_command)

    while not user_exists:
        asyncore.poll(timeout=1.0)
        config, user_exists = load_config()

    server_com.username = config['username']
    server_com.password = config['password']
    server_com.auth = HTTPBasicAuth(server_com.username, server_com.password)

    event_handler = DirectoryEventHandler(server_com, snapshot_manager)
    file_system_op = FileSystemOperator(event_handler, server_com, snapshot_manager)
    executer = CommandExecuter(file_system_op, server_com)
    server_com.setExecuter(executer)
    observer = Observer()
    observer.schedule(event_handler, config['dir_path'], recursive=True)

    observer.start()

    last_synk_time = 0
    try:
        while True:
            asyncore.poll(timeout=5.0)
            if (time.time() - last_synk_time) >= 5.0:
                last_synk_time = time.time()
                server_com.synchronize(file_system_op)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    main()
