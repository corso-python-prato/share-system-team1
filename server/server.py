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

from server_errors import *
from snapshot import *


app = Flask(__name__)
api = Api(app)
auth = HTTPBasicAuth()
_API_PREFIX = "/API/v1/"
USERS_DIRECTORIES = "user_dirs/"
USERS_DATA = "user_data.json"
parser = reqparse.RequestParser()
parser.add_argument("task", type=str)


class User(object):
    ''' maintaining two dictionaries:
        paths     = { client_path : [server_path, md5] }
        inside Snapshot: { md5 : [client_path1, client_path2] }
    server_path is for shared directories management '''

# class initialization: first try with a config file, if fail initialize
# from scratch
    users = {}
    counter_id = 0

    try:
        ud = open(USERS_DATA, "r")
        saved = json.load(ud)
        ud.close()
    # if error, create new structure from scratch
    except IOError:
        pass                # missing file
    except ValueError:      # invalid json
        os.remove(USERS_DATA)
    else:
        counter_id = saved["counter_id"]
        for u, v in saved["users"].items():
            User(u, u["psw"], u["paths"])


# other class methods
    @classmethod
    def get_new_id(cls):
        new_id = hex(cls.counter_id)[2:]
        cls.counter_id += 1    
        return new_id


    @classmethod
    def save_users(cls, filename=None):
        if not filename:
            filename = USERS_DATA

        to_save = {
            "counter_id" : cls.counter_id,
            "users" : {}
        }        
        for u, v in users.items():
            to_save["users"][u] = v.to_dict()

        with open(filename, "w") as f:
            json.dump(to_save, f)

    @classmethod
    def get_user(cls, username):
        try:
            return = User.users[username]
        except KeyError:
            raise ConflictError("User doesn't exist")


# dynamic methods
    def __init__(self, username, password, paths=None):
    # if restoring the server
        if paths:
            self.psw = password
            self.paths = paths
            self.snapshot = Snapshot.restore_server(paths)
            User.user[username] = self
            return

    # else if I'm creating a new user
        if username in User.users:
            return "This user already exists", 409

        psw_hash = sha256_crypt.encrypt(password)
        dir_id = User.get_new_id()
        full_path = os.path.join(USERS_DIRECTORIES, dir_id)
        try:
            os.mkdir(full_path)
        except OSError:
            raise ConflictError(
                    "Conflict while creating the directory for a new user"
            )

    # class attributes
        self.psw = psw_hash
        self.snapshot = Snapshot()
        self.paths = {}     # path of each file and each directory of the user!
                            # client_path : [server_path, md5]

    # update snapshot, users, file
        self.push_path("", full_path)
        User.users[username] = self
        User.save_users()

        return "User created!", 201


    def to_dict(self):
        return {
            "psw" : self.psw,
            "paths" : self.paths
        }


    def get_server_path(self, client_path):
        if client_path in self.paths:
            return self.paths[client_path][0]
        else:
            return False


    def push_path(self, client_path, server_path):
        md5 = self.snapshot.push(client_path)
        self.paths[client_path] = [server_path, md5]
            # TODO: manage shared folder here. Something like:
            # for s, v in shared_folder.items():
            #     if server_path.startswith(s):
            #         update each user


    def rm_path(self, client_path):
        md5 = self.paths[client_path][1]
        self.snapshot.rm(md5, client_path)
        del self.paths[client_path]


class Resource(Resource):
    method_decorators = [auth.login_required]


class Files(Resource):
    def get(self, client_path):
        """ Download
        this function return file content as a string using GET """
        u = User.get_user(auth.username())
        server_path = u.get_server_path(client_path)
        if not server_path:
            abort(404)
        try:
            f = open(server_path, "r")
            return f.read() 
        except IOError:
            abort(404)


    def put(self, client_path):
        """ Put
        this function updates an existing file """
        u = User.get_user(auth.username())
        server_path = u.get_server_path(client_path)
        
        directory_path, file_name = os.path.split(server_path)
        f = request.files["file_content"]
        server_dir = os.getcwd()                    

        try:
            os.chdir(directory_path)
            f.save(file_name)                   # ISSUE: non è possibile dare a save la path completa, senza usare i chdir?
            os.chdir(server_dir)
        except IOError: 
            abort(409)
        else:
            u.push_path(client_path, server_path)
            # TODO: check here if the directory is shared and notify to the other users
            return "File updated", 201


    def post(self, client_path):
        """ Upload
        this function upload a new file using POST """
        u = User.get_user(auth.username())
        if u.get_server_path(client_path):
            return "An file of the same name already exists in the same path", 409

    # Search a father directory in user's client paths
        directory_path, file_name = os.path.split(client_path)
        dir_list = directory_path.split("/")
        
        to_be_created = []
        while os.path.join(dir_list) not in u.paths:
            to_be_created.append(dir_list.pop())

        server_path = os.path.join(
                *dir_list,
                *to_be_created
        )
        # TODO: check here if the directory is shared and notify to the other users

    # Create the new folder and continue saving the file
        os.makedirs(server_path)

        server_dir = os.getcwd()
        os.chdir(server_path)

        f = request.files["file_content"]
        f.save(file_name)
        os.chdir(server_dir)

        server_path = os.path.join(server_path, file_name)
        u.push_path(client_path, server_path)
        return "file uploaded", 201


class Actions(Resource):
    def get_src_dest_path(self):
        file_src = request.form["file_src"]
        src_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        destination_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        full_src_path = os.path.join("user_dirs", src_folder, file_src)
        file_dest = request.form["file_dest"]
        full_dest_path = os.path.join("user_dirs", destination_folder, file_dest)
        return full_src_path,full_dest_path


    def get_files(self):
        """ Send a JSON with the timestamp of the last change in user
        directories and an md5 for each file """
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
        full_path = get_server_path(auth.username(), path)

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
        "get_files": get_files,
        "delete": _delete,
        "move": _move,
        "copy": _copy
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
