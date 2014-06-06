#!/usr/bin/env python
#-*- coding: utf-8 -*-
 
class Response(object):
	headers = 'text/plain'
	encoding =  'UTF-8'
	text = 'OK'
	status_code = 500

def post(url, data):
	return Response()