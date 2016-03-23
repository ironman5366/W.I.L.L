import glob
import os
from logger import log
import json
import imp


def load(dir_name="plugins"):
    """
    Iterates over files and folders in the plugins directory and returns
    meta data for plugins to be loaded.

    Args:
        dir_name (string):  The directory name or path where your plugins are
            stored.

    Returns:
        list:  A list of dicts representing the meta data for plugins.

    Raises:
        IOError:  Raised if the directory/path specified in dir_name does not
            exist or is not actually a directory.

    """
    plugins = []
    plugin_dir_path = os.path.abspath(dir_name)
    plugin_paths = map(
        lambda plugin_path: os.path.join(plugin_dir_path, plugin_path),
        os.listdir(plugin_dir_path)
    )

    if not os.path.exists(plugin_dir_path) or not os.path.isdir(plugin_dir_path):  # noqa
        log.error("Plugin directory not found.")
        raise IOError

    log.info("Loading plugins from {0}".format(plugin_dir_path))
    for plugin_path in plugin_paths:
        try:
            plugins.append(
                {os.path.basename(plugin_path): load_plugin(plugin_path)}
            )
        except IOError:
            next

    return plugins


def load_plugin(plugin_path):
    """
    Loads and returns meta data for a given plugin.

    Args:
        plugin_path (string):  The directory path to a plugin.

    Returns:
        list:  A list of dicts representing meta data of the plugin specified
            by the plugin_path.

    Raises:
        IOError:  Raised if the plugin's 'plugin.json' file doesn't exist.

    """
    plugin_json_path = os.path.join(plugin_path, "plugin.json")

    if not os.path.isdir(plugin_path):
        raise IOError
    if not os.path.exists(plugin_json_path) or not os.path.isfile(plugin_json_path):  # noqa
        log.warn("\"plugin.json\" at \"{0}\" does not exist.")
        raise IOError

    log.info("Loading plugin {0}".format(plugin_json_path))
    with open(plugin_json_path, 'r') as json_file:
        plugin_json = json.load(json_file)

    return plugin_json


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
	try:
        	result = getattr(imvar, plugfunction)(finalargs)
	except TypeError:
		result = getattr(imvar, plugfunction)
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
