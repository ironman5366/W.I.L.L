import glob
import os
from logs import logs as log
logs=log()

def parse(command, plugins):
	words=command.split(' ')
	firstword=words[0]
	verb=False
	logs.write('Analyzing word {0}'.format(firstword), 'working')
	logs.write('Checking to see if the word is a plugin', 'trying')
	for plugin in plugins:
		logs.write("Full plugin is {0}".format(plugin), 'working')
		plugname=plugin.keys()[0]
		logs.write("Plugin name is {0}".format(plugname),'working')
		plugvals=plugin.values()[0]
		logs.write("Plugin values are {0}".format(plugvals),'working')
		for plugdict in plugvals:
			logs.write("Checking dictionary {0}".format(plugdict),'trying')
			if plugdict.keys()[0]=="synonyms":
				logs.write("Found synonyms dictionary", 'success')
				syns=plugdict.values()[0]
				break
		if firstword.lower()==plugname.lower():
			logs.write("The command and plugin name match",'success')
			return {'execute':plugin}
		else:
			for syn in syns:
				logs.write("Checking synonym {0}".format(syn), 'working')
				if firstword.lower()==syn:
					logs.write()
			logs.write("The command does not match the plugin name",'trying')
	for word in words:
		questionwords=open("questionwords.txt").read()
		questions=questionwords.split('-----\n')[0].split('\n')	
		possiblequestions=questionwords.replace('----\n','').split('\n')
		logs.write("Checking to see if word {0} is a question word".format(word), 'working')
		for question in questions:
			logs.write("Checking against question word {0}".format(question), 'working')
			if question.lower()==word.lower():
				logs.write("Question word {0} found".format(question), 'success')
				questionplugs=[]
				for plugin in plugins:
					for plugdict in plugvals:
						logs.write("Checking dictionary {0}".format(plugdict),'trying')
						if plugdict.keys()[0]=="questiontriggers":
							logs.write("Found questiontriggers dictionary", 'success')
							qts=plugdict.values()[0]
							break
					if qts=="any":
						questionplugs.append(plugin)
					return {'questionlist':questionplugs}
		for question in possiblequestions:
			logs.write("Checking against possible question word {0}".format(question), 'working')
			if question.lower()==word.lower():
				logs.write("Possible question word {0} found".format(question), 'success')
				questionplugs=[]
				for plugin in plugins:
					for plugdict in plugvals:
						logs.write("Checking dictionary {0}".format(plugdict),'trying')
						if plugdict.keys()[0]=="questiontriggers":
							logs.write("Found questiontriggers dictionary", 'success')
							qts=plugdict.values()[0]
							break
					if qts=="any":
						questionplugs.append(plugin)
					return {'questionlist':questionplugs}