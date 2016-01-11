import glob
import os
from logs import logs as log
import json
import imp
logs=log()
def load():
	logs.write("In plugin loader",'working')
	plugins=[]
	if os.path.isdir("plugins"):
		plugindir=list(list(os.walk('plugins'))[0])
		logs.write("plugindir is {0}".format(plugindir), 'working')
		for plugin in plugindir[1]:
			logs.write("Plugin is {0}".format(str(plugin)), 'working')
			logs.write("Loading plugin {0}".format(plugin),'trying')
			logs.write("plugin.json file path should be plugins/{0}/plugin.json".format(plugin),'working')
			if os.path.isfile('plugins/{0}/plugin.json'.format(plugin)):
				pluginfo=json.loads(open('plugins/{0}/plugin.json'.format(plugin)).read())
				plugins.append({plugin:pluginfo})
				logs.write("Loaded plugin {0}".format(plugin),'success')
			else:
				logs.write("plugin.json file not found for plugin {0}".format(plugin),'error')
		return plugins
	else:
		logs.write("Plugin directory not found", 'error')
		return False
def execute(plugin, command):
	def checkdicts(checkvar):
		logs.write("Looking for {0} dictionary".format(checkvar), 'trying')
		for plugdict in plugin.values()[0]:
			logs.write("Checking dictionary {0}".format(plugdict),'trying')
			if plugdict.keys()[0]==checkvar:
				logs.write("Found dictionary {0}".format(checkvar), 'success')
				checkval=plugdict.values()[0]
				break
		return checkval
	logs.write("Executing plugin {0}".format(plugin),'working')
	plugtype=checkdicts('type')
	logs.write("Plugin type is {0}".format(plugtype), 'working')
	firstword=checkdicts('firstword')
	if firstword=='no':
		command=command.split(command.split(" ")[0]+" ")[1]
		logs.write("removed the first word from the command. The command is now {0}".format(command), 'success')
	if plugtype=="python":
		logs.write("Checking to get the name of the python file", 'trying')
		pyfile=checkdicts('file')
		logs.write("Trying to import python file {0}".format(pyfile), 'trying')
		pyimport="plugins/{0}/{1}".format(plugin.keys()[0],pyfile)
		logs.write("Import path is {0}".format(pyimport), 'workng')
		imvar = imp.load_source('plugfile', pyimport)
		logs.write("Imported python plugin", 'success')
		plugfunction = checkdicts('function')
		required=checkdicts('require')
		needed=[]
		finalargs=[]
		for item in required:
			needed.append(item)
		if required==["command"]:
			finalargs.append(command)
		else:
			for item in required:
				logs.write("Trying to find argument {0}".format(item), 'trying')
				try:
					fetched=argfetcher.get(item)
					logs.write("Fetched the argument {0}. The value was {1}".format(item,fetched),'success')
				except Exception as e:
					logs.write("{0} occurred trying to fetch the item", 'error')
		finalargs=tuple(finalargs)
		result = getattr(imvar, plugfunction)(finalargs)
		return result
	elif plugtype=="exec":
		required=checkdicts('require')
		needed=[]
		finalargs=[]
		for item in required:
			needed.append(item)
		if required==["command"]:
			finalargs.append({"command":command})
		else:
			for item in required:
				logs.write("Trying to find argument {0}".format(item), 'trying')
				try:
					fetched=argfetcher.get(item)
					logs.write("Fetched the argument {0}. The value was {1}".format(item,fetched),'success')
					finalargs.append({item:fetched})
				except Exception as e:
					logs.write("{0} occurred trying to fetch the item", 'error')
		structure=checkdicts('structure')
		for item in required:
			for arg in finalargs:
				if arg.keys()[0]==item:
					finalval=arg.values()[0]
					logs.write("Final value of {0} is {1}".format(arg,finalval), 'working')
			structure=structure.replace('{0}'.format(item),finalval)
		logs.write("Executing comamnd {0}".format(structure), 'trying')
		resultvar=os.popen(structure).read()
		logs.write("Executed command {0}, got {1}".format(structure,resultvar), 'success')
		if checkdicts('returns')=="answer":
			return resultvar
		else:
			return "Done"