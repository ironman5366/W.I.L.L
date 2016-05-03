from expects import *
from mock import MagicMock
from will.config import FilePath
import will.plugins as plugins


with describe("will.plugins.load_plugins"):
    with it("calls plugin_loader on each plugin in plugin_paths"):
        plugin_loader = MagicMock()
        plugin_paths = "some.py plugins.py to.py check.py".split(' ')
        plugins.load_plugins(plugin_paths, plugin_loader)

        expect(plugin_loader.call_count).to(equal(len(plugin_paths)))