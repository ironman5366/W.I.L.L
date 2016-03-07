import glob
import os
from logger import log


def qparse(questionlist):
    '''Goes through questions in a really ugly way. It works though and is somehow fairly fast'''
    def checkdicts(checkvar, plugin):
        '''I have no excuses for having this'''
        plugvals = plugin.values()[0]
        for plugdict in plugvals:
            log.info("Checking dictionary {0}".format(plugdict))
            if plugdict.keys()[0] == checkvar:
                log.info("Found {0} dictionary".format(checkvar))
                checkval = plugdict.values()[0]
                return checkval
    # Sees which plugins have the highest priority for question words. This
    # means that you can define which plugins you'd like to answer the
    # question if possible. If they can't it goes to the next.
    log.info("Parsing possible plugins")
    priority = open('priority.txt').read().split('\n')
    prioritized = []
    for plugin in questionlist:
        plugname = plugin.keys()[0]
        log.info("Checking plugin {0}".format(plugname))
        log.info("Checking to see if the plugin is in the priority list")
        plugname = plugin.keys()[0]
        for line in priority:
            name = line.split(':')[1]
            status = line.split(':')[0]
            log.info('Item {0} in priority list is {1}'.format(
                status, name))
            if plugname.lower() == name.lower():
                log.info(
                    "Plugin name and priority list item match")
                prioritized.append({status: plugin})
    log.info("Going through list of prioritized plugins")
    log.info(prioritized)
    num = None
    for plugin in prioritized:
        log.info("Looking at plugin {0}".format(plugin))
        status = plugin.keys()[0]
        plugname = plugin.values()[0].keys()[0]
        log.info("Plugin {0} has priority {1}".format(
            plugname, status))
        status = int(status)
        if num == None:
            num = status
        else:
            if status > num:
                num = status
            else:
                pass
        if plugin == prioritized[-1]:
            log.info("Analyzed the last plugin")
            for item in prioritized:
                if int(item.keys()[0]) == num:
                    log.info("Highest priority was {0}".format(
                        item.values()[0].keys()[0]))
                    try:
                        return {'execute': item.values()[0]}
                    except AttributeError:
                        log.error("Command not recognized")
                        return {'error':'notfound'}


def parse(command, plugins):
    '''Parses intent from commands. The plugins argument is a list containing lists of information about each plugin.'''
    words = command.split(' ')
    firstword = words[0]
    verb = False
    log.info('Analyzing word {0}'.format(firstword))
    # Goes through plugins to see if the word matches
    log.info('Checking to see if the word is a plugin')
    for plugin in plugins:
        log.info("Full plugin is {0}".format(plugin))
        plugname = plugin.keys()[0]
        log.info("Plugin name is {0}".format(plugname))
        plugvals = plugin.values()[0]
        log.info("Plugin values are {0}".format(plugvals))
        for plugdict in plugvals:
            # Looks to see if the command matches a synonym of the plugin
            log.info("Checking dictionary {0}".format(plugdict))
            if plugdict.keys()[0] == "synonyms":
                log.info("Found synonyms dictionary")
                syns = plugdict.values()[0]
                break
        if firstword.lower() == plugname.lower():
            log.info("The command and plugin name match")
            # Tells main.py to run the plugin
            try:
                return {'execute': plugin}
            except AttributeError:
                log.error("Command not recognized")
                return {'error':'notfound'}
        else:
            for syn in syns:
                log.info("Checking synonym {0}".format(syn))
                if firstword.lower() == syn or syn in command.lower():
                    log.info("The command and synonym name match")
                    try:
                        return {'execute': plugin}
                    except AttributeError:
                        log.error("Command not recognized")
                        return {'error':'notfound'}
            log.warn("The command does not match the plugin name")
    for word in words:
        # Checks to see if the word is one that I've defined as a question
        # word. There are two categories, dedicated question words, and words
        # that can also mean other things
        questionwords = open("questionwords.txt").read()
        questions = questionwords.split('-----\n')[0].split('\n')
        possiblequestions = questionwords.replace('-----\n', '').split('\n')
        log.info(
            "Checking to see if word {0} is a question word".format(word))
        for question in questions:
            log.info("Checking against question word {0}".format(
                question))
            if question.lower() == word.lower():
                log.info("Question word {0} found".format(
                    question))
                questionplugs = []
                for plugin in plugins:
                    plugvals = plugin.values()[0]
                    log.info("Analyzing plugin {0}".format(
                        plugin))
                    for plugdict in plugvals:
                        log.info("Checking dictionary {0}".format(
                            plugdict))
                        # Checking to see which kinds of question words the
                        # plugin can be triggered by
                        if plugdict.keys()[0] == "questiontriggers":
                            log.info(
                                "Found questiontriggers dictionary")
                            # qts is the questiontriggers value. It's any
                            # meaning that it can be triggered by any question
                            # word, none meaning none, or some meaning only
                            # dedicated question words.
                            qts = plugdict.values()[0]
                            break
                    log.info(qts)
                    if qts == "any":
                        log.info("Appending plugin {0} to questionplugs".format(
                            plugin))
                        questionplugs.append(plugin)
                        return qparse(questionplugs)
            for question in possiblequestions:
                # Checks to see if a non dedicated question word fits what I
                # want
                log.info("Checking against possible question word {0}".format(
                    question))
                if question.lower() == word.lower():
                    log.info("Possible question word {0} found".format(
                        question))
                    questionplugs = []
                    for plugin in plugins:
                        plugvals = plugin.values()[0]
                        log.info("Analyzing plugin {0}".format(
                            plugin))
                        for plugdict in plugvals:
                            plugvals = plugin.values()[0]
                            log.info("Checking dictionary {0}".format(
                                plugdict))
                            if plugdict.keys()[0] == "questiontriggers":
                                log.info(
                                    "Found questiontriggers dictionary")
                                qts = plugdict.values()[0]
                                break
                        if qts == "any":
                            log.info("Appending plugin {0} to questionplugs".format(
                                plugin))
                            questionplugs.append(plugin)
                            return qparse(questionplugs)
            log.error("Command not found")
            return {'error':'notfound'}
