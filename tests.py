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

if "debug_db" in configuration_data.keys():
    db = dataset.connect(configuration_data["debug_db"])
else:
    db = dataset.connect(configuration_data["db_url"])

class KeySort(unittest.TestCase):
    def test_key_sort(self):
        key = tools.load_key("wolfram", db)
        self.assertEqual(True, True)

class plugin_tests(unittest.TestCase):
    def test_subscriptions(self):
        plugin_handler.load('core/plugins', db)
        plugin_num = 5
        print plugin_handler.plugin_subscriptions
        self.assertEqual(len(plugin_handler.plugin_subscriptions), plugin_num)
    def test_search(self):
        call_function = None
        plugin_handler.load('core/plugins', db)
        for i in plugin_handler.plugin_subscriptions:
            if i['name'] == "search":
                call_function = i["function"]
        searches = [
            "Who is the queen of england?",
            "How old is putin?",
            "When did napoleon die?",
            "Who invented python?",
            "what day is it",
            "what's 27 times 62",
            "When did bach die?",
            "Who is will beddow?",
            "Who's obama?"
        ]
        def do_search(query, call_function):
            print (plugin_handler.subscriptions().call_plugin(call_function, {
                "command": query, "db": db, "user_table":db['users'].find_one(username="willbeddow")}))
        map(lambda x: do_search(x, call_function), searches)
    def test_news(self):
        call_function = None
        plugin_handler.load('core/plugins', db)
        for i in plugin_handler.plugin_subscriptions:
            if i['name'] == "news":
                call_function = i["function"]
        print call_function({"command": "Read me the news", "username": "willbeddow", "db": db})
    def test_weather(self):
        call_function = None
        plugin_handler.load('core/plugins', db)
        for i in plugin_handler.plugin_subscriptions:
            if i['name'] == "weather":
                call_function = i["function"]
        response = call_function({"command": "Tell me the weather", "username": "willbeddow", "db": db})
        logging.info("Weather response is {0}".format(response))
        print response
    # def test_spotify(self):
    #     call_function = None
    #     plugin_handler.load('core/plugins', db)
    #     for i in plugin_handler.plugin_subscriptions:
    #         if i['name'] == "spotify":
    #             call_function = i["function"]
    #     command = "Play Yesterday on Spotify"
    #     response = call_function({"command": command, "doc": nlp(unicode(command))})
    #     print response
class notification_send(unittest.TestCase):
    def test_email(self):
        notification.send_notification(
            {"username": "willbeddow",
             "value": "This is a sample reminder that also tests the 5 word summary"},
            db)

if __name__ == '__main__':
    unittest.main()
