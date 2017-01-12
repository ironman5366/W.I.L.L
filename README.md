#W.I.L.L

##Welcome to W.I.L.L
W.I.L.L is an open source personal assistant that aims to be free, easy to use, and expandable by the user.
It runs on a python based plugin framework accessible by a JSON API that let's you access it from a variety of different platforms.
We've provided some platforms for you, but if you don't like any of those, you can easily create your own, or, if you want to change W.I.L.L, setup your own version


##Quickstart

###Use a provided platform

####Signup
Before you can use W.I.L.L, you need to sign up.
You can sign up for free at http://willbeddow.com/signup

#####Telegram
All you have to do to use W.I.L.L on telegram is go @WillAssistantBot and click start!

###Use the json api
The main W.I.L.L server, as well as the web app, is at http://willbeddow.com
It runs on a flask server that provides a JSON API

###Quickstart
####Send a request with python
```python
import requests
import json
#Assume that the user has already signed up
server_url = "http://67.205.186.54/api"
payload = dict(username="myusername", password="mypassword")
#Start the session and generate a session token. This session token will endure until you go to /end_session or the server reboots
response = requests.post(url="{0}/api/start_session".format(server_url), data=payload)
#{"type": "success", "text": "Authentication successful", "data": {"session_id": "aaaa-bbbb-cccc-dddd"}
session_id = response["data"]["session_id"]
#Submit a command
command_data = dict(session_id=session_id, command="What is the meaning of life?")
answer = requests.post(url="{0}/api/command".format(server_url), data=command_data)
#{"type": "success", "text", "42 (according to the book The Hitchhiker's Guide to the Galaxy, by Douglas Adams)", "data": {"command_id": "aaaa-bbbb-cccc-dddd_1", "command_response": "42 (according to the book The Hitchhiker's Guide to the Galaxy, by Douglas Adams)"}}
print answer["text"]
#42 (according to the book The Hitchhiker's Guide to the Galaxy, by Douglas Adams)
```


###API Docs:
The core of he JSON API is a response object. A response object looks like this:
```json
{"type": "success", "text": "Request successful!", "data": {}}
```
As you can see, each response object has three objects.
- Type
    - The type of the response. This will be either `success`, `error`, or `response`
    - `success` indicates that a request completed successfully
    - `error` indicates that a request encountered an error
    - `response`indicates that the request requires a response or a callback. The information for this will usually be in data
-  Text
    - The message to the user
- Data
    - A dictionary that contains any request specific data the user should interpret

API Methods:
- `/api/new_user`
    - Requires the following parameters in the request
    - `first_name`
    - `last_name`
    - `username`
    - `password` (the password will laster be encrypted by bcrypt in the databsae)
    - `email`
    - `default_plugin` (It's usually best just to submit search for this)
- `/api/start_session`
    - Takes `username` and `password` and returns a `session_id` in `data`
- `/api/command`
    - Takes `session_id` and `command` and returns `command_response` in `data`
- `/api/end_session`
    Takes a `session_id` and ends it
- `/api/get_updates`
   - Takes a `session_id` and returns all pending updates and notifications
- `/api/get_sessions`
   - Takes a `username` and `password` and returns all active sessions


###Events framework
W.I.L.L has a customizable events framework that allows you to pass events and notifications that will be asynchronously
pushed to the user. 
At the moment W.I.L.L offers three classes of events, two of which endure between reboots of the server
- `notification`
    - A pending notification to the user. Unlike the rest of the notifications, as well as being available from 
    `/api/get_updates`, a notification is also pushed to the user in various ways, including email, telegram, and text.
    Information about which of these the user has enabled is stored in a JSON array in the database
    - Endures between server updates
- `url`
    - A url that will be opened, the contents of the page pushed to the updates for `/api/get_updates`
    - Endures between server updates
- `function`
    - A function object that will be run, the result pushed to the updates for `/api/get_updates`
    - Does not endure between server updates, as a python `func` object cannot be stored between runs

An event object is defined by 5 keys:
- `type`
    - The type of the event, `notification`, `url`, or `function`
- `username`
    - The username of the user who the event belongs to
- `value`
    - The data of the event. In a `notification` event it's the notification text, it's the url in a `url` event, 
    and the `func` object in a `function` event
- `time`
    - The time when the event should be run in Unix epoch time.
    - Can be generated with the builtin `time` module like so:
 ```python
    import time
    #The current epoch time
    current_time = time.time()
    #Set the time for a minute
    event_activation_time = current_time+60
```
- `uid`
    - A modified `uuid` object providing a unique identifier for the event
    - Generated with `tools.get_event_uid(type)` where `type` is the `type` key explained above
    
