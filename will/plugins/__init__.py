import pyplugins
import os
from pydispatch import dispatcher
from will.collections import DictObject


def load(dir_path):
    plugins = (dir_path.join(module_path)
               for module_path in os.listdir(str(dir_path)))
    load_plugins(plugins, pyplugins.plugin_loader)
    # JSON plugins loaded next
    dispatcher.send(signal=pyplugins.EVT_INIT)


def load_plugins(plugin_paths, plugin_loader):
    map(lambda plugin: plugin_loader(plugin), plugin_paths)


def unload_all():
    pyplugins.unload_all()


class Command(DictObject):
    def __init__(self, expression):
        word = expression.split(' ')[0].lower()  # First word of expression
        super(Command, self).__init__(word=word,
                                      event=word,
                                      expression=expression)

    def dispatch_event(self):
        return_values = []
        return_values.extend(
            dispatcher.send(pyplugins.EVT_ANY_INPUT, dispatcher.Any, self.expression)
        )
        return_values.extend(
            dispatcher.send(
                self.event, dispatcher.Any, self.word, self.expression)
        )

        if len(return_values) > 0:
            return map(lambda x: x[1], return_values)
        return tuple()
