# Builtin imports
from unittest.mock import *
import unittest
import os

# Internal imports
from will import core
from will import tools


class PluginLoadTests(unittest.TestCase):
    """
    Basic tests to assert that the plugin loader is running correctly
    """
    def setUp(self):
        """
        Mock out tools.parser
        """
        tools.parser = MagicMock()

    def test_correct_load(self):
        """
        Send the plugin loader correct configuration data and assert that the correct plugins are loaded
        """
        configuration_data = {
            "plugins":
                {
                    "dir": "{}/will/core/plugins".format(os.path.dirname(os.getcwd()))
                }
        }
        core_instance = core.Core(configuration_data=configuration_data)
        # Validate the plugins
        core_plugins = core_instance.plugins
        # Assert that all of the plugins are getting loaded
        correct_plugin_num = len([
            i for i in os.listdir("../will/core/plugins") if i.endswith(".py") and not i.startswith("__")])
        self.assertEqual(len(core_plugins), correct_plugin_num)