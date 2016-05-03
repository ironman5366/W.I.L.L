import os
import sys
import importlib
from pydispatch import dispatcher
from collections import Iterable
from will.logger import log

# Events
EVT_INIT = "will_evt_init"
EVT_EXIT = "will_evt_exit"
EVT_ANY_INPUT = "will_evt_any_input"

_event_handlers = {}


def event(events):
    def subscribe(evt, func):
        dispatcher.connect(func, signal=evt)
        if event not in _event_handlers:
            _event_handlers[evt] = []
        _event_handlers[evt].append(func)

    def decorator(func):
        if not isinstance(events, str) and isinstance(events, Iterable):
            for evt in events:
                subscribe(evt, func)
        else:
            subscribe(events, func)
        return func

    return decorator


class PluginFilePath:
    def __init__(self, file_path):
        self.file_path = file_path

    def __str__(self):
        return str(self.file_path)

    def get_lib_path(self):
        return os.path.normpath(
            os.sep.join(str(self.file_path).split(os.sep)[:-1])
        )

    def get_module_name(self):
        if not self.file_path.exists():
            raise IOError("No such file or directory: {0}".format(self.file_path))

        if self.file_path.is_directory():
            return self._dir_path()
        else:
            return self._file_path()

    def is_plugin(self):
        for call in [self._file_path, self._dir_path]:
            try:
                call()
            except IOError:
                continue
            return True
        return False

    def _file_path(self):
        if str(self.file_path).endswith('.py'):
            return self.file_path.base_name().split('.')[0]
        raise IOError("File is not a python plugin: {0}".format(self.file_path))

    def _dir_path(self):
        if self.file_path.join('__init__.py').exists():
            return self.file_path.base_name()
        raise IOError("File is not a python plugin: {0}".format(self.file_path))


def plugin_loader(path):
    plugin_path = PluginFilePath(path)
    lib_path = plugin_path.get_lib_path()
    try:
        if plugin_path.is_plugin():
            log.info("Loading plugin: {0}".format(str(plugin_path)))
            if lib_path not in sys.path:
                sys.path.append(lib_path)
            importlib.import_module(plugin_path.get_module_name())
    except IOError:
        return


def unload_all():
    dispatcher.send(EVT_EXIT)

    # note, a copy of the _event_handlers[event] list is made here with the [:]
    # syntax as we are going to be removing event handlers from the list and
    # we can't do this while iterating over the same list.

    for event, handlers in _event_handlers.iteritems():
        for handler in handlers[:]:
            dispatcher.disconnect(handler, signal=event)
            _event_handlers[event].remove(handler)

