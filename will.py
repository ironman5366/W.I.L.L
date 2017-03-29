# External imports
from flask import Flask
from flask_socketio import SocketIO
import dataset

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

# Internal imports
import core
import API
import web

class will:

    @atexit.register
    def dump_events(self, *args):
        '''
        Dump events to db on exit
        :return:
        '''
        try:
            log.info(":SYS:Dumping events")
        except:
            print(":SYS: Error with logging while dumping events")
        for event in core.events:
            if event["type"] != "function":
                try:
                    log.debug(":SYS:Dumping event {0}".format(event))
                    db["events"].upsert(event, ['uid'])
                except:
                    print(":SYS:Error encountered while dumping events")

    def start(self):
        """
        Initialize db and session monitor thread

        """
        global db
        log.info(":SYS:Starting W.I.L.L")
        db_url = self.configuration_data["db_url"]
        log.info(":SYS:Connecting to database")
        db = dataset.connect(db_url, engine_kwargs={"pool_recycle": 1})
        core.db = db
        API.db = db
        web.db = db
        start_time = self.now.strftime("%I:%M %p %A %m/%d/%Y")
        web.start_time = start_time
        log.info(":SYS:Starting W.I.L.L core")
        core.initialize(db)
        log.info(":SYS:Starting sessions parsing thread")
        core.sessions_monitor(db)
        log.info(":SYS:W.I.L.L started")

    def __init__(self):

        self.now = datetime.datetime.now()

        conf_file = "will.conf"
        if os.path.isfile("debug_will.conf"):
            conf_file = "debug_will.conf"
        self.conf_file = conf_file
        if os.path.isfile(conf_file):
            data_string = open(conf_file).read()
            json_data = json.loads(data_string)
            self.configuration_data = json_data
            API.configuration_data = self.configuration_data
            web.configuration_data = self.configuration_data
        else:
            print("Couldn't find will.conf file, exiting")
            os._exit(1)
        self.db = None
        app = Flask(__name__)
        app.register_blueprint(web.web)
        app.register_blueprint(API.api, url_prefix="/api")
        self.app = app
        app.logger.setLevel(logging.DEBUG)
        app.logger.addHandler(logging.StreamHandler(sys.stdout))
        app.secret_key = self.configuration_data["secret_key"]
        logfile = self.configuration_data["logfile"]
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            filemode='w', filename=logfile)
        ch = logging.StreamHandler(sys.stdout)
        if self.configuration_data["debug"]:
            ch.setLevel(logging.DEBUG)
        else:
            ch.setLevel(logging.INFO)
        handler = RotatingFileHandler(logfile, maxBytes=10000000, backupCount=5)
        handler.setLevel(logging.DEBUG)
        self.app.logger.addHandler(handler)
        global log
        log = self.app.logger
        self.socketio = SocketIO(app)

        web.socketio = self.socketio

        self.socketio.on(web.disconnect_session, 'disconnect')
        self.socketio.on(web.get_updates, "get_updates")

        signal.signal(signal.SIGTERM, self.dump_events)

        self.start()

        self.socketio.run(
            app, host=self.configuration_data["host"], port=self.configuration_data["port"], debug=self.configuration_data["debug"]
            , use_reloader=False)

if __name__ == "__main__":
    will()
