import unittest
import tools
import json
import os
import dataset
import core.plugin_handler as plugin_handler
import core.notification as notification
import logging

logging.basicConfig(filename="unittests.log", level=logging.DEBUG)

if os.path.isfile("will.conf"):
    data_string = open("will.conf").read()
    json_data = json.loads(data_string)
    configuration_data = json_data
else:
    print "Couldn't find will.conf file, exiting"
    os._exit(1)

class KeySort(unittest.TestCase):
    def test_key_sort(self):
        if "debug_db" in configuration_data.keys():
            db = dataset.connect(configuration_data["debug_db"])
        else:
            db = dataset.connect(configuration_data["db_url"])
        key = tools.load_key("wolfram", db)
        self.assertEqual(True, True)

class plugins_subscribed(unittest.TestCase):
    def test_subscriptions(self):
        if "debug_db" in configuration_data.keys():
            db = dataset.connect(configuration_data["debug_db"])
        else:
            db = dataset.connect(configuration_data["db_url"])
        plugin_handler.load('core/plugins', db)
        plugin_num = 2
        self.assertEqual(len(plugin_handler.plugin_subscriptions), plugin_num)

class notification_send(unittest.TestCase):
    def test_email(self):
        if "debug_db" in configuration_data.keys():
            db = dataset.connect(configuration_data["debug_db"])
        else:
            db = dataset.connect(configuration_data["db_url"])
        notification.send_notification({"username": "willbeddow", "text": "This is a sample reminder that also tests the 5 word summary"}, db)

if __name__ == '__main__':
    unittest.main()
