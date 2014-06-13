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
from hashlib import md5


app = Flask(__name__)
api = Api(app)
auth = HTTPBasicAuth()
USERS_DIRECTORIES = "user_dirs/"
USERS_DATA = "user_data.json"
parser = reqparse.RequestParser()
parser.add_argument("task", type=str)


def file_updated(modified_file_path):
    ''' set new timestamp for each user who can access to the file +
    create new md5 for that file '''
    timestamp = time.time()
    md5_file = md5[modified_file_path]

    for u, v in users.users.items():
        for p in v["paths"]:
            if modified_file_path.startswith(p):
                v["last_change"] = timestamp
                v["md5_tree"][md5_file] = modified_file_path


class Users(object):
    
    def __init__(self):
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
            #            "psw" : encoded_password,
            #            "paths" : [list of directory]
            #            "last_change" : timestamp,
            #            "md5_tree" : {
            #                   md5 : path_file
            #            }
            #     }
            # }
            self.counter_id = 0
    

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

        history.set_change("new", dir_id)

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


class Files(Resource):
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
            history_path = os.path.join(destination_folder, file_name) #eg. <user_dir>/subdir/file.txt
            history.set_change("modify", history_path)
            return "updated", 201
        else:
            return "file not found", 409


    def post(self, path):
        """Upload
        this function load file using POST"""
        destination_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        full_path = os.path.join("user_dirs", destination_folder, path)
        dirs_tree = path.split("/")[:-1]  #list of subdirectories that contains the new file except filename
        if os.path.exists(full_path):
            return "already exists", 409
        else:
            server_dir = os.getcwd()
            os.chdir(os.path.join("user_dirs", destination_folder))
            for folder in dirs_tree:      #checking if subdirectories already exist else create them
                if os.path.exists(folder):
                    os.chdir(folder)                   
                else:
                    os.mkdir(folder)
                    os.chdir(folder)
            f = request.files["file_content"]
            file_name = os.path.split(path)[1]
            f.save(file_name)
            os.chdir(server_dir)
            history_path = os.path.join(destination_folder, file_name) #eg. <user_dir>/subdir/file.txt
            history.set_change("new", history_path)
            return "upload done", 201


class Actions(Resource):
    def get_files(self):
        ''' Send a JSON with the timestamp of the last change in user
        directories and an md5 for each file '''
        # {
        #     "last_change" : timestamp_last_change
        #     "files" : {
        #         md5 : path
        #     }
        # }
        u = users.users[auth.username()]
        to_send = {
            "last_change" : u["last_change"]
            "files" : u["md5_tree"]
        }
        return json.dumps(to_send)


    def _delete(self):
        """Delete
        this function delete file selected"""
        path = request.form["path"]
        destination_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        full_path = os.path.join("user_dirs", destination_folder, path)

        if os.path.exists(full_path):
            os.remove(full_path)
            history_path = os.path.join(destination_folder, file_name) #eg. <user_dir>/subdir/file.txt
            history.set_change("rm", history_path)
            return "file deleted",200
        else:
            return "file not found", 409


    def _copy(self):
        """Copy
        this function copy a file from src to dest"""
        file_src = request.form["file_src"]
        src_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        destination_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        full_src_path = os.path.join("user_dirs", src_folder, file_src)
        file_dest = request.form["file_dest"]
        full_dest_path = os.path.join("user_dirs", destination_folder, file_dest)
        
        if os.path.exists(full_src_path): 
            if os.path.exists(full_dest_path):
                shutil.copy(full_src_path, full_dest_path)
                history_path = os.path.join(destination_folder, file_src) #eg. <user_dir>/subdir/file.txt
                history_dest_path = os.path.join(destination_folder, file_dest)
                history.set_change("cp", history_path, history_dest_path)
                return "copied file",200
            else:
                return "dest not found", 409
        else:
            return "file not found in src", 409


    def _move(self):
        """Move
        this function move a file from src to dest"""
        file_src = request.form["file_src"]
        src_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        destination_folder = users.users[auth.username()]["paths"][0] #for now we set it has the user dir
        full_src_path = os.path.join("user_dirs", src_folder, file_src)
        file_dest = request.form["file_dest"]
        full_dest_path = os.path.join("user_dirs", destination_folder, file_dest)
        
        if os.path.exists(full_src_path): 
            if os.path.exists(full_dest_path):
                shutil.copy(full_src_path, full_dest_path)
                os.remove(full_src_path)
                history_path = os.path.join(destination_folder, file_src) #eg. <user_dir>/subdir/file.txt
                history_dest_path = os.path.join(destination_folder, file_dest)
                history.set_change("mv", history_path, history_dest_path)
                return "moved file",200
            else:
                return "dest not found", 409
        else:
            return "file not found in src", 409
    
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
    print username
    if username not in users.users:
        return False
    return sha256_crypt.verify(password, users.users[username]["psw"])


@app.route("/diffs")
@auth.login_required
def diffs():
    """ Returns a JSON with a list of changes.
    Expected as POST data:
    { "timestamp" : float }  """

    try:
        timestamp = request.form["timestamp"]
    except KeyError:
        abort(400)

    changes = []

    for p, v in history._history.items():
        for myp in users.users[auth.username()]["paths"]:
            if p.startswith(myp) and v[0] > timestamp:
                changes.append({
                    "path" : p,
                    "action" : v
                })
    
    if changes:
        return json.dumps(changes), 200
    else:
        return "up to grade", 204

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
_API_PREFIX = "/API/v1/"

api.add_resource(Files, "{}files/<path:path>".format(_API_PREFIX))
api.add_resource(Actions, "{}actions/<string:cmd>".format(_API_PREFIX))

if __name__ == "__main__":
    main()
