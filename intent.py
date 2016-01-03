import glob
import os
from logs import logs as log
logs=log()

def parse(command, plugins):
	words=command.split(' ')
	for word in words:
		verb=False
		logs.write('Analyzing word {0}'.format(word), 'working')
		logs.write('Checking to see if the word is a plugin', 'trying')
		for plugin in glob.glob("plugins/*.will"):
			plugname=plugin.split('.will')[0].split('plugins/')[1]
			logs.write("Plugin name is {0}".format(plugname),'working')
			if command.lower()==plugname.lower():
				logs.write("The command and plugin name match",'success')
				return plugname
			else:
				logs.write("The command does not match the plugin name",'trying')
				