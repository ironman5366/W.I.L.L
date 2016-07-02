#External imports
import requests
import json

#Builtin imports
import logging
import urllib

#TODO: in the future (in the public betas) add a server to check nearest server and redirect to that

SERVER_IP = "107.170.142.65"

def post(url,data):
    post_url = "{0}/{1}".format(SERVER_IP,url)
    try:
        request = requests.post(post_url,data)
        return request.json
    except Exception as post_error:
        logging.error(post_error.message)
        return False

class session():
    '''Session management section'''
    def start(self, sessiondata):
        '''Start the session'''
        return post("/start_session",sessiondata)
    def end(self, sessiondata):
        return post("/end_session",sessiondata)

class nlp():
    '''Data to send to the server'''
    def start(self, session_data):
        return post("/nlp/start",session_data)
    def send_reqs(self, reqs, session_data):
        request_data = session_data.update(reqs)
        return post("/nlp/send_reqs",request_data)
