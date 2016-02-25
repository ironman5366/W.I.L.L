from flask import Flask
from flask import request
import intent
from logs import logs as log
import plugins as plugs
import contentextract
import threading
from slackclient import SlackClient
import json
import personality
import os
import requests
import time
logs=log()
token = "Your token here" 
app = Flask(__name__)
def slack():
	'''Slack rtm reader started in seprate thread'''
	logs.write("In slack function in new thread", 'working')
	sc = SlackClient(token)
	if sc.rtm_connect():
		logs.write("Connected to rtm socket", 'success')
    	while True:
    		time.sleep(0.1)
    		#Get message from rtm socket
        	message=sc.rtm_read()
        	#If the message isn't empty
        	if message!=[]:
        		#If the message is text as opposed to a notification. Eventually plan to have other kinds of messages in a backend communications channel.
        		if message[0].keys()[0]=='text':
        			command=message[0].values()[0]
        			logs.write(command,'working')
        			#The commands are json or plain text. If it isn't a json backend command, interpret it as a "normal" command
        			try:
        				command=json.loads(command)
        			except ValueError:
        				command=[{'type':'command'},{'devices':'all'},{'action':"{0}".format(command)}]
        			#Json slack commands or management can eventually be formatted like so: [{"type":"management/command",{"devices":"all/mobile/desktop/network/device name"},{"action":"message content"}]
        			#Not sure if I want to do that in the backend or command channel or what really, but I'm definitely working with it. 
        			commandtype=command[0]
        			devices=command[1]
        			action=command[2]
        			#Replace thisdevicename with whatever you want to name yours in the W.I.L.L slack network (obviously)
        			if devices.values()[0]=='all' or devices.values()[0]=="thisdevicename":
	        			logs.write("Checking local W.I.L.L server", 'trying')
	        			#Hit W.I.L.L with the command. This is also where you could add exceptions or easter eggs
	        			answer=requests.get('http://127.0.0.1:5000/?context=command&command={0}'.format(action.values()[0])).text
	        			print sc.api_call( "chat.postMessage", channel="#w_i_l_l", text="{0}".format(answer), username='W.I.L.L')
	else:
		logs.write("Connection Failed, invalid token?", 'error')

@app.route("/")
def main():
	'''Take command from 127.0.0.1:5000 and run it through various modules'''
	try:
		#Get command
		command = request.args.get("command", '')
		logs.write("Command is {0}".format(command),'working')
		logs.write("Analyzing content in command", 'trying')
		#Run command through contentextract.py
		contentextract.main(command)
		logs.write("Analyzed command content", 'success')
		logs.write("Trying to load plugin modules", 'trying')
		#Load plugins using plugins.py
		plugins=plugs.load()
		#If the plugins encounter an error
		if plugins==False:
			logs.write("Could not load plugins", 'error')
			return "error"
		#If plugins.py says that there are no plugins found. All functions are a plugin so no point in continuing
		elif plugins==[]:
			logs.write("No plugins found", 'error')
			return 'error'
		logs.write("Successfully loaded plugin modules", 'success')
		logs.write("Using the intent module to parse the command", 'trying')
		#Use intent.py to try to extract intent from command
		parsed=intent.parse(command, plugins)
		logs.write("Parsed the command", 'success')
		#If the intent parser says to execute the following plugin. Leaves room if I ever want to expand the capabilities of the intent module
		if parsed.keys()[0]=="execute":
			logs.write("Executing plugin {0}".format(parsed.values()[0].keys()[0]), 'trying')
			response=plugs.execute(parsed.values()[0], command)
			logs.write("Found answer {0}, returning it".format(response), 'success')
			return response
	except Exception as e:
		logs.write(e,'error')
		return str(e)
if __name__ == "__main__":
	'''Open logs, check log settings, and start the flask server and slack thread'''
	logs.openlogs()
	logs.write('''

\                /   |    |              |
 \              /    |    |              |
  \            /     |    |              |
   \    /\    /      |    |              |
    \  /  \  /       |    |              |
     \/    \/        |    ------------   ------------
		''', 'success')
	if logs.debug():
		debugval=True
	else:
		debugval=False
	logs.write("Debug value is {0}".format(debugval),'working')
	logs.write("Connecting to rtm socket", 'trying')
	t=threading.Thread(target=slack)
	t.start()
	logs.write("Starting flask server on localhost",'trying')
	print app.run(debug=debugval,use_reloader=False)
