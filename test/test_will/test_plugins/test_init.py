import unittest
from mock import MagicMock
from expects import *
import will.plugins as plugins


class TestLoadPlugins(unittest.TestCase):
    def test_ShouldCallPluginLoaderOnEachPluginInPluginPaths(self):
        plugin_loader = MagicMock()
        plugin_paths = "some.py plugins.py to.py check.py".split(' ')
        plugins.load_plugins(plugin_paths, plugin_loader)

        expect(plugin_loader.call_count).to(equal(len(plugin_paths)))

