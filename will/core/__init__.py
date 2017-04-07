#Builtin modules
import logging
import os

#Internal modules
try:
    pass
except ImportError:
    import plugin_handler
    import parser
from will.exceptions import *

log = logging.getLogger()

class core:
    def __init__(self, configuration_data):
        self.configuration_data = configuration_data
        plugin_configuration = self.configuration_data["plugins"]
        error_cause = None
        # Validate the plugin configuration
        try:
            error_cause = "dir"
            assert type(plugin_configuration["dir"]) == str
            assert os.path.isdir(plugin_configuration["dir"])
        except (KeyError, AssertionError):
            error_string = "Plugin configuration is invalid. Please check the {0} field.".format(error_cause)
            log.error(error_string)
            raise ConfigurationError(error_string)
        self.plugins = plugin_handler.load(plugin_configuration["dir"])

