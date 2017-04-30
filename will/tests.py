import logging
import unittest
import will
from will.API import tests as api_tests


log = logging.getLogger()

json_header = "application/json"
Will = will.will(conf_file="will_tests.conf")


class InstanceTests(unittest.TestCase):
    """
    Tests that test attributes of the running W.I.L.L instance
    """
    pass


class ModuleTests(unittest.TestSuite):
    modules = [api_tests]

    def test_process(self):
        """
        Load tests from each module and add their test classes to the ModuleTests test suite
        
        """
        for test_module in self.modules:
            test_module.Will = Will
            self.addTests(test_module.tests)


if __name__ == '__main__':
    unittest.main()
