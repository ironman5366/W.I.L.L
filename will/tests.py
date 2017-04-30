import logging
import unittest
import will
from will.API import tests


log = logging.getLogger()

json_header = "application/json"
print("Loading will")
Will = will.will(conf_file="will_tests.conf")
print("Loaded W.I.L.L")


class InstanceTests(unittest.TestCase):
    pass

if __name__ == '__main__':
    unittest.main()
