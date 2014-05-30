#!/usr/bin/env python
#-*- coding: utf-8 -*-

import datetime
from flask import Flask
from flask import request
from flask.ext.httpauth import HTTPBasicAuth

app = Flask(__name__)
auth = HTTPBasicAuth()

# username : password
users = {
	"testUser" : "propropro",
}

@auth.get_password
def get_pw(username):
	print username
	if username in users:
		return users[username]
	return None

@app.route("/hidden_page")
@auth.login_required
def hidden_page():
	return "Hello {}".format(auth.username())

@app.route("/create_user", methods=["POST"])
# this method takes only 'user' and 'psw' as POST variables
def create_user():
	if not ("user" in request.form and "psw" in request.form):
		return "400 Bad Request"
	if request.form["user"] in users:
		return "Error! Another user has your nickname\n" 	# TODO: code?
	
	users[request.form["user"]] = request.form["psw"]
	return "User created!\n"

@app.route("/")
def welcome():
	local_time = datetime.datetime.now()
	formatted_time = local_time.strftime("%Y-%m-%d %H:%M")
	return "Welcome on the Server!\n{}\n".format(formatted_time)

def main():
	app.run()

if __name__ == '__main__':
	main()