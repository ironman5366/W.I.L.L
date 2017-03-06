# External imports
from flask import Flask
from flask_socketio import SocketIO
import dataset

#Internal imports
import web
import API

# Builtin imports
import logging
import sys
try:
    import Queue
except ImportError:
    import queue as Queue
import os
import json
from logging.handlers import RotatingFileHandler
import datetime
import atexit
import signal


now = datetime.datetime.now()

app = Flask(__name__)

app.register_blueprint(web.web)
app.register_blueprint(API.api, url_prefix="/api")


conf_file = "will.conf"
if os.path.isfile("debug_will.conf"):
    conf_file = "debug_will.conf"
if os.path.isfile(conf_file):
    data_string = open(conf_file).read()
    json_data = json.loads(data_string)
    configuration_data = json_data
    API.configuration_data = configuration_data
    web.configuration_data = configuration_data
else:
    print ("Couldn't find will.conf file, exiting")
    os._exit(1)

db = None
app.logger.setLevel(logging.DEBUG)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.secret_key = configuration_data["secret_key"]
logfile = configuration_data["logfile"]
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filemode='w', filename=logfile)
ch = logging.StreamHandler(sys.stdout)
if configuration_data["debug"]:
    ch.setLevel(logging.DEBUG)
else:
    ch.setLevel(logging.INFO)
handler = RotatingFileHandler(logfile, maxBytes=10000000, backupCount=5)
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)
log = app.logger


socketio = SocketIO(app)


# Internal imports
import core
import API
import web

web.socketio = socketio

socketio.on(web.disconnect_session, 'disconnect')
socketio.on(web.get_updates, "get_updates")

@atexit.register
def dump_events(*args):
    '''
    Dump events to db on exit
    :return:
    '''
    try:
        log.info(":SYS:Dumping events")
    except:
        print (":SYS: Error with logging while dumping events")
    for event in core.events:
        if event["type"] != "function":
            try:
                log.debug(":SYS:Dumping event {0}".format(event))
                db["events"].upsert(event, ['uid'])
            except:
                print (":SYS:Error encountered while dumping events")

signal.signal(signal.SIGTERM, dump_events)

def start():
    """
    Initialize db and session monitor thread

    """
    global db
    global start_time
    log.info(":SYS:Starting W.I.L.L")
    db_url = configuration_data["db_url"]
    log.info(":SYS:Connected to database")
    db = dataset.connect(db_url, engine_kwargs={"pool_recycle": 1})
    core.db = db
    API.db = db
    web.db = db
    start_time = now.strftime("%I:%M %p %A %m/%d/%Y")
    web.start_time = start_time
    log.info(":SYS:Starting W.I.L.L core")
    core.initialize(db)
    log.info(":SYS:Starting sessions parsing thread")
    core.sessions_monitor(db)
    log.info(":SYS:W.I.L.L started")

if __name__ == "__main__":
    start()
    socketio.run(
        app, host=configuration_data["host"], port=configuration_data["port"], debug=configuration_data["debug"]
    ,use_reloader=False)