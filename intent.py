import glob
import os
from logs import logs as log
logs=log()

def parse(command, plugins):
	words=command.split(' ')
	with words[0] as word:
		verb=False
		logs.write('Analyzing word {0}'.format(word), 'working')
		logs.write('Checking to see if the word is a plugin', 'trying')
		for plugin in plugins:
			logs.write("Plugin name is {0}".format(plugin[0]),'working')
			syns=plugin[7][1]
			if command.lower()==plugname.lower():
				logs.write("The command and plugin name match",'success')
				return plugins[plugname]
			else:
				for syn in syns:
					logs.write("Checking synonym {0}".format(syn), 'working')
					if command.lower()==syn:
						logs.write()
				logs.write("The command does not match the plugin name",'trying')
	#At this point, the first word didn't match a plugin or it's synonyms
				