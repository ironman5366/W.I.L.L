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
logs=log()
token = "Your token here" 
app = Flask(__name__)
def slack():
	logs.write("In slack function in new thread", 'working')
	sc = SlackClient(token)
	if sc.rtm_connect():
		logs.write("Connected to rtm socket", 'success')
    	while True:
        	message=sc.rtm_read()
        	if message!=[]:
        		if message[0].keys()[0]=='text':
        			command=message[0].values()[0]
        			logs.write(command,'working')
        			try:
        				command=json.loads(command)
        			except ValueError:
        				command=[{'type':'command'},{'devices':'all'},{'action':"{0}".format(command)}]
        			commandtype=command[0]
        			devices=command[1]
        			action=command[2]
        			if devices.values()[0]=='all' or devices.values()[0]=="XPS":
	        			logs.write("Checking local W.I.L.L server", 'trying')
	        			answer=requests.get('http://127.0.0.1:5000/?context=command&command={0}'.format(action.values()[0])).text
	        			print sc.api_call( "chat.postMessage", channel="#w_i_l_l", text="{0}".format(answer), username='W.I.L.L')
	else:
		logs.write("Connection Failed, invalid token?", 'error')

@app.route("/")
def main():
	try:
		command = request.args.get("command", '')
		logs.write("Command is {0}".format(command),'working')
		logs.write("Analyzing content in command", 'trying')
		contentextract.main(command)
		logs.write("Analyzed command content", 'success')
		logs.write("Trying to load plugin modules", 'trying')
		plugins=plugs.load()
		if plugins==False:
			logs.write("Could not load plugins", 'error')
			return "error"
		elif plugins==[]:
			logs.write("No plugins found", 'error')
			return 'error'
		logs.write("Successfully loaded plugin modules", 'success')
		logs.write("Using the intent module to parse the command", 'trying')
		parsed=intent.parse(command, plugins)
		logs.write("Parsed the command", 'success')
		if parsed.keys()[0]=="execute":
			logs.write("Executing plugin {0}".format(parsed.values()[0].keys()[0]), 'trying')
			response=plugs.execute(parsed.values()[0], command)
			logs.write("Found answer {0}, returning it".format(response), 'success')
			return response
	except Exception as e:
		logs.write(e,'error')
		return str(e)
if __name__ == "__main__":
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
