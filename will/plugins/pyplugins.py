import os
import sys
import importlib
from pydispatch import dispatcher
from collections import Iterable
from will.logger import log
from will import nlp

# Events
EVT_INIT = "will_evt_init"
EVT_EXIT = "will_evt_exit"
EVT_ANY_INPUT = "will_evt_any_input"

_event_handlers = {}


def plugin_loader(path):
    python_loader = PythonLoader(path)

    try:
        python_loader.load()
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
def event(events, **kwargs):
    log.info("In event, events are {0}".format(str(events)))
    log.info("In event, kwargs are {0}".format(str(kwargs)))
    def subscribe(evt, func):
        dispatcher.connect(func, signal=evt)
        if event not in _event_handlers:
            _event_handlers[evt] = []
        _event_handlers[evt].append(func)


    def decorator(func):
        log.info(func)
        # Append the plugin data to the nlp parsing que
        log.info("Appending {0} to nlp.current_plugins".format(str(events)))
        nlp.current_plugins.append(events)
        if not isinstance(events, str) and isinstance(events, Iterable) and not isinstance(events, dict):
            for evt in events:
                log.info("subscribing evt {0}".format(evt))
                subscribe(evt, func)
        elif isinstance(events, dict):
            log.info(events)
            evt_keywords = events["key_words"]
            if evt_keywords:
                for key_word in evt_keywords:
                    log.info("Subscribing {0} to {1}".format(key_word, str(func)))
                    subscribe(key_word, func)
            else:
                log.info("Error: event {0} has no attribute name".format(str(events)))
        else:
            subscribe(events, func)
        return func


    return decorator


class PythonLoader:

    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        if self.is_plugin():
            log.info("Loading plugin: {0}".format(self.file_path))
            self.update_path()
            importlib.import_module(self.import_name())

    def is_plugin(self, fs_tools=os.path):
        if fs_tools.exists(self.file_path):
            if fs_tools.isfile(self.file_path) and \
                    self.file_path.endswith('.py'):
                return True
            if fs_tools.isdir(self.file_path):
                init_file = os.path.join(self.file_path, "__init__.py")
                if fs_tools.exists(init_file) and fs_tools.isfile(init_file):
                    return True
        return False

    def import_name(self):
        if self.file_path.endswith('.py'):
            return os.path.basename(self.file_path).split('.')[0]
        else:
            return os.path.basename(self.file_path)

    def update_path(self):
        lib_path = self._lib_path()
        if lib_path not in sys.path:
            sys.path.append(lib_path)

    def _lib_path(self):
        return os.path.normpath(
            os.sep.join(os.path.normpath(self.file_path).split(os.sep)[:-1])
        )
