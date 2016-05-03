# 3rd party libs
from slackclient import SlackClient
from flask import request
from flask import Flask
import requests

# Builtin libs
import threading
import json
import time
import logging

# internals
from will.logger import log
import plugins
import intent
import config


app = Flask(__name__)


def slack():
    '''Slack rtm reader started in seprate thread'''
    slack_conf = config.load_config("slack")
    log.info("In slack function in new thread")
    sc = SlackClient(slack_conf["token"])
    if sc.rtm_connect():
        log.info("Connected to rtm socket")
    while True:
        time.sleep(0.1)
        # Get message from rtm socket
        message = sc.rtm_read()
        # If the message isn't empty
        if message != []:
            # If the message is text as opposed to a notification. Eventually
            # plan to have other kinds of messages in a backend communications
            # channel.
            if message[0].keys()[0] == 'text':
                command = message[0].values()[0]
                log.debug(command)
                # The commands are json or plain text. If it isn't a json
                # backend command, interpret it as a "normal" command
                try:
                    command = json.loads(command)
                except ValueError:
                    command = [{'type': 'command'}, {'devices': 'all'}, {
                        'action': "{0}".format(command)}]
                # Json slack commands or management can eventually be formatted like so: [{"type":"management/command",{"devices":"all/mobile/desktop/network/device name"},{"action":"message content"}]
                # Not sure if I want to do that in the backend or command
                # channel or what really, but I'm definitely working with it.
                commandtype = command[0]
                devices = command[1]
                action = command[2]
                # Replace thisdevicename with whatever you want to name yours
                # in the W.I.L.L slack network (obviously)
                if devices.values()[0] == 'all' or devices.values()[0] == slack_conf["domain"]:
                    log.info("Checking local W.I.L.L server")
                    # Hit W.I.L.L with the command. This is also where you
                    # could add exceptions or easter eggs
                    answer = requests.get(
                        'http://127.0.0.1:5000/?context=command&command={0}'.format(action.values()[0])).text
                    if answer != '':
                        print sc.api_call(
                            "chat.postMessage",
                            channel=slack_conf["channel"],
                            text="{0}".format(answer),
                            username=slack_conf["username"]
                        )
    else:
        log.error("Connection Failed, invalid token?")


@app.route("/")
def main():
    '''Take command from 127.0.0.1:5000 and run it through various modules'''
    try:
        # Get command
        plugin_command = plugins.Command(request.args.get("command", ''))
        return_values = plugin_command.dispatch_event()
        if len(return_values) > 0:
            return '\n'.join(return_values)
        else:
            return ''
    except Exception as e:
        log.exception(e)
        return str(e)


def run():
    '''Open logs, check log settings, and start the flask server and slack thread'''
    log.info('''

\                /   |    |              |
 \              /    |    |              |
  \            /     |    |              |
   \    /\    /      |    |              |
    \  /  \  /       |    |              |
     \/    \/        |    ------------   ------------
        ''')
    if log.getEffectiveLevel() == logging.DEBUG:
        debugval = True
    else:
        debugval = False
    plugins.load(config.FilePath("plugins/"))
    log.info("Debug value is {0}".format(debugval))
    log.info("Connecting to rtm socket")
    t = threading.Thread(target=slack)
    t.daemon=True #Kills the thread on program exit
    t.start()
    log.info("Starting flask server on localhost")
    print app.run(debug=debugval, use_reloader=False)
