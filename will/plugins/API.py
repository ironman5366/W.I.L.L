"""
-----------------------------------
Public facing API for WILL plugins.
-----------------------------------

Will uses an event driven plugin architecture revolving around the simple use
of decorators.  Writing a plugin for WILL is as simple as subscribing to an event
via a simple decorator.

Events currently come in two varieties, "System Events" and "Key Word Events".

System Events:
    System events are events that are internal to WILL, such as plugin
    initialization and system shutdown events.

Key Word Events:
    Key word events are the bread and butter of WILL.  These are subscription
    events allowing functions in plugins to subscribe to specific key words or
    phrases.

Decorators currently provided:
    System Events:
        @init
        @shutdown
    Key Word Events:
        @subscribe_to
        @subscribe_to_any

Example:
>> # plugins/echo.py
>> import will.plugins.API as API
>>
>>
>> @API.subscribe_to("echo")
>> def echo(word, full_text):
>>    return full_text
>>

Echo.py subscribes to the key word "echo" and returns the very same message
received.
"""

import pyplugins as plugins
import will.logger as logger


"""
Decorator that subscribes the decorated function to the init event.  This
event gets called when the plugin system in first initialized.

Examples:

myfile = None


@API.init
def setup():
    global myfile
    myfile = open("somefile.txt", 'w')
"""
init = plugins.event(plugins.EVT_INIT)


"""
Decorator that subscribes the decorated function to the shutdown event.  This
is called whenever the entire system is shutting down allowing for cleanup of
any resources being used such as databases or file handles.

Example:
#myfile being an open file handle

@API.shutdown
def on_exit():
    myfile.close()
"""
shutdown = plugins.event(plugins.EVT_EXIT)


"""
Decorator that subscribes the decorated function to the "any" event.  This event
is called whenever any text is sent through WILL.  This is particularly good for
any functions that may do logging and need access to every line of text sent
through your slack channel or whatever front end you are using.  Anything
returned from the decorated function will be sent back to the requesting client.

Example:

#myfile being an open file handle

@API.subscribe_to_any
def logger(text):
    myfile.write("{0}\n".format(text))
"""
subscribe_to_any = plugins.event(plugins.EVT_ANY_INPUT)


"""
Decorator that subscribes the decorated function to a single, or series, of
key word events.  Anything returned from the decorated function will be sent
back to the requesting client.

Args:
    keywords:
        Either a single string used as a key word or a list/tuple of key words.

Examples:

@API.subscribe_to("echo"):
def echo(keyword, full_text):
    return full_text

@API.subscribe_to(["echo", "repeat", "say"])
def echo(keyword, full_text):
    return full_text
"""
subscribe_to = plugins.event

"""
Standard logging for WILL.  See python's "logging" module for documentation.
"""
log = logger.log
