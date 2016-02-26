import glob
import os
from logs import logs as log
logs = log()


def qparse(questionlist):
    '''Goes through questions in a really ugly way. It works though and is somehow fairly fast'''
    def checkdicts(checkvar, plugin):
        '''I have no excuses for having this'''
        plugvals = plugin.values()[0]
        for plugdict in plugvals:
            logs.write("Checking dictionary {0}".format(plugdict), 'trying')
            if plugdict.keys()[0] == checkvar:
                logs.write("Found {0} dictionary".format(checkvar), 'success')
                checkval = plugdict.values()[0]
                return checkval
    # Sees which plugins have the highest priority for question words. This
    # means that you can define which plugins you'd like to answer the
    # question if possible. If they can't it goes to the next.
    logs.write("Parsing possible plugins", 'trying')
    priority = open('priority.txt').read().split('\n')
    prioritized = []
    for plugin in questionlist:
        plugname = plugin.keys()[0]
        logs.write("Checking plugin {0}".format(plugname), 'working')
        logs.write(
            "Checking to see if the plugin is in the priority list", 'working')
        plugname = plugin.keys()[0]
        for line in priority:
            name = line.split(':')[1]
            status = line.split(':')[0]
            logs.write('Item {0} in priority list is {1}'.format(
                status, name), 'working')
            if plugname.lower() == name.lower():
                logs.write(
                    "Plugin name and priority list item match", 'success')
                prioritized.append({status: plugin})
    logs.write("Going through list of prioritized plugins", 'trying')
    logs.write(prioritized, 'working')
    num = None
    for plugin in prioritized:
        logs.write("Looking at plugin {0}".format(plugin), 'working')
        status = plugin.keys()[0]
        plugname = plugin.values()[0].keys()[0]
        logs.write("Plugin {0} has priority {1}".format(
            plugname, status), 'working')
        status = int(status)
        if num == None:
            num = status
        else:
            if status < num:
                num = status
            else:
                pass
        if plugin == prioritized[-1]:
            logs.write("Analyzed the last plugin", 'working')
            for item in prioritized:
                if int(item.keys()[0]) == num:
                    logs.write("Highest priority was {0}".format(
                        item.values()[0].keys()[0]), 'success')
                    return {'execute': item.values()[0]}


def parse(command, plugins):
    '''Parses intent from commands. The plugins argument is a list containing lists of information about each plugin.'''
    words = command.split(' ')
    firstword = words[0]
    verb = False
    logs.write('Analyzing word {0}'.format(firstword), 'working')
    # Goes through plugins to see if the word matches
    logs.write('Checking to see if the word is a plugin', 'trying')
    for plugin in plugins:
        logs.write("Full plugin is {0}".format(plugin), 'working')
        plugname = plugin.keys()[0]
        logs.write("Plugin name is {0}".format(plugname), 'working')
        plugvals = plugin.values()[0]
        logs.write("Plugin values are {0}".format(plugvals), 'working')
        for plugdict in plugvals:
            # Looks to see if the command matches a synonym of the plugin
            logs.write("Checking dictionary {0}".format(plugdict), 'trying')
            if plugdict.keys()[0] == "synonyms":
                logs.write("Found synonyms dictionary", 'success')
                syns = plugdict.values()[0]
                break
        if firstword.lower() == plugname.lower():
            logs.write("The command and plugin name match", 'success')
            # Tells main.py to run the plugin
            return {'execute': plugin}
        else:
            for syn in syns:
                logs.write("Checking synonym {0}".format(syn), 'working')
                if firstword.lower() == syn:
                    logs.write("The command and synonym name match", 'success')
                    return {'execute': plugin}
            logs.write("The command does not match the plugin name", 'trying')
    for word in words:
        # Checks to see if the word is one that I've defined as a question
        # word. There are two categories, dedicated question words, and words
        # that can also mean other things
        questionwords = open("questionwords.txt").read()
        questions = questionwords.split('-----\n')[0].split('\n')
        possiblequestions = questionwords.replace('-----\n', '').split('\n')
        logs.write(
            "Checking to see if word {0} is a question word".format(word), 'working')
        for question in questions:
            logs.write("Checking against question word {0}".format(
                question), 'working')
            if question.lower() == word.lower():
                logs.write("Question word {0} found".format(
                    question), 'success')
                questionplugs = []
                for plugin in plugins:
                    plugvals = plugin.values()[0]
                    logs.write("Analyzing plugin {0}".format(
                        plugin), 'working')
                    for plugdict in plugvals:
                        logs.write("Checking dictionary {0}".format(
                            plugdict), 'trying')
                        # Checking to see which kinds of question words the
                        # plugin can be triggered by
                        if plugdict.keys()[0] == "questiontriggers":
                            logs.write(
                                "Found questiontriggers dictionary", 'success')
                            # qts is the questiontriggers value. It's any
                            # meaning that it can be triggered by any question
                            # word, none meaning none, or some meaning only
                            # dedicated question words.
                            qts = plugdict.values()[0]
                            break
                    logs.write(qts, 'working')
                    if qts == "any":
                        logs.write("Appending plugin {0} to questionplugs".format(
                            plugin), 'working')
                        questionplugs.append(plugin)
                        return qparse(questionplugs)
            for question in possiblequestions:
                # Checks to see if a non dedicated question word fits what I
                # want
                logs.write("Checking against possible question word {0}".format(
                    question), 'working')
                if question.lower() == word.lower():
                    logs.write("Possible question word {0} found".format(
                        question), 'success')
                    questionplugs = []
                    for plugin in plugins:
                        plugvals = plugin.values()[0]
                        logs.write("Analyzing plugin {0}".format(
                            plugin), 'working')
                        for plugdict in plugvals:
                            plugvals = plugin.values()[0]
                            logs.write("Checking dictionary {0}".format(
                                plugdict), 'trying')
                            if plugdict.keys()[0] == "questiontriggers":
                                logs.write(
                                    "Found questiontriggers dictionary", 'success')
                                qts = plugdict.values()[0]
                                break
                        if qts == "any":
                            logs.write("Appending plugin {0} to questionplugs".format(
                                plugin), 'working')
                            questionplugs.append(plugin)
                            return qparse(questionplugs)
