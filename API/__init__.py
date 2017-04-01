#Builtin imports
import logging
import threading

#Internal imports
from exceptions import *
import userspace

#External  imports
import falcon

log = logging.getLogger()

app = falcon.API()

class StatusCheck(object):
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200


class API:
    def __init__(self, configuration_data):
        self.configuration_data = configuration_data