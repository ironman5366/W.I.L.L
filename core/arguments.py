import logging

log = logging.getLogger()

class Argument:

    @property
    def valid(self):
        if type(self._argument) == self.argument_type:
            pass
        return False

    def _build(self):
        pass

    def __init__(self, argument):
        self._argument = argument

class Location(Argument):
    pass