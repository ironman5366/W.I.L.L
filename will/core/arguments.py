import logging

log = logging.getLogger()

# TODO: consider an Argument class from which both BasicArgument and ComplexArgument inherit

# Built in validation
class Argument:
    argument_type = str
    def valid(self):
        pass
    def __init__(self, argument, possible_settings={}):
        self._argument = argument
        self._possible_settings = possible_settings

class Command(Argument):
    pass

class ComplexArgument(Argument):
    pass