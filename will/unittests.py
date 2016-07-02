import unittest


class TestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        import logging
        logging.disable(logging.CRITICAL)

        super(TestCase, self).__init__(*args, **kwargs)