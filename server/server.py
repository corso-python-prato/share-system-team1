#!/usr/bin/env python
#-*- coding: utf-8 -*-

from flask.ext.restful import reqparse, abort, Api, Resource
from flask.ext.mail import Mail, Message
from passlib.hash import sha256_crypt
from flask.ext.httpauth import HTTPBasicAuth
from flask import Flask, request
from server_errors import *
import ConfigParser
import hashlib
import shutil
import time
import json
import os


HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_GONE = 410

app = Flask(__name__)
api = Api(app)
auth = HTTPBasicAuth()
_API_PREFIX = "/API/v1/"

USERS_DIRECTORIES = "user_dirs/"
USERS_DATA = "user_data.json"
PENDING_USERS = ".pending.tmp"
CORRUPTED_DATA = "corrupted_data"
EMAIL_SETTINGS_INI = "email_settings.ini"

SERVER_ROOT = os.path.dirname(__file__)
USERS_DIRECTORIES = os.path.join(SERVER_ROOT, "user_dirs/")
USERS_DATA = os.path.join(SERVER_ROOT, "user_data.json")

parser = reqparse.RequestParser()
parser.add_argument("task", type=str)


def to_md5(full_path=None, block_size=2 ** 20, file_object=False):
    """ if path is a file, return a md5;
    if path is a directory, return False
    if file_object is defined file_object content md5"""
    if file_object:
        m = hashlib.md5()
        for chunk in iter(lambda: file_object.read(block_size), b''):
            m.update(chunk)
        return m.hexdigest()

    if os.path.isdir(full_path):
        return None
    m = hashlib.md5()
    with open(full_path, 'rb') as f:
        for chunk in iter(lambda: f.read(block_size), b''):
            m.update(chunk)
    return m.hexdigest()


def can_write(username, server_path):
    """
    This sharing system is in read-only mode.
    Check if an user is the owner of a file (or father directory).
    (the server_path begins with his name)
    """
    return server_path.split('/')[0] == username


class User(object):
    """
    Maintaining two dictionaries:
        · paths     = { client_path : [server_path, md5/None, timestamp] }
        None instead of the md5 means that the path is a directory.
        · shared_resources: { server_path : [owner, ben1, ben2, ...] }
    The full path to access to the file is a join between USERS_DIRECTORIES and
    the server_path.
    """
    users = {}
    shared_resources = {}

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
            for u, v in saved["users"].iteritems():
                User(u, None, from_dict=v)

    @classmethod
    def save_users(cls, filename=None):
        if not filename:
            filename = USERS_DATA

        to_save = {
            "users": {}
        }
        for u, v in cls.users.iteritems():
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
            self.username = username
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
        self.username = username
        self.psw = password
        #self.psw = psw_hash

        # path of each file and each directory of the user:
        #     { client_path : [server_path, md5, timestamp] }
        self.paths = {}

        # timestamp of the last change in the user's files
        self.timestamp = time.time()

        # update users, file
        self.push_path("", username, update_user_data=False)
        User.users[username] = self
        User.save_users()

    def to_dict(self):
        return {
            "psw": self.psw,
            "paths": self.paths,
            "timestamp": self.timestamp
        }

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

        # check if the user can write in that server directory
        new_client_path = father
        new_server_path = self.paths[father][0]

        if not can_write(self.username, new_server_path):
            return False

        # create all the new subdirs and add them to paths
        for d in to_be_created:
            new_client_path = os.path.join(new_client_path, d)
            new_server_path = os.path.join(new_server_path, d)
            # create these directories on disk
            full_path = os.path.join(USERS_DIRECTORIES, new_server_path)
            if not os.path.exists(full_path):
                os.makedirs(full_path)
            # update the structure
            self.push_path(
                new_client_path,
                new_server_path,
                update_user_data=False
            )

        return os.path.join(new_server_path, filename)

    def _get_shared_root(self, server_path):
        """
        From a server_path, generate a valid shared root.
        """
        path_parts = server_path.split("/")
        # if len(path_parts) > 3:
        #     # shared resource has to be in owner's root
        #     return False

        resource_name = path_parts.pop()
        return os.path.join("shares", self.username, resource_name)

    def _get_ben_path(self, server_path):
        """
        Search a shared father for the resource. If it exists, return the
        shared resource name and the ben_path, else return False.
        """
        for shared_server_path, beneficiaries in \
                User.shared_resources.iteritems():
            if server_path.startswith(shared_server_path):
                ben_path = server_path.replace(
                    shared_server_path,
                    self._get_shared_root(shared_server_path),
                    1
                )
                return shared_server_path, ben_path
        return False

    def push_path(self, client_path, server_path, update_user_data=True,
                  only_modify=False):
        md5 = to_md5(os.path.join(USERS_DIRECTORIES, server_path))
        now = time.time()
        file_meta = [server_path, md5, now]
        self.paths[client_path] = file_meta

        is_shared = self._get_ben_path(server_path)
        if is_shared:
            share, ben_path = is_shared

            # upgrade every beneficiaries
            for ben_name in User.shared_resources[share][1:]:
                ben_user = User.get_user(ben_name)
                if not only_modify:
                    ben_user.paths[ben_path] = file_meta
                ben_user.timestamp = now

        if update_user_data:
            self.timestamp = now
            User.save_users()

    def rm_path(self, client_path):
        """
        Remove the path from the paths dictionary. If there are empty
        directories, remove them from the filesystem.
        """
        now = time.time()
        self.timestamp = now

        # remove empty directories
        directory_path, filename = os.path.split(client_path)
        if directory_path != "":
            dir_list = directory_path.split("/")

            while len(dir_list) > 0:
                client_subdir = os.path.join(*dir_list)
                server_subdir = self.paths[client_subdir][0]
                try:
                    # step 1: remove from filesystem
                    os.rmdir(os.path.join(USERS_DIRECTORIES, server_subdir))
                except OSError:
                    # the directory is not empty
                    break
                else:
                    # step 2: remove from shared beneficiary's paths
                    is_shared = self._get_ben_path(server_subdir)
                    if is_shared:
                        shared_server_path, ben_path = is_shared
                        for ben_name in \
                                User.shared_resources[shared_server_path][1:]:
                            ben_user = User.get_user(ben_name)
                            del ben_user.paths[ben_path]
                    # step 3: remove from paths
                    del self.paths[client_subdir]
                    dir_list.pop()

        # remove from shared beneficiary's paths
        is_shared = self._get_ben_path(self.paths[client_path][0])
        if is_shared:
            shared_server_path, ben_path = is_shared
            for ben_name in User.shared_resources[shared_server_path][1:]:
                ben_user = User.get_user(ben_name)
                del ben_user.paths[ben_path]
                ben_user.timestamp = now
            # if the shared resource is a removed file or an empty directory
            # remove it from shared_resources
            if not os.path.exists(shared_server_path):
                del User.shared_resources[shared_server_path]

        # remove the argument client_path and save
        del self.paths[client_path]
        User.save_users()

    def delete_user(self, username):
        user_root = self.paths[""][0]
        del User.users[username]
        shutil.rmtree(user_root)
        User.save_users()

    def add_share(self, client_path, beneficiary):
        try:
            server_path = self.paths[client_path][0]
            ben = User.users[beneficiary]
        except KeyError:
            # invalid client_path or the beneficiary is not an user
            return False

        if server_path not in User.shared_resources:
            User.shared_resources[server_path] = [self.username, beneficiary]
        else:
            User.shared_resources[server_path].append(beneficiary)

        new_client_path = self._get_shared_root(server_path)

        # The item referenced in ben.paths and in the owner's paths is the
        # same. If modified, the both are update.
        ben.paths[new_client_path] = self.paths[client_path]

        if self.paths[client_path][1] is None:
            # If client_path is a directory, add to the beneficiary's paths
            # every file and folder in the shared folder
            for path, value in self.paths.iteritems():
                if path.startswith(client_path):
                    to_insert = path.replace(client_path, new_client_path, 1)
                    ben.paths[to_insert] = value

        ben.timestamp = time.time()
        User.save_users()
        return True


class Resource_with_auth(Resource):
    method_decorators = [auth.login_required]


class UsersApi(Resource):

    def load_pending_users(self):
        pending = {}
        if os.path.isfile(PENDING_USERS):
            try:
                with open(PENDING_USERS, "r") as p_u:
                    pending = json.load(p_u)
            except ValueError:  # PENDING_USERS exists but is corrupted
                if os.path.getsize(PENDING_USERS) > 0:
                    shutil.copy(PENDING_USERS, CORRUPTED_DATA)
                    os.remove(PENDING_USERS)
                else:           # PENDING_USERS exists but is empty
                    pending = {}
        return pending

    def post(self, username):
        """Create a user registration request
        Expected {"psw": <password>}
        save pending as
        {<username>:
            {
            "password": <password>,
            "code": <activation_code>
            "timestamp": <timestamp>
            }
        }"""
        pending = self.load_pending_users()

        try:
            psw = request.form["psw"]
        except KeyError:
            return "Missing password", HTTP_BAD_REQUEST

        if username in pending:
            return "This user have arleady a pending request", HTTP_CONFLICT
        elif username in User.users:
            return "This user already exists", HTTP_CONFLICT
        else:
            psw_hash = sha256_crypt.encrypt(psw)
            code = os.urandom(16).encode('hex')
            send_mail(username, "RawBox activation code", code)
            pending[username] = \
                {"password": psw_hash,
                 "code": code,
                 "timestamp": time.time()}

            with open(PENDING_USERS, "w") as p_u:
                json.dump(pending, p_u)
            return "User added to pending users", HTTP_CREATED

    def put(self, username):
        """Activate a pending user
        Expected
        {"code": <activation code>}"""
        try:
            code = request.form["code"]
        except KeyError:
            return "Missing activation code", HTTP_BAD_REQUEST

        if username in User.users:
            return "This user is already active", HTTP_CONFLICT

        pending = self.load_pending_users()

        if username in pending:
            if code == pending[username]["code"]:
                User(username, pending[username]["password"])
                del pending[username]
                if pending:
                    with open(PENDING_USERS, "w") as p_u:
                        json.dump(pending, p_u)
                else:
                    os.remove(PENDING_USERS)
                return "User activated", HTTP_CREATED
            else:
                return "Wrong code", HTTP_NOT_FOUND
        else:
            return "User need to be created", HTTP_NOT_FOUND

    @auth.login_required
    def delete(self, username):
        """Delete the user who is making the request
        """
        current_username = auth.username()
        current_user = User.get_user(current_username)
        if current_username == username:
            current_user.delete_user(username)
            return "user deleted", HTTP_OK
        else:
            return "access denied", HTTP_BAD_REQUEST


class Files(Resource_with_auth):
    def _diffs(self):
        """ Send a JSON with the timestamp of the last change in user
        directories and an md5 for each file
        Expected GET method without path """
        u = User.get_user(auth.username())
        tree = {}
        for p, v in u.paths.iteritems():
            if v[1] is None:
                # the path p is a directory
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
        try:
            full_path = os.path.join(
                USERS_DIRECTORIES, u.paths[client_path][0]
            )
        except KeyError:
            return "File unreachable", HTTP_NOT_FOUND

        try:
            f = open(full_path, "rb")
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

        try:
            server_path = u.paths[client_path][0]
        except KeyError:
            abort(HTTP_NOT_FOUND)

        if not can_write(u.username, server_path):
            abort(HTTP_FORBIDDEN)

        f = request.files["file_content"]

        if request.form["file_md5"] != to_md5(file_object=f):
            abort(HTTP_BAD_REQUEST)

        f.seek(0)
        f.save(os.path.join(USERS_DIRECTORIES, server_path))
        u.push_path(client_path, server_path, only_modify=True)
        return u.timestamp, HTTP_CREATED

    def post(self, client_path):
        """ Upload
        Upload a new file
        Expected as POST data:
        { "file_content" : <file>} """
        u = User.get_user(auth.username())

        if client_path in u.paths:
            # The file is already present. To modify it, use PUT, not POST
            abort(HTTP_CONFLICT)

        server_path = u.create_server_path(client_path)
        if not server_path:
            # the server_path belongs to another user
            abort(HTTP_FORBIDDEN)

        f = request.files["file_content"]

        if request.form["file_md5"] != to_md5(file_object=f):
            abort(HTTP_BAD_REQUEST)

        f.seek(0)
        f.save(os.path.join(USERS_DIRECTORIES, server_path))
        u.push_path(client_path, server_path)
        return u.timestamp, HTTP_CREATED


class Actions(Resource_with_auth):
    def _delete(self):
        """ Expected as POST data:
        { "path" : <path>} """
        # check user and path
        u = User.get_user(auth.username())
        client_path = request.form["path"]
        try:
            server_path = u.paths[client_path][0]
        except KeyError:
            abort(HTTP_NOT_FOUND)
        if not can_write(u.username, server_path):
            abort(HTTP_FORBIDDEN)

        # change on disk!
        os.remove(os.path.join(USERS_DIRECTORIES, server_path))

        # change the structure
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

        try:
            server_src = u.paths[client_src][0]
        except KeyError:
            abort(HTTP_NOT_FOUND)

        server_dest = u.create_server_path(client_dest)
        if not server_dest:
            # the server_path belongs to another user
            abort(HTTP_FORBIDDEN)

        # changes on disk!
        full_src = os.path.join(USERS_DIRECTORIES, server_src)
        full_dest = os.path.join(USERS_DIRECTORIES, server_dest)
        try:
            if keep_the_original:
                shutil.copy(full_src, full_dest)
            else:
                shutil.move(full_src, full_dest)
        except shutil.Error:
            return abort(HTTP_CONFLICT)         # TODO: check.
        else:
            # update the structure
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


class Shares(Resource):
    def post(self, client_path, beneficiary):
        owner = User.get_user(auth.username())

        if not owner.add_share(client_path, beneficiary):
            abort(HTTP_BAD_REQUEST)     # TODO: choice the code
        else:
            return HTTP_OK              # TODO: timestamp is needed here?

    def _remove_beneficiary(self, owner, server_path, client_path,
                            beneficiary):
        # remove the beneficiary from the shared resources list
        try:
            ben_user = User.get_user(beneficiary)
            User.shared_resources[server_path].remove(beneficiary)
        except (KeyError, ValueError):
            abort(HTTP_BAD_REQUEST)

        if len(User.shared_resources[server_path]) == 1:
            # the resource isn't shared with anybody.
            # (the first user in the list is the owner)
            del User.shared_resources[server_path]

        # remove every resource which isn't shared anymore
        ben_path = owner._get_shared_root(server_path)
        for client_path in ben_user.paths.keys():
            if client_path.startswith(ben_path):
                del ben_user.paths[client_path]

        # update timestamp and save
        ben_user.timestamp = time.time()
        User.save_users()
        return HTTP_OK

    def _remove_share(self, owner, server_path, client_path):
        try:
            for ben in User.shared_resources[server_path][1:]:
                self._remove_beneficiary(owner, server_path, client_path, ben)
        except KeyError:
            abort(HTTP_BAD_REQUEST)
        else:
            User.save_users()
            return HTTP_OK

    def delete(self, client_path, beneficiary=None):
        owner = User.get_user(auth.username())
        try:
            server_path = owner.paths[client_path][0]
        except KeyError:
            return "The specified file or directory is not present", \
                HTTP_BAD_REQUEST

        if beneficiary:
            return self._remove_beneficiary(
                owner, server_path, client_path, beneficiary
            )
        else:
            return self._remove_share(owner, server_path, client_path)


class MissingConfigIni(Exception):
    pass


def mail_config_init():
    config = ConfigParser.ConfigParser()
    if config.read(EMAIL_SETTINGS_INI):
        app.config.update(
            MAIL_SERVER = config.get('email', 'smtp_address'),
            MAIL_PORT = config.getint('email', 'smtp_port'),
            MAIL_USERNAME = config.get('email', 'smtp_username'),
            MAIL_PASSWORD = config.get('email', 'smtp_password')
        )
        mail = Mail(app)
        return mail
    else:
        raise MissingConfigIni


def send_mail(receiver, obj, content):
    """ Send an email to the 'receiver', with the
    specified object ('obj') and the specified 'content' """
    mail = mail_config_init()
    msg = Message(
        obj,
        sender="RawBoxTeam",
        recipients=[receiver])
    msg.body = content
    with app.app_context():
        mail.send(msg)


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
        os.makedirs(USERS_DIRECTORIES)
    User.user_class_init()
    app.run(host="0.0.0.0", debug=True)         # TODO: remove debug=True

api.add_resource(UsersApi, "{}Users/<string:username>".format(_API_PREFIX))
api.add_resource(Actions, "{}actions/<string:cmd>".format(_API_PREFIX))
api.add_resource(
    Files,
    "{}files/<path:client_path>".format(_API_PREFIX),
    "{}files/".format(_API_PREFIX))
api.add_resource(
    Shares,
    "{}shares/<path:client_path>".format(_API_PREFIX),
    "{}shares/<path:client_path>/<string:beneficiary>".format(_API_PREFIX))

if __name__ == "__main__":
    main()
