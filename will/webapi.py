#External imports
import requests
import json

#Builtin imports
import logging
import urllib

#TODO: in the future (in the public betas) add a server to check nearest server and redirect to that

SERVER_IP = "107.170.142.65"
sessionid = False
credentials = {"username":False,:"password":False}

# Encode the data
class session():
    '''Session management section'''
    def start(self, sessiondata):
        '''Start the session'''
        global credentials
        credentials["username"] = sessiondata["username"]
        credentials["password"] = sessiondata["password"]
        request = requests.post("{0}/start_session".format(SERVER_IP), sessiondata)
        response = request.json
        global sessionid
        sessionid = response['sessionid']
        return response
    def end(self, sessiondata):
        request = requests.post("{0}/end_session".format(SERVER_IP),sessiondata)
        response = request.json
        return response
class send():
    '''Data to send to the server'''
    def nlp_reqs(self, reqs):
        request_data = {
            "sessionid" : sessionid,
            "username" : credentials["username"],
            "password" : credentials["password"],
           "req_data" : reqs
        }
        request = requests.post("{0}/nlp/add_req.".format(SERVER_IP), request_data)
        response = request.json
        return response
#TODO: Finish this
