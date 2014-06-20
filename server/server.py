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


HTTP_CONFLICT = 409
HTTP_CREATED = 201
HTTP_NOT_FOUND = 404
HTTP_BAD_REQUEST = 400

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
        · paths     = { client_path : [server_path, md5] }
        · inside Snapshot: { md5 : [client_path1, client_path2] }
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
            return cls.users[username]
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
            return "This user already exists", HTTP_CONFLICT

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

        return "User created!", HTTP_CREATED


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


    def create_server_path(self, client_path):
        directory_path, filename = os.path.split(client_path)
        dir_list = directory_path.split("/")
        
        to_be_created = []
        while os.path.join(dir_list) not in self.paths:
            to_be_created.insert(0, dir_list.pop())
        
        if not dir_list:
            fathernew_client_path = ""
        else:
            father = os.path.join(dir_list)

        new_server_path = self.paths[new_client_path][0]
        new_client_path = father
        for d in to_be_created:
            new_client_path = os.path.join(new_client_path, d)
            new_server_path = os.path.join(new_server_path, d)
            push_path(new_client_path, new_server_path)

        return new_server_path, filename


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
            abort(HTTP_NOT_FOUND)
        try:
            f = open(server_path, "r")
            content = f.read()
            f.close()
            return content
        except IOError:
            abort(HTTP_NOT_FOUND)


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
            abort(HTTP_CONFLICT)
        else:
            u.push_path(client_path, server_path)
            # TODO: check here if the directory is shared and notify to the other users
            return "File updated", HTTP_CREATED


    def post(self, client_path):
        """ Upload
        this function upload a new file using POST """
        u = User.get_user(auth.username())
        if u.get_server_path(client_path):
            return "An file of the same name already exists in the same path", HTTP_CONFLICT

        server_path = u.create_server_path(client_path)
        os.makedirs(server_path)

        server_dir = os.getcwd()
        os.chdir(server_path)

        f = request.files["file_content"]
        f.save(file_name)
        os.chdir(server_dir)

        server_path = os.path.join(server_path, file_name)
        u.push_path(client_path, server_path)
        return "file uploaded", HTTP_CREATED


class Actions(Resource):
    def get_files(self):
        """ Send a JSON with the timestamp of the last change in user
        directories and an md5 for each file """
        # {
        #     "last_change" : timestamp_last_change
        #     "files" : {
        #         md5 : path
        #     }
        # }
        u = User.get_user(auth.username())
        return u.snapshot.to_json()


    def _delete(self):
        """ This function deletes a selected file """
        u = User.get_user(auth.username())
        client_path = request.form["path"]
        server_path = u.get_server_path(client_path)

        try:
            os.remove(server_path)
        except KeyError:
            return abort(HTTP_CONFLICT)
        else:
            u.rm_path(client_path)
            return "File delete complete"


    def _copy(self):
        """ This function copies a file from src to dest """
        u = User.get_user(auth.username())
        client_src = request.form["file_src"]
        client_dest = request.form["file_dest"]

        server_src = u.get_server_path(client_src)
        server_dest = u.create_server_path(client_dest)

        try:
            shutil.copy(server_src, server_dest)
        except KeyError:
            return abort(HTTP_CONFLICT)
        else:
            u.push_path(client_dest, server_dest)
            return "File copy complete"


    def _move(self):
        """ This function moves a file from src to dest"""
        u = User.get_user(auth.username())
        client_src = request.form["file_src"]
        client_dest = request.form["file_dest"]

        server_src = u.get_server_path(client_src)
        server_dest = u.create_server_path(client_dest)
        
        try:
            shutil.move(server_src, server_dest)
        except KeyError:
            return abort(HTTP_CONFLICT)
        else:
            u.rm_path(client_src)
            u.push_path(client_dest, server_dest)
            return "File trasnfer complete"

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
            return abort(HTTP_NOT_FOUND)


@auth.verify_password
def verify_password(username, password):
    if username not in users.users:
        return False
    return sha256_crypt.verify(password, users.users[username]["psw"])


@app.route("{}create_user".format(_API_PREFIX), methods = ["POST"])
# @app.route("/API/v1/create_user", methods = ["POST"])
def create_user():
        ''' Expected as POST data:
        { "user" : username, "psw" : password } '''
        try:
            user = request.form["user"]
            psw = request.form["psw"]
        except KeyError:
            abort(HTTP_BAD_REQUEST)
        else:
            User(user, psw)


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
        User.save_users(os.path.join(folder_name, USERS_DATA))
        return True


def main():
    if not os.path.isdir(USERS_DIRECTORIES):
        os.mkdir(USERS_DIRECTORIES)
    app.run(host="0.0.0.0",debug=True)         # TODO: remove debug=True


api.add_resource(Files, "{}files/<path:path>".format(_API_PREFIX))
api.add_resource(Actions, "{}actions/<string:cmd>".format(_API_PREFIX))

if __name__ == "__main__":
    main()
