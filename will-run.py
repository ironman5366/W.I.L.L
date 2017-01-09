'''Run the wsgi server for W.I.L.L'''
from geventwebsocket.handler import WebSocketHandler
from gevent.pywsgi import WSGIServer
import gevent

from will import app, start
start()
print "Loading server"
http_server = WSGIServer(('', 80), app, handler_class=WebSocketHandler)
http_server.serve_forever()