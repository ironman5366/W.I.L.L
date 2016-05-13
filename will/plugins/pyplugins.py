import os
import sys
import importlib
from pydispatch import dispatcher
from collections import Iterable
from will.logger import log
from will.collections import DictObject

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


class PythonLoader:
    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        pass

    def is_plugin(self, fs_tools=os.path):
        if fs_tools.exists(self.file_path):
            if fs_tools.isfile(self.file_path):
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
        pass

    def _lib_path(self):
        return os.path.normpath(
            os.sep.join(os.path.normpath(self.file_path).split(os.sep)[:-1])
        )


def get_import_name(path, fs_tools=os.path):
    if path.endswith('.py') and fs_tools.exists(path):
        return fs_tools.basename(path).split('.')[0]
    if fs_tools.isdir(path) and fs_tools.exists(fs_tools.join(path, '__init__.py')):
        return fs_tools.basename(path)
    raise IOError("File is not a python plugin: {0}".format(path))


def get_lib_path(path):
    return os.path.normpath(
        os.sep.join(os.path.normpath(path).split(os.sep)[:-1])
    )


def load_plugin_meta_data(path):
    try:
        return DictObject(
            lib_path=get_lib_path(path),
            import_name=get_import_name(path),
            is_plugin=True
        )
    except IOError:
        return DictObject(
            lib_path="",
            import_name="",
            is_plugin=False
        )


def plugin_loader_old(path):
    meta_data = load_plugin_meta_data(path)
    if meta_data.is_plugin:
        log.info("Loading plugin: {0}".format(path))
        if meta_data.lib_path not in sys.path:
            sys.path.append(meta_data.lib_path)
        importlib.import_module(meta_data.import_name)

