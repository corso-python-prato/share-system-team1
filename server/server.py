#!/usr/bin/env python
#-*- coding: utf-8 -*-

from flask import Flask, request, abort
from flask.ext.httpauth import HTTPBasicAuth
from passlib.hash import sha256_crypt
import datetime
import time
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
    ''' creates univoque IDs, used as users' directories name '''
    counter_id = 0

    @classmethod
    def get_id(cls):
        new_id = hex(cls.counter_id)[2:]
        cls.counter_id += 1    
        return  new_id


@auth.verify_password
def verify_password(username, password):
    return sha256_crypt.verify(password, users[username]['psw'])


def verify_path(username, path):
    #verify if the path is in the user accesses
    for p in users[username]['paths']:
        if p == path:
            return True
    else: return False

def access_permission(username,path):
    if  not verify_path(username, path):
        abort(500)
    

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


@app.route("/download/<path>")
@auth.login_required
def download(path):
    """this function return file content as string by get"""
    access_permission(auth.username())
    if os.path.exists(path):
        with open(path, "r") as tmp:
            return 200, tmp.read()
    else:
        return abort(404)


@app.route("/upload/<path>", methods=["POST"])
@auth.login_required
def upload(path):
    """this function load file by POST"""
    access_permission(auth.username())
    f = request.files['data']
    f.save(f.filename)
    return "", 201


@app.route("/modify/<path>", methods=["PUT"])
@auth.login_required
def modify(path):
    """this function modify file by PUT"""
    access_permission(auth.username())
    if os.path.exists(path):
        upload(path)
    else:
        return abort(404)

def main():
    app.run(debug=True)         # TODO: remove debug=True

if __name__ == '__main__':
    main()
