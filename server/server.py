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

# TODO: from raw_box_common import md5
from hashlib import md5


app = Flask(__name__)
api = Api(app)
auth = HTTPBasicAuth()
_API_PREFIX = "/API/v1/"
USERS_DIRECTORIES = "user_dirs/"
USERS_DATA = "user_data.json"
parser = reqparse.RequestParser()
parser.add_argument("task", type=str)


def path_updated(modified_file_path):
    ''' set new timestamp for each user who can access to the file +
    create new md5 for that file '''
    timestamp = time.time()
    md5_file = str(md5(modified_file_path))
    # TODO: if file has been removed

    for u, v in users.users.items():
        for p in v["paths"]:
            if modified_file_path.startswith(p):
                v["last_change"] = timestamp
                v["md5_tree"][md5_file] = modified_file_path


class Users(object):
    
    def __init__(self):
        def from_zero(self):
            self.users = {}
            # { 
            #     username : { 
            #            "psw" : encoded_password,
            #            "paths" : [list of directory]
            #            "last_change" : timestamp,
            #            "md5_tree" : {
            #                   md5 : path_file
            #            }
            #     }
            # }
            self.counter_id = 0

        try:
            ud = open(USERS_DATA, "r")
            saved = json.load(ud)
            self.users = saved["users"]
            self.counter_id = saved["counter_id"]
            ud.close()
        except IOError:         # file not present
            from_zero(self)
        except ValueError:      # invalid json
            os.remove(USERS_DATA)
            from_zero(self)
    

    def get_id(self):
        new_id = hex(self.counter_id)[2:]
        self.counter_id += 1    
        return new_id


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
            "paths" : [dir_id],
            "last_change" : time.time(),
            "md5_tree" : {}
        }

        path_updated(dir_id)
        self.save_users()
        return "User created!", 201


    def save_users(self, filename=None):
        if not filename:
            filename = USERS_DATA
        to_save = {
            "counter_id" : self.counter_id,
            "users" : self.users
        }
        with open(filename, "w") as ud:
            json.dump(to_save, ud)


class Resource(Resource):
    method_decorators = [auth.login_required]


def get_path(user, path):
    folder = users.users[user]["paths"][0]
    return os.path.join("user_dirs", folder, path)


class Files(Resource):
    def get(self, path):
        """Download
        this function return file content as string using GET"""
        full_path = get_path(auth.username(), path)
        try:
            f = open(full_path, "r")
            return f.read() 
        except IOError: 
            abort(404)


    def put(self, path):
        """Put
        this function update file"""
        full_path = get_path(auth.username(), path)
        directory_path, file_name = os.path.split(full_path)
        f = request.files["file_content"]
        server_dir = os.getcwd()

        try:
            os.chdir(directory_path)
            f.save(file_name)
            os.chdir(server_dir)
            return "file updated"
        except IOError: 
            abort(409)
        else:
            file_path = os.path.join(directory_path, file_name)
            path_updated(file_path)


    def post(self, path):
        """Upload
        this function load file using POST"""
        full_path = get_path(auth.username(), path)

        if os.path.exists(full_path):
            return "already exists", 409
        else:
            os.makedirs(full_path)
            put(self, path)


class Actions(Resource):
    def get_src_dest_path():
        file_src = request.form["file_src"]
        src_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        destination_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        full_src_path = os.path.join("user_dirs", src_folder, file_src)
        file_dest = request.form["file_dest"]
        full_dest_path = os.path.join("user_dirs", destination_folder, file_dest)
        return full_src_path,full_dest_path


    def get_files(self):
        ''' Send a JSON with the timestamp of the last change in user
        directories and an md5 for each file '''
        # {
        #     "last_change" : timestamp_last_change
        #     "files" : {
        #         md5 : path
        #     }
        # }
        usr = users.users[auth.username()]
        to_send = {
            "last_change" : usr["last_change"],
            "files" : usr["md5_tree"]
            }
        return json.dumps(to_send)


    def _delete(self):
        """Delete
        this function delete file selected"""
        path = request.form["path"]
        full_path = get_path(auth.username(), path)

        try:
            os.remove(full_path)
            return "file delete complete"
        except KeyError:
            return abort(409)
        else:
            path_updated(full_path)


    def _copy(self):
        """Copy
        this function copy a file from src to dest"""
        full_src_path,full_dest_path = self.get_src_dest_path()

        try:
            shutil.copy(full_src_path, full_dest_path)
            return "file copy complete"
        except KeyError:
            return abort(409)
        else:
            path_updated(full_src_path)
            path_updated(full_dest_path)


    def _move(self):
        """Move
        this function move a file from src to dest"""
        full_src_path,full_dest_path = self.get_src_dest_path()
        
        try:
            shutil.move(full_src_path, full_dest_path)
            return "file trasnfer complete"
        except KeyError:
            return abort(409)
        else:
            path_updated(full_src_path)
            path_updated(full_dest_path)

    
    commands = {
        "get_files" : get_files,
        "delete" : _delete,
        "move" : _move,
        "copy" : _copy
    }

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


# @app.route("{}create_user".format(_API_PREFIX), methods = ["POST"])
@app.route("/API/v1/create_user", methods = ["POST"])
def create_user():
        ''' Expected as POST data:
        { "user" : username, "psw" : password } '''

        try:
            user = request.form["user"]
            psw = request.form["psw"]
        except KeyError:
            abort(400)

        return users.new_user(user, psw)


@app.route("/hidden_page")
@auth.login_required
def hidden_page():
    return "Hello {}\n".format(auth.username())


@app.route("/")
def welcome():
    local_time = datetime.datetime.now()
    formatted_time = local_time.strftime("%Y-%m-%d %H:%M")
    return "Welcome on the Server!\n{}\n".format(formatted_time)


def backup_config_files(folder_name=None):
    if not folder_name:
        folder_name = os.path.join("backup", str(time.time()))

    try:
        os.makedirs(folder_name)
    except IOError:
        return False
    else:
        users.save_users(os.path.join(folder_name, USERS_DATA))
        return True


def main():
    if not os.path.isdir(USERS_DIRECTORIES):
        os.mkdir(USERS_DIRECTORIES)
    app.run(host="0.0.0.0",debug=True)         # TODO: remove debug=True


users = Users()

api.add_resource(Files, "{}files/<path:path>".format(_API_PREFIX))
api.add_resource(Actions, "{}actions/<string:cmd>".format(_API_PREFIX))

if __name__ == "__main__":
    main()
