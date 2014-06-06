#!/usr/bin/env python
#-*- coding: utf-8 -*-

from flask import Flask, request, abort
from flask.ext.httpauth import HTTPBasicAuth
from passlib.hash import sha256_crypt, md5_crypt
import datetime
import os

app = Flask(__name__)
auth = HTTPBasicAuth()
USERS_DIRECTORIES = "user_dirs/"

users = {}
# { 
#     username : { 
#            psw : encoded_password,
#            paths : list_of_path
#     }
# }


class IdCreator(object):
    last_id = None

    @classmethod
    def get_id(cls):
        new_id = md5_crypt(datetime.datetime.now())
        if new_id == cls.last_id:
            return id_creator
        else:
            cls.last_id = new_id
            return  new_id


@auth.verify_password
def verify_password(username, password):
    return sha256_crypt.verify(password, users[username][psw])

def access_permission(f):
    def verify_path(username, path):
        for p in users[username]['paths']:
            if p == path:
                return f(username, path)
        else: raise access_denied('you are not allowed to access to this directory')

@app.route("/hidden_page")
@auth.login_required
def hidden_page():
    return "Hello {}".format(auth.username())


@app.route("/create_user", methods=["POST"])
# this method takes only 'user' and 'psw' as POST variables
def create_user():
    if not ("user" in request.form
            and "psw" in request.form
            and len(request.form) == 2):
        abort(400)      # Bad Request
    if request.form["user"] in users:
        abort(409)      # Conflict
    psw_hash = sha256_crypt.encrypt(request.form["psw"])

    dir_id = IdCreator.get_id()
    os.mkdir(os.path.join(USERS_DIRECTORIES, dir_id))
    
    users[request.form["user"]] = { 
        psw: psw_hash,
        paths : [dir_id]
    }
    return "User created!\n", 201


@app.route("/")
def welcome():
    local_time = datetime.datetime.now()
    formatted_time = local_time.strftime("%Y-%m-%d %H:%M")
    return "Welcome on the Server!\n{}\n".format(formatted_time)


@app.route("/download/<file_name>")
@auth.login_required
def download(file_name):
    """this function return file content as string by get"""
    if os.path.exists(file_name):
        with open(file_name, "r") as tmp:
            return tmp.read()


@app.route("/upload/<username>", methods=["POST"])
@auth.login_required
def upload(username):
    """this function load file by POST"""
    f = request.files['data']
    f.save(f.filename)
    return "", 201


def main():
    app.run(debug=True)         # TODO: remove debug=True

if __name__ == '__main__':
    main()
