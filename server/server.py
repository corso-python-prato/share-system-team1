#!/usr/bin/env python
#-*- coding: utf-8 -*-

import datetime
from flask import Flask, request, abort
from flask.ext.httpauth import HTTPBasicAuth
from passlib.hash import md5_crypt

app = Flask(__name__)
auth = HTTPBasicAuth()

users = {}		# username : encoded_password

@auth.verify_password
def verify_password(username, password):
	return md5_crypt.verify(password, users[username])

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
		abort(400)		# Bad Request
	if request.form["user"] in users:
		abort(409) 		# Conflict
	psw_hash = md5_crypt.encrypt(request.form["psw"])
	users[request.form["user"]] = psw_hash
	return "User created!\n", 201

@app.route("/")
def welcome():
	local_time = datetime.datetime.now()
	formatted_time = local_time.strftime("%Y-%m-%d %H:%M")
	return "Welcome on the Server!\n{}\n".format(formatted_time)

def main():
	app.run(debug=True)			# TODO: remove debug=True

if __name__ == '__main__':
	main()