#External imports
import requests
import json

#Builtin imports
import logging
import urllib

#TODO: in the future (in the public betas) add a server to check nearest server and redirect to that
SERVER_IP = "107.170.142.65"

# Encode the data
class session():
    '''Session management section'''
    def start(self, sessiondata):
        '''Start the session'''
        request = requests.post("{0}/start_session".format(SERVER_IP), sessiondata)
        response = request.json
        return response
#TODO: Add more methods