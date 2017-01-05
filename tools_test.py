import unittest
import tools
import json
import os
import dataset

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


if __name__ == '__main__':
    unittest.main()
