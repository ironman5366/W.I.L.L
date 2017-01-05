import unittest
import json
import os
import core.plugin_handler as plugin_handler
import dataset

if os.path.isfile("will.conf"):
    data_string = open("will.conf").read()
    json_data = json.loads(data_string)
    configuration_data = json_data
else:
    print "Couldn't find will.conf file, exiting"
    os._exit(1)


class plugins_subscribed(unittest.TestCase):
    def test_subscriptions(self):
        if "debug_db" in configuration_data.keys():
            db = dataset.connect(configuration_data["debug_db"])
        else:
            db = dataset.connect(configuration_data["db_url"])
        plugin_handler.load('core/plugins', db)
        plugin_num = 2
        self.assertEqual(len(plugin_handler.plugin_subscriptions), plugin_num)


if __name__ == '__main__':
    unittest.main()
