#!/usr/bin/env python
#-*- coding: utf-8 -*-

from flask.ext.restful import reqparse, abort, Api, Resource
from flask.ext.mail import Mail, Message
from passlib.hash import sha256_crypt
from flask.ext.httpauth import HTTPBasicAuth
from flask import Flask, request, send_file
import passwordmeter
import ConfigParser
import hashlib
import shutil
import time
import json
import os
import traceback
import sys


HTTP_OK = 200
HTTP_CREATED = 201
HTTP_ACCEPTED = 202
HTTP_BAD_REQUEST = 400
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_NOT_ACCEPTABLE = 406
HTTP_CONFLICT = 409


app = Flask(__name__)


class ServerApi(Api):
    """This class is a subclass of Api class from flask restful"""
    enable_report_mail = False

    def handle_error(self, e):
        """This (ovverrided) method implements handling of unhandled errors
        @param e Exception
        @return a 500 error message response or use the default error handler 
        """
        code = getattr(e, "code", 500)
        # not expected exception
        if code == 500 and ServerApi.enable_report_mail:
            # create the object and the body of the email report
            obj, msg = create_traceback_report(sys.exc_info())
            # ... and send it to a (eventual) mail list
            report_emails = load_emails()
            if report_emails:
                for mail in report_emails:
                    send_mail(mail, obj, msg)
            print msg
            return self.make_response({"message": "Internal Error Server!",
                                       "error_code": "Unexpected"}, code)
        return super(ServerApi, self).handle_error(e)


api = ServerApi(app)
auth = HTTPBasicAuth()
_API_PREFIX = "/API/v1/"
PROJECT_NAME = "RawBox"



SERVER_ROOT = os.path.dirname(__file__)
USERS_DIRECTORIES = os.path.join(SERVER_ROOT, "user_dirs/")
USERS_DATA = os.path.join(SERVER_ROOT, "user_data.json")
PENDING_USERS = os.path.join(SERVER_ROOT, ".pending.tmp")
CORRUPTED_DATA = os.path.join(SERVER_ROOT, "corrupted_data.json")
EMAIL_SETTINGS_INI = os.path.join(SERVER_ROOT, "email_settings.ini")
EMAIL_REPORT_INI = os.path.join(SERVER_ROOT, "email_report.ini")
PASSWORD_NOT_ACCEPTED_DATA = os.path.join(
    SERVER_ROOT, "password_not_accepted.txt"
)
RESET_REQUESTS = os.path.join(SERVER_ROOT, ".reset_requests.tmp")

parser = reqparse.RequestParser()
parser.add_argument("task", type=str)


def load_emails():
    """This function reads in email_report.ini all e-mail 
    and return them as a list
    @return None or a list of emails
    """
    try:
        with open(EMAIL_REPORT_INI, "r") as f:
            return f.read().split("\n")
    except IOError:
        return None


def create_traceback_report(exc_params, testing=False):
    """This function creates the report with traceback 
    of unhandled error to send via email(s)
    @param exc_params It is a tuple (type, value, traceback) 
    relative to a raised exception.
    @return It returns two strings, the first one the object of email(s)
    and the second one the body of the message
    """
    # get exception info and the traceback object (stack of calls)
    exc_type, exc_msg, tb = exc_params
    if exc_type and exc_msg and tb:
        # looping all frames and save them in call_stack
        # reversing their order
        while True:
            if not tb.tb_next:
                break
            tb = tb.tb_next
        call_stack = []
        last_frame = tb.tb_frame
        while last_frame:
            call_stack.append(last_frame)
            last_frame = last_frame.f_back
        call_stack.reverse()
        # set object text and form in a better way
        # the body of message
        obj = "RawBox Server Error Dump"
        msg = []
        msg.append("--Traceback--\n\n")
        # traceback
        msg.append(str(traceback.format_exc()))
        msg.append("\n\n-------------\n\n")
        # dump of variables and their values
        # in every frame
        msg.append("--Local variables dump--\n\n")
        for level in call_stack:
            module = level.f_code.co_filename
            # filter the module name
            if module == "server.py" or testing:
                msg.append("Frame: {} ".format(level.f_code.co_name))
                msg.append("\tModule: {}".format(module))
                msg.append("\tLine: {}".format(str(level.f_lineno)))
                msg.append("\nVars: {}".format(str(level.f_code.co_varnames)))
                msg.append("\n\n")
                for k, v in level.f_locals.iteritems():
                    msg.append("\t{}={}".format(k, str(v)))
                    msg.append("\n")
                msg.append("\n\n")
        msg.append("\n\n")
        return obj, "".join(msg)
    return None, None


def to_md5(full_path=None, block_size=2 ** 20, file_object=False):
    """This function generates a md5 for a file
    @param full_path The full path of the file, set to None as default
    @param block_size The size of the blocks to read from the file
    @file_object The file object, set to False as default
    @return False if the input path is a directory or the md5
    """
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
    """This function checks if an user 
    it is the owner of a file (or father directory)
    P.S.: This sharing system is in read-only mode. 
    root/shares is a reserved name.
    @param username User to check
    @param server_path The path of the file 
    to check (the server_path begins with the user)
    @return True if the User is the owner else return False
    """
    pieces = server_path.split('/')
    return (pieces[0] == username) and \
        ((len(pieces) == 1) or (pieces[1] != "shares"))


def PasswordChecker(clear_password):
    """This function checks if the password to create is secure
    @param clear_password The password to examinate
    @return the password if the test pass or an error message if the test fails
    """
    # if the password is too short
    if len(clear_password) <= 5:
        return "This password is too short, the password " + \
            "must be at least 6 characters", HTTP_NOT_ACCEPTABLE
    # if the password is too common
    f = open(PASSWORD_NOT_ACCEPTED_DATA)
    lines = f.readlines()
    f.close()
    for line in lines:
        for word in line.split():
            if clear_password == word:
                return "This password is too common, the password " + \
                    "must be something unusual", HTTP_NOT_ACCEPTABLE
    # if the password is too easy
    strength, _ = passwordmeter.test(clear_password)
    if strength < 0.5:
        return "This password is too easy, the password should " + \
            "be a combination of numbers, uppercase and lowercase" + \
            "characters and special characters", HTTP_NOT_ACCEPTABLE
    return clear_password


class MissingConfigIni(Exception):
    """This an Exception to raise when the config .ini is missing"""
    pass


class User(object):
    """This class handles the users resouces maintaining two dictionaries:
        · paths = { client_path : [server_path, md5/None, timestamp] }
        None instead of the md5 means that the path is a directory.
        · shared_resources: { server_path : [ben1, ben2, ...] }
    The full path to access to the file is a join between USERS_DIRECTORIES and
    the server_path.
    """
    users = {}
    shared_resources = {}

    # CLASS AND STATIC METHODS
    @staticmethod
    def user_class_init():
        """This static method load users data from .json, if it exists"""
        try:
            ud = open(USERS_DATA, "r")
            saved = json.load(ud)
            ud.close()
        except IOError:
            pass
            # The json file is not present. It will be created a new structure
            # from scratch.
        # If the json file is corrupted, it will be raised a ValueError here.
        # In that case, please remove the corrupted file.
        else:
            for u, v in saved["users"].iteritems():
                User(u, None, from_dict=v)

    @classmethod
    def save_users(cls, filename=None):
        """This class method save in a .json the users data
        @param filename This is the filename for the json, 
        set to None as default.
        """
        if not filename:
            filename = USERS_DATA

        to_save = {
            "users": {}
        }
        for u, v in cls.users.iteritems():
            to_save["users"][u] = v.to_dict()

        with open(filename, "w") as f:
            json.dump(to_save, f)

    # DYNAMIC METHODS
    def __init__(self, username, password, from_dict=None):
        """The constructor
        @param username 
        @param password
        @param from_dict An object containing user's data, 
        set to None as default
        """
        # if restoring the server:
        if from_dict:
            self.username = username
            self.psw = from_dict["psw"]
            self.paths = from_dict["paths"]
            self.timestamp = from_dict["timestamp"]
            User.users[username] = self
            return

        # else, if a real new user is being created:
        full_path = os.path.join(USERS_DIRECTORIES, username)
        os.mkdir(full_path)
        # If a directory with the same name of the user is already present,
        # it will be raised an OSError here. It shouldn't happen, if the server
        # works right.

        # OBJECT ATTRIBUTES
        self.username = username
        self.psw = password
        self.paths = {}

        # timestamp of the last change in the user's files
        self.timestamp = time.time()

        # update users, file
        self.push_path("", username, update_user_data=False)
        self.push_path(
            "shares/DO NOT WRITE HERE.txt",
            "not_write_in_share_model.txt",
            update_user_data=False
        )
        User.users[username] = self
        User.save_users()

    def to_dict(self):
        """This method returns a dictionary containing the user's data"""
        return {
            "psw": self.psw,
            "paths": self.paths,
            "timestamp": self.timestamp
        }

    def create_server_path(self, client_path):
        """This method create a new path on the server for user
        """
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
        """This method from a server_path, generate a valid shared root
        @param server_path
        @return the correct shared root
        """
        resource_name = server_path.split("/")[-1]
        return os.path.join("shares", self.username, resource_name)

    def _get_ben_path(self, server_path):
        """This method search for a shared father for the resource. 
        If it exists, return the shared resource name and the ben_path, 
        else return False.
        @param server_path
        @return False or the shared resource name and the beneficiary path
        """
        for shared_server_path in User.shared_resources.iterkeys():
            if server_path.startswith(shared_server_path):
                ben_path = server_path.replace(
                    shared_server_path,
                    self._get_shared_root(shared_server_path),
                    1
                )
                return shared_server_path, ben_path
        return False

    def push_path(
            self, client_path, server_path, update_user_data=True,
            only_modify=False):
        """This method updates the resources data
        @param client_path
        @param server_path
        @param update_user_data If it is set on True the users' data are saved. 
        It is set on True as default
        @param only_modify If it is set on False 
        the beneficiaries paths are updated. 
        It is set on False as default
        """
        md5 = to_md5(os.path.join(USERS_DIRECTORIES, server_path))
        now = time.time()
        file_meta = [server_path, md5, now]
        self.paths[client_path] = file_meta

        is_shared = self._get_ben_path(server_path)
        if is_shared:
            share, ben_path = is_shared

            # upgrade every beneficiaries
            for ben_name in User.shared_resources[share]:
                ben_user = User.users[ben_name]
                if not only_modify:
                    ben_user.paths[ben_path] = file_meta
                ben_user.timestamp = now

        if update_user_data:
            self.timestamp = now
            User.save_users()

    def rm_path(self, client_path):
        """This method removes the path from the paths dictionary. 
        If there are empty directories, remove them from the filesystem.
        @param client_path
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
                                User.shared_resources[shared_server_path]:
                            ben_user = User.users[ben_name]
                            del ben_user.paths[ben_path]
                    # step 3: remove from paths
                    del self.paths[client_subdir]
                    dir_list.pop()

        # remove from shared beneficiary's paths
        is_shared = self._get_ben_path(self.paths[client_path][0])
        if is_shared:
            shared_server_path, ben_path = is_shared
            for ben_name in User.shared_resources[shared_server_path]:
                ben_user = User.users[ben_name]
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
        """This method removes an user and all user's data
        @param username
        """
        user_root = self.paths[""][0]
        del User.users[username]
        shutil.rmtree(os.path.join(USERS_DIRECTORIES, user_root))
        User.save_users()

    def add_share(self, client_path, beneficiary):
        """This method shares a resource with a beneficiary user
        @param client_path
        @param beneficiary
        @return An error message or True
        """
        if self.username == beneficiary:
            return "You can't share things with yourself."
        if len(client_path.split("/")) > 1:
            return "You can't share something in a subdir."

        try:
            server_path = self.paths[client_path][0]
            ben = User.users[beneficiary]
        except KeyError:
            return "Invalid client_path or the beneficiary is not an user"

        if server_path not in User.shared_resources:
            User.shared_resources[server_path] = [beneficiary]
        elif beneficiary in User.shared_resources[server_path]:
            return "Resource yet shared with that beneficiary"
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
    """This class inherits from Resource and provides 
    the login_required control to the subclasses
    """
    method_decorators = [auth.login_required]


class UsersApi(Resource):
    """This class (inheriting from Resource) handles the api for Users/ urls"""

    def load_pending_users(self):
        """This method load from file a json containing 
        the pending users (still not activated)
        @return pending The json with pending users inside
        """
        pending = {}
        if os.path.isfile(PENDING_USERS):
            try:
                with open(PENDING_USERS, "r") as p_u:
                    pending = json.load(p_u)
            except ValueError:  # PENDING_USERS exists but is corrupted
                if os.path.getsize(PENDING_USERS) > 0:
                    shutil.move(PENDING_USERS, CORRUPTED_DATA)
        return pending

    def load_reset_requests(self):
        """This method load from json the reset requests
        @return reset_requests The json with reset requests
        """
        reset_requests = {}
        if os.path.isfile(RESET_REQUESTS):
            try:
                with open(RESET_REQUESTS, "r") as reset_rq:
                    reset_requests = json.load(reset_rq)
            except ValueError:  # RESET_REQUESTS exists but is corrupted
                if os.path.getsize(RESET_REQUESTS) > 0:
                    shutil.move(RESET_REQUESTS, CORRUPTED_DATA)
                else:
                    return reset_requests
        return reset_requests

    def post(self, username):
        """This method (POST request) creates a user registration request
        Expected {"psw": <password>}
        save pending as
        {<username>:
            {
            "password": <password>,
            "code": <activation_code>
            "timestamp": <timestamp>
            }
        }
        if request.form["reset"] is True, it is a reset password request.
        In this case it saves request in a file, reset_requests, as
        {<username>: <resetting code>}
        @param username
        @return A http code with a return message
        """
        pending = self.load_pending_users()
        if request.form["reset"] == "True":
            if username in pending or username in User.users:
                reset_requests = self.load_reset_requests()
                code = os.urandom(16).encode('hex')
                send_mail(username, "RawBox' s resetting code", code)
                reset_requests[username] = code
                with open(RESET_REQUESTS, "w") as reset_rq:
                    json.dump(reset_requests, reset_rq)
                return "User added to resetting requests", HTTP_ACCEPTED
            else:
                return "User added to resetting requests", HTTP_ACCEPTED

        try:
            psw = request.form["psw"]
        except KeyError:
            return "Missing password", HTTP_BAD_REQUEST
        if username in pending:
            return "This user have already a pending request", HTTP_CONFLICT
        elif username in User.users:
            return "This user already exists", HTTP_CONFLICT
        if psw is not PasswordChecker(psw):
            return PasswordChecker(psw)
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
        """This method (PUT request) activates a pending user
        Expected
        {"code": <activation code>}
        if request.form["reset"] is True, it is a 
        set password request after reset one.
        In this case it set a new password 
        for the user (a pending or active one),
        if the reset code provided is correct.
        @param username
        @return A http code with a return message
        """
        pending = self.load_pending_users()

        if request.form["reset"] == "True":
            reset_requests = self.load_reset_requests()
            code = request.form["code"]
            psw = request.form["psw"]

            if username in reset_requests and reset_requests[username] == code:
                psw_hash = sha256_crypt.encrypt(psw)

                if username in pending:
                    pending[username]["password"] = psw_hash
                    del reset_requests[username]
                    with open(RESET_REQUESTS, "w") as reset_rq:
                        json.dump(reset_requests, reset_rq)
                    with open(PENDING_USERS, "w") as p_u:
                        json.dump(pending, p_u)
                    return "User's password resetted", HTTP_ACCEPTED
                else:
                    User.users[username].psw = psw_hash
                    del reset_requests[username]
                    with open(RESET_REQUESTS, "w") as reset_rq:
                        json.dump(reset_requests, reset_rq)
                    User.save_users()
                    return "User's password resetted", HTTP_ACCEPTED

            else:
                return "Reset request not found or wrong code", HTTP_NOT_FOUND

        try:
            code = request.form["code"]
        except KeyError:
            return "Missing activation code", HTTP_BAD_REQUEST

        if username in User.users:
            return "This user is already active", HTTP_CONFLICT

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
    def delete(self):
        """This method (DELETE request) deletes the user 
        who is making the request
        @return A http code with a return message
        """
        current_username = auth.username()
        User.users[current_username].delete_user(current_username)
        return "user deleted", HTTP_OK


class Files(Resource_with_auth):
    """This class (inheriting from Resource_with_auth) 
    handles the api for files/ urls
    """

    def _diffs(self):
        """This method send a JSON with the timestamp of the last change in user
        directories and an md5 for each file
        Expected GET method without path
        @return snapshot, HTTP_OK
        """
        u = User.users[auth.username()]
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
        """This method returns file content as a byte string
        Expected GET method with path
        @param client_path
        @return execution of send_file function
        """
        u = User.users[auth.username()]
        try:
            full_path = os.path.join(
                USERS_DIRECTORIES, u.paths[client_path][0]
            )
        except KeyError:
            return "File unreachable", HTTP_NOT_FOUND

        return send_file(full_path)

    def get(self, client_path=None):
        """This method handles a GET request and chooses what to do with
        client_path parameter value
        @param client_path
        @return Exceution of _diff or _download function
        """
        if not client_path:
            return self._diffs()
        else:
            return self._download(client_path)

    def put(self, client_path):
        """This method handles a PUT request to update an existing file
        Expected as POST data:
        { "file_content" : <file>}
        @param client_path
        @return a timestamp a http code if it does not abort
        """
        u = User.users[auth.username()]
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
        """This method handles a POST request to upload a new file
        Expected as POST data:
        { "file_content" : <file>}
        @param client_path
        @return a timestamp a http code if it does not abort
        """
        u = User.users[auth.username()]

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
    """This class (inheriting from Resource_with_auth) 
    handles the api for actions/ urls
    """

    def _delete(self):
        """This method handles an user resource cancellation
        Expected as POST data:
        { "path" : <path>}
        @return a timestamp or it aborts with a http code
        """
        # check user and path
        u = User.users[auth.username()]
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
        """This method call _transfer to copy an user resource
        @return Excecution of _transfer method 
        with keep_the_original set to True
        """
        return self._transfer(keep_the_original=True)

    def _move(self):
        """This method call _transfer to move an user resource
        @return Excecution of _transfer method 
        with keep_the_original set to False
        """
        return self._transfer(keep_the_original=False)

    def _transfer(self, keep_the_original=True):
        """This method moves or copy a file from src to dest
        depending on keep_the_original value
        Expected as POST data:
        { "file_src": <path>, "file_dest": <path> }
        @param keep_the_original This parameter indicates 
        if move or copy a resource. 
        It is set to True as default
        """
        u = User.users[auth.username()]
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
        """This method (POST request) execute one of the provivded commands
        @param cmd
        @return Excecution of cmd or aborting with a http code
        """
        try:
            return Actions.commands[cmd](self)
        except KeyError:
            return abort(HTTP_NOT_FOUND)


class Shares(Resource_with_auth):
    """This class (inheriting from Resource_with_auth) 
    handles the api for shares/ urls
    """

    def post(self, client_path, beneficiary):
        """This method (POST request) shares a resource with a beneficiary user
        @param client_path
        @param beneficiary
        @return a http code or False, http code
        """
        owner = User.users[auth.username()]

        result = owner.add_share(client_path, beneficiary)
        if result is not True:
            return result, HTTP_BAD_REQUEST
        else:
            return HTTP_OK          # TODO: timestamp is needed here?

    def _remove_beneficiary(self, owner, server_path, client_path,
                            beneficiary):
        """This method removes the beneficiary from the shared resources list
        @param owner
        @param server_path
        @param client_path
        @param beneficiary
        @return a http code or aborting with a http code
        """
        # remove the beneficiary from the shared resources list
        try:
            ben_user = User.users[beneficiary]
            User.shared_resources[server_path].remove(beneficiary)
        except (KeyError, ValueError):
            # beneficiary is not an user or the resource is not shared
            # or the resource is shared, but not with this beneficiary
            abort(HTTP_BAD_REQUEST)

        if len(User.shared_resources[server_path]) == 0:
            # the resource isn't shared with anybody.
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
        """This method remove a user's resource from the shares
        @param owner
        @param server_path
        @param client_path
        @return a http code or aborting with a http code
        """
        try:
            for ben in User.shared_resources[server_path]:
                self._remove_beneficiary(owner, server_path, client_path, ben)
        except KeyError:
            abort(HTTP_BAD_REQUEST)
        else:
            User.save_users()
            return HTTP_OK

    def delete(self, client_path, beneficiary=None):
        """This method (DELETE request) deletes a share or remove 
        a beneficiary user from shares
        @param client_path
        @param beneficiary Set to None as default
        @return Excecution of _remove_beneficiary or _remove_share 
        or returns a http code
        """
        owner = User.users[auth.username()]
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

    def get(self):
        """This method (GET request) return a list of user's shared resources
        @return The list (eventually empty) of shares and a http code
        """
        me = User.users[auth.username()]

        my_shares = {}
        # {client_path1: [ben1, ben2]}

        other_shares = {}
        # {owner : client_path}

        for server_path, bens in User.shared_resources.iteritems():
            parts = server_path.split("/")
            ownername = parts[0]

            if ownername == me.username:
                client_path = "/".join(parts[1:])
                my_shares[client_path] = bens
            elif me.username in bens:
                owner = User.users[ownername]
                other_shares[ownername] = (owner._get_shared_root(server_path))

        shares = {
            "my_shares": my_shares,
            "other_shares": other_shares
        }
        return shares, HTTP_OK


def mail_config_init():
    """This function load from .ini the configuration to send emails
    @return a Mail object or raise a MissingConfigIni Exception
    """
    config = ConfigParser.ConfigParser()
    if config.read(EMAIL_SETTINGS_INI):
        app.config.update(
            MAIL_SERVER=config.get('email', 'smtp_address'),
            MAIL_PORT=config.getint('email', 'smtp_port'),
            MAIL_USERNAME=config.get('email', 'smtp_username'),
            MAIL_PASSWORD=config.get('email', 'smtp_password')
        )
        return Mail(app)
    raise MissingConfigIni


def send_mail(receiver, obj, content):
    """This function send an email to the 'receiver', with the
    specified object ('obj') and the specified 'content'
    @param obj The object of the email
    @param content The content of the email
    """
    mail = mail_config_init()
    msg = Message(
        obj,
        sender="{}Team".format(PROJECT_NAME),
        recipients=[receiver])
    msg.body = content
    with app.app_context():
        mail.send(msg)


@auth.verify_password
def verify_password(username, password):
    if username not in User.users:
        return False
    else:
        return sha256_crypt.verify(password, User.users[username].psw)


def main():
    if not os.path.isdir(USERS_DIRECTORIES):
        os.makedirs(USERS_DIRECTORIES)
    User.user_class_init()
    ServerApi.enable_report_mail = True
    app.run(host="0.0.0.0", debug=False)

api.add_resource(
    UsersApi,
    "{}Users/<string:username>".format(_API_PREFIX),
    "{}Users/<string:username>/reset".format(_API_PREFIX),
    "{}Users/".format(_API_PREFIX))

api.add_resource(Actions, "{}actions/<string:cmd>".format(_API_PREFIX))
api.add_resource(
    Files,
    "{}files/<path:client_path>".format(_API_PREFIX),
    "{}files/".format(_API_PREFIX))
api.add_resource(
    Shares,
    "{}shares/".format(_API_PREFIX),
    "{}shares/<path:client_path>".format(_API_PREFIX),
    "{}shares/<path:client_path>/<string:beneficiary>".format(_API_PREFIX))

if __name__ == "__main__":
    main()
