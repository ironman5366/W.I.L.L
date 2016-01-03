from flask import Flask
from flask import request
import intent
from logs import logs as log
import plugins as plugs
logs=log()

app = Flask(__name__)

@app.route("/")
def main():
	command = request.args.get("command", '')
	logs.write("Command is {0}".format(command),'working')
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
	intent.parse(command, plugins)
	return "Done"
if __name__ == "__main__":
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
	logs.write("Starting flask server on localhost",'trying')
	print app.run(debug=debugval,use_reloader=False)