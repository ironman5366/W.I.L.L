import glob
import os
from logs import logs as log
import json
logs=log()
def load():
	logs.write("In plugin loader",'working')
	plugins=[]
	if os.path.isdir("plugins"):
		plugin=[x[0] for x in os.walk('plugins')][1]
		logs.write("Loading plugin {0}".format(plugin.split("plugins/")[1]),'trying')
		logs.write("plugin.json file path should be {0}/plugin.json".format(plugin),'working')
		if os.path.isfile('{0}/plugin.json'.format(plugin)):
			pluginfo=json.loads(open('{0}/plugin.json'.format(plugin)).read())
			plugins.append({plugin.split("plugins/")[1]:pluginfo})
			logs.write("Loaded plugin {0}".format(plugin.split("plugins/")[1]),'success')
		else:
			logs.write("plugin.json file not found for plugin {0}".format(plugin.split("plugins/")[1]),'error')
		return plugins
	else:
		logs.write("Plugin directory not found", 'error')
		return False
def execute(plugin):
	logs.write("Executing plugin {0}".format(plugin),'working')
	for plugdict in plugin.values()[0]:
		logs.write("Checking dictionary {0}".format(plugdict),'trying')
		if plugdict.keys()[0]=="type":
			logs.write("Found type dictionary", 'success')
			plugtype=plugdict.values()[0]
			break
	logs.write("Plugin type is {0}".format(plugtype), 'working')
	return "Done"