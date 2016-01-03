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
			plugins.append({plugin:pluginfo})
			logs.write("Loaded plugin {0}".format(plugin.split("plugins/")[1]),'success')
		else:
			logs.write("plugin.json file not found for plugin {0}".format(plugin.split("plugins/")[1]),'error')
		return plugins
	else:
		logs.write("Plugin directory not found", 'error')
		return False