'''Run the wsgi server for W.I.L.L'''
from gevent.wsgi import WSGIServer
from will import app, start
start()
print "Loading server"
http_server = WSGIServer(('', 80), app)
http_server.serve_forever()