import os
import sys
from will.logger import log
import json
import imp
import will.argfetcher as argfetcher


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


# TODO Remove this entirely.  It's a horrible way to work with dicts.
def checkdicts(plugin, checkvar):
    """
    This function iterates over the dictionaries in the plugin list.
    I have no excuse for it.
    """
    for plugin_dict in plugin.values()[0]:
        if plugin_dict.keys()[0] == checkvar:
            return plugin_dict.values()[0]
    raise ValueError


# TODO Document after plugin data is refactored
def execute_python_plugin(plugin, command):
    python_plugin_name = checkdicts(plugin, 'file')
    python_plugin_path = os.path.abspath("plugins/{0}/{1}".format(
        plugin.keys()[0], python_plugin_name
    ))
    lib_path = os.path.abspath("plugins/{0}".format(plugin.keys()[0]))

    if lib_path not in sys.path:
        sys.path.append(lib_path)

    log.info("Loading python plugin: {0}".format(python_plugin_path))
    # Why are we reloading the python module every time we call out to it?
    python_plugin_module = imp.load_source('plugfile', python_plugin_path)
    python_plugin_entry_point = checkdicts(plugin, 'function')
    final_arguments = (command,)  # Why wouldn't this just be
    # "final_arguments=command" or better yet, just pass in the command itself

    log.info("Calling into python plugin: {0}".format(python_plugin_path))
    try:
        return getattr(python_plugin_module,
                       python_plugin_entry_point)(final_arguments)
    except TypeError:
        return getattr(python_plugin_module, python_plugin_entry_point)


# TODO factor this out entirely
def get_requirements(args):
    results = []
    for item in args:
        try:
            results.append(
                {item: argfetcher.get(item)}
            )
        except Exception as e:
            log.exception("{0} occured trying to fetch item".format(e))
    return results


# TODO factor this out entirely
def construct_exec_command(structure, expected_arguments, final_arguments):
    for item in expected_arguments:
        for arg in final_arguments:
            if arg.keys()[0] == item:
                return structure.replace('{0}'.format(item), arg.values()[0])


# TODO Document after plugin data is refactored
def execute_exec_plugin(plugin, command):
    expected_arguments = checkdicts(plugin, 'require')
    structure = checkdicts(plugin, 'structure')
    final_arguments = []

    if expected_arguments == ["command"]:
        final_arguments.append({"command": command})
    else:
        final_arguments = get_requirements(expected_arguments)

    structure = construct_exec_command(
        structure,
        expected_arguments,
        final_arguments
    )

    log.info("Executing comamnd {0}".format(structure))
    results = os.popen(structure).read()
    log.info("Executed command {0}, got {1}".format(structure, results))
    if checkdicts(plugin, 'returns') == "answer":
        return results
    else:
        return "Done"


# TODO Document after the plugin data is refactored
def execute(plugin, command):
    """
    Execute a plugin. The plugin arg is the info from the plugin.json file
    """
    log.info("Executing plugin {0}".format(plugin))
    plugtype = checkdicts(plugin, 'type')
    # Check if the plugin wants the first word from the command.
    firstword = checkdicts(plugin, 'firstword')
    if firstword == 'no':
        command = command.split(command.split(" ")[0] + " ")[1]

    if plugtype == "python":
        return execute_python_plugin(plugin, command)
    # If the plugin is a terminal command
    elif plugtype == "exec":
        return execute_exec_plugin(plugin, command)
