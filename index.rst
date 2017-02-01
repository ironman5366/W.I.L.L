.. W.I.L.L documentation master file, created by
   sphinx-quickstart on Mon Jan 30 13:05:39 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to W.I.L.L's documentation!
===================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   will.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
* :ref:`will`


===========
Quickstart
===========
* Send a request in python::

      import requests
      import json
      #Assume that the user has already signed up
      server_url = "http://willbeddow.com"
      payload = dict(username="myusername", password="mypassword")
      #Start the session and generate a session token. This session token will endure until you go to /end_session or the server reboots
      response = requests.post(url="{0}/api/start_session".format(server_url), data=payload).json()
      #{"type": "success", "text": "Authentication successful", "data": {"session_id": "aaaa-bbbb-cccc-dddd"}
      session_id = response["data"]["session_id"]
      #Submit a command
      command_data = dict(session_id=session_id, command="What is the meaning of life?")
      answer = requests.post(url="{0}/api/command".format(server_url), data=command_data).json()
      #{"type": "success", "text", "42 (according to the book The Hitchhiker's Guide to the Galaxy, by Douglas Adams)", "data": {"command_id": "aaaa-bbbb-cccc-dddd_1", "command_response": "42 (according to the book The Hitchhiker's Guide to the Galaxy, by Douglas Adams)"}}
      print answer["text"]
      #42 (according to the book The Hitchhiker's Guide to the Galaxy, by Douglas Adams)
      #End your session
      requests.post(url="{0}/api/end_session".format(server_url), data={"session_id": session_id})

=========
API Docs
=========
The core of the JSON API is a response object. A response object looks like this::


{"type": "success", "text": "Request successful!", "data": {}}


As you can see, each response object has three objects.

* Type
    * The type of the response. This will be either `success`, `error`, or `response`
    * `success` indicates that a request completed successfully
    * `error` indicates that a request encountered an error
    * `response` indicates that the request requires a response or a callback. The information for this will usually be in data

*  Text
    * The message to the user

* Data
    * A dictionary that contains any request specific data the user should interpret

API Methods:

* `/api/new_user`

    * Requires the following parameters in the request
    * `first_name`
    * `last_name`
    * `username`
    * `password` (the password will laster be encrypted by bcrypt in the databsae)
    * `email`
    * `default_plugin` (It's usually best just to submit search for this)

* `/api/start_session`
    * Takes `username` and `password` and returns a `session_id` in `data`
* `/api/command`
    * Takes `session_id` and `command` and returns `command_response` in `data`
* `/api/end_session`
   * Takes a `session_id` and ends it
* `/api/get_updates`
   * Takes a `session_id` and returns all pending updates and notifications
* `/api/get_sessions`
   * Takes a `username` and `password` and returns all active sessions
* `/api/check_session`
    * Takes a `session_id` and returns a boolean
* `/api/settings`
   * Requires a `username` and `password`, any other settings submitted will be changed to the value submitted
   * Ex: `{"username": "myusername", "password": "mypassword", "news_site": "http://my_new_news_site.com"}` would change the users news site to http://my_news_site.com

================
Events Framework
================
W.I.L.L has a customizable events framework that allows you to pass events and notifications that will be asynchronously
pushed to the user.
At the moment W.I.L.L offers three classes of events, two of which endure between reboots of the server
* `notification`
    * A pending notification to the user. Unlike the rest of the notifications, as well as being available from `/api/get_updates`, a notification is also pushed to the user in various ways, including email, telegram, and text.
    Information about which of these the user has enabled is stored in a JSON array in the database
    * Endures between server updates
* `url`
    * A url that will be opened, the contents of the page pushed to the updates for `/api/get_updates`
    * Endures between server updates
* `function`
    * A function object that will be run, the result pushed to the updates for `/api/get_updates`
    * Does not endure between server updates, as a python `func` object cannot be stored between runs

An event object is defined by 5 keys:
* `type`
    * The type of the event, `notification`, `url`, or `function`
* `username`
    * The username of the user who the event belongs to
* `value`
    * The data of the event. In a `notification` event it's the notification text, it's the url in a `url` event,
    and the `func` object in a `function` event
* `time`
    * The time when the event should be run in Unix epoch time.
    * Can be generated with the builtin `time` module like so::

       import time
       #The current epoch time
       current_time = time.time()
       #Set the time for a minute
       event_activation_time = current_time+60


* `uid`
    * A modified `uuid` object providing a unique identifier for the event
    * Generated with `tools.get_event_uid(type)` where `type` is the `type` key explained above

============================================
Code Example: Setting an event from a plugin
============================================

This example will set a notification event from a plugin::

   import core
   from core.plugin_handler import subscribe
   import tools
   import time

   def my_plugin_check(event):
      #Check for a keyword in the spaCy object
      return "plugin_word" in [i.orth_ for i in event["doc"]]

   @subscribe({"name":"my_plugin", "check": my_plugin_check})
   def my_plugin(event):
      #Get a unique event id
      event_id = tools.get_event_uid("notification")
      #Get an event time a minute from now
      event_time = time.time()+60
      core.events.append({
           "username": event["session"]["username"],
           "time": event_time,
           "value": "My plugin was activated!",
           "type": "notification",
           "uid": event_id
       })
