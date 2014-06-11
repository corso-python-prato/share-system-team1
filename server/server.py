#!/usr/bin/env python
#-*- coding: utf-8 -*-

from flask import Flask, request
from flask.ext.httpauth import HTTPBasicAuth
from flask.ext.restful import reqparse, abort, Api, Resource
from passlib.hash import sha256_crypt
import time
import datetime
import json
import os
import shutil
import urlparse
from server_errors import *

app = Flask(__name__)
api = Api(app)
auth = HTTPBasicAuth()
USERS_DIRECTORIES = "user_dirs/"
USERS_DATA = "user_data.json"
parser = reqparse.RequestParser()
parser.add_argument("task", type=str)

_API_PREFIX = "/API/v1/"
_URLS = {
    "files" :     "files/<path:path>",
    "actions" :   "actions/<string:cmd>",
    "user" :      "user/<string:cmd>"
}
def init():
    for u in _URLS.keys():
        _URLS[u] = urlparse.urljoin(_API_PREFIX, _URLS.pop(u))

    api.add_resource(UserActions, _URLS["user"])
    api.add_resource(Files, _URLS["files"])
    api.add_resource(Actions, _URLS["actions"])


class Users(object):
    def __init__(self):
        self.load()

    def get_id(self):
        new_id = hex(self.counter_id)[2:]
        self.counter_id += 1    
        return new_id

    def load(self):
        try:
            ud = open(USERS_DATA, "r")
            saved = json.load(ud)
            self.users = saved["users"]
            self.counter_id = saved["counter_id"]
            ud.close()
        except IOError:
            self.users = {}
            # { 
            #     username : { 
            #            psw : encoded_password,
            #            paths : list_of_path
            #     }
            # }
            self.counter_id = 0

    def new_user(self, user, password):
        if user in self.users:
            return "This user already exists", 409

        psw_hash = sha256_crypt.encrypt(password)
        dir_id = self.get_id()
        dir_path = os.path.join(USERS_DIRECTORIES, dir_id)
        try:
            os.mkdir(dir_path)
        except OSError:
            return "The directory already exists", 409
        
        self.users[user] = { 
            "psw": psw_hash,
            "paths" : [dir_id]
        }

        history.set_change("new", dir_id)

        self.save_users()
        return "User created!", 201

    def save_users(self):
        to_save = {
            "counter_id" : self.counter_id,
            "users" : self.users
        }
        with open(USERS_DATA, "w") as ud:
            json.dump(to_save, ud)


class History(object):
    ACTIONS = ["new", "modify", "rm", "mv", "cp"]

    def __init__(self):
        self._history = {}
        # {
        #     path : [last_timestamp, action]
        #     path : [last_timestamp, "moved by", source_path]
        # }

    def set_change(self, action, source_path, destination_path=None):
        ''' actions allowed:
            with only a path:   new, modify, rm
            with two paths:     mv, cp '''
        if action not in History.ACTIONS:
            raise NotAllowedError

        if action != "new" and path not in self._history:
            raise MissingFileError
        
        if (action == "mv" or action == "cp") and destination_path is None:
            raise MissingDestinationError

        if action == "mv":
            self._history[source_path] = [time.time(), "moved to", destination_path]
            self._history[destination_path] = [time.time(), "moved by", source_path]
        elif action == "cp":
            self._history[destination_path] = [time.time(), "copied by", source_path]
        else:
            self._history[source_path] = [time.time(), action]


class UserActions(Resource):
    @auth.login_required
    def diffs(self):
        """ Returns a JSON with a list of changes.
        Expected as POST data:
        { "timestamp" : float }  """

        try:
            timestamp = request.form["timestamp"]
        except KeyError:
            abort(400)

        changes = []

        for path in users.users[auth.username()]["paths"]:
            if history._history[path][0] > timestamp:
                changes.append({
                        "path" : path, 
                        "action" : history[path]
                })
        
        if changes:
            return json.dumps(changes), 200
        else:
            return "up to grade", 204

    def create_user(self):
        ''' Expected as POST data:
        { "user" : username, "psw" : password } '''

        try:
            user = request.form["user"]
            psw = request.form["psw"]
        except KeyError:
            abort(400)

        return users.new_user(user, psw)

    commands = {
        "create" :  create_user,
        "diffs"  :  diffs,
    }

    def post(self, cmd):
        try:
            return UserActions.commands[cmd](self)
        except KeyError:
            abort(404)


class Files(Resource):
    @auth.login_required
    def get(self, path):
        """Download
        this function return file content as string using GET"""
        destination_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        file_name = path        #fix this for subdirectories
        full_path = os.path.join("user_dirs", destination_folder, file_name)
        if os.path.exists(full_path):
            with open(full_path, "r") as tmp:
                return tmp.read()
        else:
            abort(404)


    @auth.login_required
    def put(self, path):
        """Put
        this function update file"""
        destination_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        file_name = request.form["file_name"]
        full_path = os.path.join("user_dirs", destination_folder, file_name)

        if os.path.exists(full_path):
            f = request.files["file_content"]
            server_dir = os.getcwd()
            os.chdir(os.path.join("user_dirs", destination_folder))
            f.save(file_name)
            os.chdir(server_dir)
            return "updated", 201  
        else:
            return "file not found", 409


    @auth.login_required
    def post(self, path):
        """Upload
        this function load file using POST"""
        destination_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        file_name = request.form["file_name"]
        full_path = os.path.join("user_dirs", destination_folder, file_name)

        if os.path.exists(full_path):
            return "already exists", 409
        else:
            f = request.files["file_content"]
            server_dir = os.getcwd()
            os.chdir(os.path.join("user_dirs", destination_folder))
            f.save(file_name)
            os.chdir(server_dir)
            return "upload done", 201


class Actions(Resource):
    def _delete(self):
        """Delete
        this function delete file selected"""
        path = request.form["path"]
        destination_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        full_path = os.path.join("user_dirs", destination_folder, path)

        if os.path.exists(full_path):
            os.remove(full_path)
            return "file deleted",200
        else:
            return "file not found", 409


    def _copy(self):
        """Copy
        this function copy a file from src to dest"""
        file_src = request.form["file_src"]
        destination_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        full_src_path = os.path.join("user_dirs", destination_folder, file_src)

        file_dest = request.form["file_dest"]
        full_dest_path = os.path.join("user_dirs", destination_folder, file_dest)
        
        if os.path.exists(full_src_path): 
            if os.path.exists(full_dest_path):
                shutil.copy(full_src_path, full_dest_path)
                return "copied file",200
            else:
                return "dest not found", 409
        else:
            return "file not found in src", 409


    def _move(self):
        """Move
        this function move a file from src to dest"""
        file_src = request.form["file_src"]
        destination_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        full_src_path = os.path.join("user_dirs", destination_folder, file_src)

        file_dest = request.form["file_dest"]
        full_dest_path = os.path.join("user_dirs", destination_folder, file_dest)
        
        if os.path.exists(full_src_path): 
            if os.path.exists(full_dest_path):
                shutil.copy(full_src_path, full_dest_path)
                os.remove(full_src_path)
                return "moved file",200
            else:
                return "dest not found", 409
        else:
            return "file not found in src", 409
    
    commands = {
        "delete" : _delete,
        "move" : _move,
        "copy" : _copy
    }

    @auth.login_required
    def post(self, cmd):
        try:
            return Actions.commands[cmd](self)
        except KeyError:
            return abort(404)


@auth.verify_password
def verify_password(username, password):
    if username not in users.users:
        return False
    return sha256_crypt.verify(password, users.users[username]["psw"])


def verify_path(username, path):
    #verify if the path is in the user accesses
    if path in users.users[username]["paths"]:
        return True
    else:
        return False
    

@app.route("/hidden_page")
@auth.login_required
def hidden_page():
    return "Hello {}\n".format(auth.username())


@app.route("/")
def welcome():
    local_time = datetime.datetime.now()
    formatted_time = local_time.strftime("%Y-%m-%d %H:%M")
    return "Welcome on the Server!\n{}\n".format(formatted_time)


def main():
    if not os.path.isdir(USERS_DIRECTORIES):
        os.mkdir(USERS_DIRECTORIES)
    app.run(host="0.0.0.0",debug=True)         # TODO: remove debug=True


users = Users()
history = History()


if __name__ == "__main__":
    init()
    main()
