import glob
import os
from logger import log
import json
import imp


def load():
    '''Go through all plugins and return the info from their plugin.json files to main.py'''
    log.info("In plugin loader")
    plugins = []
    if os.path.isdir("plugins"):
        plugindir = list(list(os.walk('plugins'))[0])
        log.info("plugindir is {0}".format(plugindir))
        for plugin in plugindir[1]:
            log.info("Plugin is {0}".format(str(plugin)))
            log.info("Loading plugin {0}".format(plugin))
            log.info(
                "plugin.json file path should be plugins/{0}/plugin.json".format(plugin))
            if os.path.isfile('plugins/{0}/plugin.json'.format(plugin)):
                pluginfo = json.loads(
                    open('plugins/{0}/plugin.json'.format(plugin)).read())
                plugins.append({plugin: pluginfo})
                log.info("Loaded plugin {0}".format(plugin))
            else:
                log.error(
                    "plugin.json file not found for plugin {0}".format(plugin))
        return plugins
    else:
        log.error("Plugin directory not found")
        return False


def execute(plugin, command):
    '''Execute a plugin. The plugin arg is the info from the plugin.json file'''
    def checkdicts(checkvar):
        '''This function iterates over the dictionaries in the plugin list. I have no excuse for it.'''
        log.info("Looking for {0} dictionary".format(checkvar))
        for plugdict in plugin.values()[0]:
            log.info("Checking dictionary {0}".format(plugdict))
            if plugdict.keys()[0] == checkvar:
                log.info("Found dictionary {0}".format(checkvar))
                checkval = plugdict.values()[0]
                break
        return checkval
    log.info("Executing plugin {0}".format(plugin))
    plugtype = checkdicts('type')
    log.info("Plugin type is {0}".format(plugtype))
    # Check if the plugin wants the first word from the command.
    firstword = checkdicts('firstword')
    if firstword == 'no':
        command = command.split(command.split(" ")[0] + " ")[1]
        log.info("removed the first word from the command. The command is now {0}".format(
            command))
    # If the plugin is a python plugin
    if plugtype == "python":
        # Find the python file name and import it
        log.info("Checking to get the name of the python file")
        pyfile = checkdicts('file')
        log.info("Trying to import python file {0}".format(pyfile))
        pyimport = "plugins/{0}/{1}".format(plugin.keys()[0], pyfile)
        log.info("Import path is {0}".format(pyimport))
        imvar = imp.load_source('plugfile', pyimport)
        log.info("Imported python plugin")
        plugfunction = checkdicts('function')
        # Find the required arguments
        required = checkdicts('require')
        needed = []
        finalargs = []
        for item in required:
            needed.append(item)
        if required == ["command"]:
            finalargs.append(command)
        else:
            for item in required:
                log.info("Trying to find argument {0}".format(item))
                try:
                    fetched = argfetcher.get(item)
                    log.info("Fetched the argument {0}. The value was {1}".format(
                        item, fetched))
                except Exception as e:
                    log.error("{0} occurred trying to fetch the item")
        # Run the plugin and return the result
        finalargs = tuple(finalargs)
        result = getattr(imvar, plugfunction)(finalargs)
        return result
    # If the plugin is a terminal command
    elif plugtype == "exec":
        # Check requirements
        required = checkdicts('require')
        needed = []
        finalargs = []
        for item in required:
            needed.append(item)
        if required == ["command"]:
            finalargs.append({"command": command})
        else:
            # Get requirements
            for item in required:
                log.info("Trying to find argument {0}".format(item))
                try:
                    fetched = argfetcher.get(item)
                    log.info("Fetched the argument {0}. The value was {1}".format(
                        item, fetched))
                    finalargs.append({item: fetched})
                except Exception as e:
                    log.error("{0} occurred trying to fetch the item")
        # Find the terminal command structure
        structure = checkdicts('structure')
        # Compose the command
        for item in required:
            for arg in finalargs:
                if arg.keys()[0] == item:
                    finalval = arg.values()[0]
                    log.info("Final value of {0} is {1}".format(
                        arg, finalval))
            structure = structure.replace('{0}'.format(item), finalval)
        # Run the command and return the output
        log.info("Executing comamnd {0}".format(structure))
        resultvar = os.popen(structure).read()
        log.info("Executed command {0}, got {1}".format(
            structure, resultvar))
        if checkdicts('returns') == "answer":
            return resultvar
        else:
            return "Done"
