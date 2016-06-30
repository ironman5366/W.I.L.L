import pyplugins
import os
import jsonplugins
from pydispatch import dispatcher
from will.collections import DictObject
from will.logger import log
from will import nlp
import time

def load(dir_path):
    '''Loads plugins'''
    plugins = lambda: (os.path.join(dir_path, module_path)
                       for module_path in os.listdir(dir_path))
    load_plugins(plugins(), pyplugins.plugin_loader)
    load_plugins(plugins(), jsonplugins.plugin_loader)
    dispatcher.send(signal=pyplugins.EVT_INIT)

def load_plugins(plugin_paths, plugin_loader):
    ''''''
    map(lambda plugin: plugin_loader(plugin), plugin_paths)


def unload_all():
    pyplugins.unload_all()

class Command(DictObject):

    def __init__(self, expression):
        word = expression.split(' ')[0].lower()  # First word of expression
        nlp.main().parse(expression)
        expression = expression[len(word) + 1:]
        super(Command, self).__init__(word=word,
                                      event=word,
                                      expression=expression)
    #TODO: fix the way the subscribing and dispatching is handled
    def dispatch_event(self):
        return_values = []
        log.info("In dispatch_event")
        while not nlp.plugins_final:
            time.sleep(0.001)
        plugins_final = nlp.plugins_final
        log.info("plugins_final is {0}".format(str(plugins_final)))
        handlers = pyplugins._event_handlers
        log.info("Event handlers are {0}".format(str(handlers)))
        return_values.extend(
            dispatcher.send(pyplugins.EVT_ANY_INPUT, dispatcher.Any,
                            self.expression)
        )
        return_values.extend(
            dispatcher.send(
                self.event, dispatcher.Any, self.word, self.expression, plugins_final)
        )

        if len(return_values) > 0:
            return map(lambda x: '' if x is None else x,
                       map(lambda x: x[1], return_values))
        return tuple()
