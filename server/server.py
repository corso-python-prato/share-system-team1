#!/usr/bin/env python
#-*- coding: utf-8 -*-

from flask import Flask, request
from flask.ext.httpauth import HTTPBasicAuth
from flask.ext.restful import reqparse, abort, Api, Resource
from flask.ext.mail import Mail, Message
from passlib.hash import sha256_crypt
import ConfigParser
import time
import datetime
import json
import os
import shutil
import hashlib
import base64

from server_errors import *


HTTP_CONFLICT = 409
HTTP_CREATED = 201
HTTP_NOT_FOUND = 404
HTTP_BAD_REQUEST = 400
HTTP_OK = 200
HTTP_GONE = 410

config = ConfigParser.ConfigParser()
config.read('email_settings.ini')
MAIL_SERVER = config.get('email', 'smtp_address')
MAIL_PORT = config.getint('email', 'smtp_port')
MAIL_USERNAME = config.get('email', 'smtp_username')
MAIL_PASSWORD = config.get('email', 'smtp_password')

app = Flask(__name__)
app.config.from_object(__name__)
mail = Mail(app)
api = Api(app)
auth = HTTPBasicAuth()
_API_PREFIX = "/API/v1/"
USERS_DIRECTORIES = "user_dirs/"
USERS_DATA = "user_data.json"
PENDING_USERS = "pending.tmp"
parser = reqparse.RequestParser()
parser.add_argument("task", type=str)

@app.route('/minfo')
def send_mail(receiver, obj, content):
    """ Send an email to the 'receiver', with the
    specified object ('obj') and the specified 'content' """
    msg = Message(
        obj,
        sender="RawBoxTeam",
        recipients=[receiver])
    msg.body = content
    with app.app_context():
        mail.send(msg)


def to_md5(path, block_size=2**20):
    """ if path is a file, return a md5;
    if path is a directory, return False """
    if os.path.isdir(path):
        return False

    m = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(block_size), b''):
            m.update(chunk)

    return m.hexdigest()


class User(object):
    """ maintaining two dictionaries:
        · paths     = { client_path : [server_path, md5] }
        · inside Snapshot: { md5 : [client_path1, client_path2] }
    server_path is for shared directories management """

    users = {}

    # CLASS AND STATIC METHODS
    @staticmethod
    def user_class_init():
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
            for u, v in saved["users"].items():
                User(u, None, from_dict=v)

    @classmethod
    def save_users(cls, filename=None):
        if not filename:
            filename = USERS_DATA

        to_save = {
            "users": {}
        }
        for u, v in cls.users.items():
            to_save["users"][u] = v.to_dict()

        with open(filename, "w") as f:
            json.dump(to_save, f)

    @classmethod
    def get_user(cls, username):
        try:
            return cls.users[username]
        except KeyError:
            raise MissingUserError("User doesn't exist")

    # DYNAMIC METHODS
    def __init__(self, username, password, from_dict=None):
        # if restoring the server
        if from_dict:
            self.psw = from_dict["psw"]
            self.paths = from_dict["paths"]
            self.timestamp = from_dict["timestamp"]
            User.users[username] = self
            return

        full_path = os.path.join(USERS_DIRECTORIES, username)
        try:
            os.mkdir(full_path)
        except OSError:
            abort(HTTP_CONFLICT)

        # OBJECT ATTRIBUTES
        self.psw = password

        # path of each file and each directory of the user:
        #     { client_path : [server_path, md5, timestamp] }
        self.paths = {}

        # timestamp of the last change in the user's files
        self.timestamp = time.time()

        # update users, file
        self.push_path("", full_path, update_user_data=False)
        User.users[username] = self
        User.save_users()

    def to_dict(self):
        return {
            "psw": self.psw,
            "paths": self.paths,
            "timestamp": self.timestamp
        }

    def get_server_path(self, client_path):
        if client_path in self.paths:
            return self.paths[client_path][0]
        else:
            return False

    def create_server_path(self, client_path):
        # the client_path do not have to contain "../"
        if (client_path.startswith("../")) or ("/../" in client_path):
            abort(HTTP_BAD_REQUEST)

        # search the first directory father already present
        directory_path, filename = os.path.split(client_path)
        dir_list = directory_path.split("/")

        to_be_created = []
        while (len(dir_list) > 0) \
                and (os.path.join(*dir_list) not in self.paths):
            to_be_created.insert(0, dir_list.pop())

        if len(dir_list) == 0:
            father = ""
        else:
            father = os.path.join(*dir_list)

        # create all the new subdirs and add them to paths
        new_client_path = father
        new_server_path = self.paths[new_client_path][0]
        for d in to_be_created:
            new_client_path = os.path.join(new_client_path, d)
            new_server_path = os.path.join(new_server_path, d)
            if not os.path.exists(new_server_path):
                os.makedirs(new_server_path)
            self.push_path(
                new_client_path,
                new_server_path,
                update_user_data=False
            )

        return os.path.join(new_server_path, filename)

    def push_path(self, client_path, server_path, update_user_data=True):
        md5 = to_md5(server_path)
        now = time.time()
        self.paths[client_path] = [server_path, md5, now]
        if update_user_data:
            self.timestamp = now
            User.save_users()
        # TODO: manage shared folder here. Something like:
        # for s, v in shared_folder.items():
        #     if server_path.startswith(s):
        #         update each user

    def rm_path(self, client_path):
        # remove empty directories
        directory_path, filename = os.path.split(client_path)
        if directory_path != "":
            dir_list = directory_path.split("/")

            while len(dir_list) > 0:
                client_subdir = os.path.join(*dir_list)
                server_subdir = self.paths[client_subdir][0]
                try:
                    os.rmdir(server_subdir)
                except OSError:         # the directory is not empty
                    break
                else:
                    del self.paths[client_subdir]
                    # TODO: manage shared folder here.
                    dir_list.pop()

        # remove the argument client_path and save
        del self.paths[client_path]
        self.timestamp = time.time()
        User.save_users()


class Resource_with_auth(Resource):
    method_decorators = [auth.login_required]


class UserApi(Resource):
    pending = {}

    def post(self, cmd):
        """Create a user registration request
        Expected {"user": <username>, "psw": <password>}
        save pending as
        {<username>:
            {
            "psw": <password>,
            "code": <activation_code>
            "timestamp": <timestamp>
            }
        }"""
        if (os.path.isfile(PENDING_USERS)):
            with open(PENDING_USERS, "r") as p_u:
                UserApi.pending = json.load(p_u)
        try:
            user = request.form["user"]
            psw = request.form["psw"]
        except KeyError:
            abort(HTTP_BAD_REQUEST)

        if user in UserApi.pending:
            return "This user have arleady a pending request", HTTP_CONFLICT
        elif user in User.users:
            return "This user already exists", HTTP_CONFLICT
        else:
            psw_hash = sha256_crypt.encrypt(psw)
            code = base64.b64encode(os.urandom(64))
            UserApi.pending[user] = \
                {"password": psw_hash,
                 "code": code,
                 "timestamp": time.time()}

            with open(PENDING_USERS, "w") as p_u:
                json.dump(UserApi.pending, p_u)
            #insert send_mail()
            return "user added to pending users", HTTP_CREATED

    def put(self, cmd):
        """Activate a pending user
        Expected
        {"user": <username>
        "code": <activation code>}"""
        try:
            user = request.form["user"]
            code = request.form["code"]
        except KeyErcreateror:
            abort(HTTP_BAD_REQUEST)

        if (os.path.isfile(PENDING_USERS)):
            with open(PENDING_USERS, "r") as p_u:
                UserApi.pending = json.load(p_u)

        if user in User.users:
            return "This user is already active", HTTP_CONFLICT
        elif code == UserApi.pending[user]["code"]:
            User(user, UserApi.pending[user]["password"])
            del UserApi.pending[user]
            with open(PENDING_USERS, "w") as p_u:
                json.dump(UserApi.pending, p_u)
            return "user activated", HTTP_CREATED

    def get(self, cmd=None):
        if not cmd:
            return self._get_user()
        elif cmd == "delete":
            return self._delete()
        else:
            return "wrong command", HTTP_BAD_REQUEST

    def _get_user(self):
        """GET user data
        for now return {"user": <username>, "psw": <password>}"""
        pass

    @auth.login_required
    def _delete(self):
        """Delete the user who is making the request
        """
        pass


class Files(Resource_with_auth):
    def _diffs(self):
        """ Send a JSON with the timestamp of the last change in user
        directories and an md5 for each file
        Expected GET method without path """
        u = User.get_user(auth.username())
        tree = {}
        for p, v in u.paths.items():
            if not v[1]:
                continue

            if not v[1] in tree:
                tree[v[1]] = [{
                    "path": p,
                    "timestamp": v[2]
                }]
            else:
                tree[v[1]].append({
                    "path": p,
                    "timestamp": v[2]
                })

        snapshot = {
            "snapshot": tree,
            "timestamp": u.timestamp
        }

        return snapshot, HTTP_OK
        # return json.dumps(snapshot), HTTP_OK

    def _download(self, client_path):
        """Download
        Returns file content as a byte string
        Expected GET method with path"""
        u = User.get_user(auth.username())
        server_path = u.get_server_path(client_path)
        if not server_path:
            return "File unreachable", HTTP_NOT_FOUND

        try:
            f = open(server_path, "rb")
            content = f.read()
            f.close()
            return content
        except IOError:
            abort(HTTP_GONE)

    def get(self, client_path=None):
        if not client_path:
            return self._diffs()
        else:
            return self._download(client_path)

    def put(self, client_path):
        """ Update
        Updates an existing file
        Expected as POST data:
        { "file_content" : <file>} """
        u = User.get_user(auth.username())
        server_path = u.get_server_path(client_path)
        if not server_path:
            abort(HTTP_NOT_FOUND)

        f = request.files["file_content"]
        f.save(server_path)

        u.push_path(client_path, server_path)
        return u.timestamp, HTTP_CREATED

    def post(self, client_path):
        """ Upload
        Upload a new file
        Expected as POST data:
        { "file_content" : <file>} """
        u = User.get_user(auth.username())
        if u.get_server_path(client_path):
            return "A file of the same name already exists in the same path", \
                HTTP_CONFLICT

        server_path = u.create_server_path(client_path)

        f = request.files["file_content"]
        f.save(server_path)

        u.push_path(client_path, server_path)
        return u.timestamp, HTTP_CREATED


class Actions(Resource_with_auth):
    def _delete(self):
        """ Expected as POST data:
        { "path" : <path>} """
        u = User.get_user(auth.username())
        client_path = request.form["path"]
        server_path = u.get_server_path(client_path)
        if not server_path:
            abort(HTTP_NOT_FOUND)

        os.remove(server_path)

        u.rm_path(client_path)
        return u.timestamp

    def _copy(self):
        return self._transfer(keep_the_original=True)

    def _move(self):
        return self._transfer(keep_the_original=False)

    def _transfer(self, keep_the_original=True):
        """ Moves or copy a file from src to dest
        depending on keep_the_original value
        Expected as POST data:
        { "file_src": <path>, "file_dest": <path> }"""
        u = User.get_user(auth.username())
        client_src = request.form["file_src"]
        client_dest = request.form["file_dest"]

        server_src = u.get_server_path(client_src)
        if not server_src:
            abort(HTTP_NOT_FOUND)

        server_dest = u.create_server_path(client_dest)

        try:
            if keep_the_original:
                shutil.copy(server_src, server_dest)
            else:
                shutil.move(server_src, server_dest)
        except shutil.Error:
            return abort(HTTP_CONFLICT)
        else:
            if keep_the_original:
                u.push_path(client_dest, server_dest)
            else:
                u.push_path(client_dest, server_dest, update_user_data=False)
                u.rm_path(client_src)
            return u.timestamp, HTTP_CREATED

    commands = {
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
    try:
        u = User.get_user(username)
    except MissingUserError:
        return False
    else:
        return sha256_crypt.verify(password, u.psw)


def main():
    if not os.path.isdir(USERS_DIRECTORIES):
        os.mkdir(USERS_DIRECTORIES)
    User.user_class_init()
    app.run(host="0.0.0.0", debug=True)         # TODO: remove debug=True

api.add_resource(UserApi, "{}user/<string:cmd>".format(_API_PREFIX),
    "{}/user/".format(_API_PREFIX))
api.add_resource(Files, "{}files/<path:client_path>".format(_API_PREFIX),
    "{}files/".format(_API_PREFIX))
api.add_resource(Actions, "{}actions/<string:cmd>".format(_API_PREFIX))

if __name__ == "__main__":
    main()
