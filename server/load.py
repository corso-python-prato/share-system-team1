#!/usr/bin/env python
#-*- coding: utf-8 -*-

import requests
import os
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    print 'index'
    return 'Index Page'

@app.route('/hello/<prova>')
def hello(prova):
    print prova
    return prova

@app.route("/download/<file_name>")
def download(file_name):
    """questa funzione comunica col server tramite GET
    restituisce il contenuto del file come stringa"""
    print file_name
    if os.path.exists(file_name):
        print "sono dentro"
        with open (file_name, "r") as request:
            return file_name.read()

# @app.route("/upload/<file>", methods = ["POST", "GET"])
# def upload():
#     """questa funzione carichera' il file tramite metodo PUT"""
#     if request.method == "GET":
#         f = request.file['file_name']
#         f.save("/upload/file.txt")


if __name__ == '__main__':
    app.run()
