#!/usr/bin/env python
#-*- coding: utf-8 -*-

from flask import Flask, request, abort
from flask.ext.httpauth import HTTPBasicAuth
from passlib.hash import sha256_crypt
import datetime
import os
from flask.ext.restful import reqparse, abort, Api, Resource


app = Flask(__name__)
auth = HTTPBasicAuth()
USERS_DIRECTORIES = "user_dirs/"
api = Api(app)


users = {}
# { 
#     username : { 
#            psw : encoded_password,
#            paths : list_of_path
#     }
# }


parser = reqparse.RequestParser()
parser.add_argument("task", type=str)

#todo
class Files(Resource):
    #@auth.login_required
    def get(self, path):
        """Download
        this function return file content as string using GET"""
        user_dir = "0"
        full_path = os.path.join("user_dirs", user_dir, path)
        if os.path.exists(full_path):
            with open(full_path, "r") as tmp:
                return tmp.read()
        else:
            return abort(404)

    # @app.route(`"/files/<path>")
    # @auth.login_required
    # def delete(self, path):
    #     """Delete
    #     """
    #     return "", 204
    
    # @app.route("/files/<path>")
    # @auth.login_required
    # def put(self, path):
    #     """Update
    #     this function modify file using PUT"""
    #     if os.path.exists(path):
    #         return "",201
    #     else:
    #         return abort(404)
    

    #@auth.login_required
    def post(self, path):
        """Upload
        this function load file using POST"""
        user_dir = "0"
        full_path = os.path.join("user_dirs", user_dir, request.form["file_name"])
        print full_path
        if os.path.exists(full_path):
            return "file gia' esistente", 409
        else:
            f = request.files["file_content"]
            os.chdir("user_dirs/0")
            f.save(request.form["file_name"])
            os.chdir(os.pardir)
            os.chdir(os.pardir)
            return "file upload done", 201



class IdCreator(object):
    """creates univoque IDs, used as users' directories name"""
    counter_id = 0

    @classmethod
    def get_id(cls):
        new_id = hex(cls.counter_id)[2:]
        cls.counter_id += 1    
        return  new_id


@auth.verify_password
def verify_password(username, password):
    if username not in users:
        return False
    return sha256_crypt.verify(password, users[username]["psw"])


def verify_path(username, path):
    #verify if the path is in the user accesses
    for p in users[username]["paths"]:
        if p == path:
            return True
    else: return False
    

@app.route("/hidden_page")
@auth.login_required
def hidden_page():
    return "Hello {}\n".format(auth.username())


@app.route("/create_user", methods=["POST"])
# this method takes only 'user' and 'psw' as POST variables
def create_user():
    if not ("user" in request.form
            and "psw" in request.form
            and len(request.form) == 2):
        abort(400)      # Bad Request
    if request.form["user"] in users:
        print "user esiste gia'"
        abort(409)      # Conflict
    psw_hash = sha256_crypt.encrypt(request.form["psw"])

    dir_id = IdCreator.get_id()
    dir_path = os.path.join(USERS_DIRECTORIES, dir_id)
    try:
        os.mkdir(dir_path)
    except OSError:
        print "la cartella esiste"
        abort(409)      # Conflict: the directory already exists
    
    users[request.form["user"]] = { 
        "psw": psw_hash,
        "paths" : [dir_id]
    }
    return "User created!\n", 201


@app.route("/")
def welcome():
    local_time = datetime.datetime.now()
    formatted_time = local_time.strftime("%Y-%m-%d %H:%M")
    return "Welcome on the Server!\n{}\n".format(formatted_time)


def main():
    if not os.path.isdir(USERS_DIRECTORIES):
        os.mkdir(USERS_DIRECTORIES)
    app.run(host="0.0.0.0",debug=True)         # TODO: remove debug=True


api.add_resource(Files, "/files/<path:path>")

if __name__ == "__main__":
    main()
