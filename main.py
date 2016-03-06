# 3rd party libs
from slackclient import SlackClient
from flask import request
from flask import Flask
import requests

# Builtin libs
import threading
import json
import time
import os
import logging

# internals
from logger import log
import plugins as plugs
import contentextract
import personality
import intent
import config


app = Flask(__name__)


def slack():
    '''Slack rtm reader started in seprate thread'''
    slack_conf = config.load_config()["slack"]
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
        command = request.args.get("command", '')
        log.debug("Command is {0}".format(command))
        log.info("Analyzing content in command")
        # Run command through contentextract.py
        contentextract.main(command)
        log.info("Analyzed command content")
        log.info("Trying to load plugin modules")
        # Load plugins using plugins.py
        plugins = plugs.load()
        # If the plugins encounter an error
        if plugins is False:
            log.error("Could not load plugins")
            return "error"
        # If plugins.py says that there are no plugins found. All functions are
        # a plugin so no point in continuing
        elif plugins == []:
            log.error("No plugins found")
            return 'error'
        log.info("Successfully loaded plugin modules")
        log.info("Using the intent module to parse the command")
        # Use intent.py to try to extract intent from command
        parsed = intent.parse(command, plugins)
        log.info("Parsed the command")
        # If the intent parser says to execute the following plugin. Leaves
        # room if I ever want to expand the capabilities of the intent module
        if parsed.keys()[0] == "execute":
            log.info("Executing plugin {0}".format(
                parsed.values()[0].keys()[0]))
            response = plugs.execute(parsed.values()[0], command)
            log.info("Found answer {0}, returning it".format(
                response))
            return response
        elif parsed.keys()[0]=="error":
            log.error("Parse function returned the error {0}".format(parsed.values()[0]))
            if parsed.values()[0]=="notfound":
                #This would have unhandled exceptions if the search plugin was gone, but I can't imagine why it would be
                log.error("The error means that the command was not recognized")
                log.info("Using the search plugin on the command phrase")
                log.info("Trying to find search plugin")
                for plugin in plugins:
                    if plugin.keys()[0]=="search":
                        searchplug=plugin
                        break
                log.info("Found search plugin")
                response=plugs.execute(searchplug,command)
                log.info("Found answer {0}, returning it".format(response))
                return response
            else:
                log.error("Unhandled error {0}. If you get this error message something is broken in the intent module. Please raise an issue on https://github.com/ironman5366/W.I.L.L".format(str(parsed.values()[0])))
    except Exception as e:
        log.error(e, 'error')
        return str(e)


if __name__ == "__main__":
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
    log.info("Debug value is {0}".format(debugval))
    log.info("Connecting to rtm socket")
    t = threading.Thread(target=slack)
    t.daemon=True #Kills the thread on program exit
    t.start()
    log.info("Starting flask server on localhost")
    print app.run(debug=debugval, use_reloader=False)
