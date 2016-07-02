# W.I.L.L

W.I.L.L is a Python based, event and plugin driven personal assistant.

  - Smart, efficient, spacy driven multithreaded nlp
  - A full, event driven plugin framework supporting multiple types of plugins with room for expansion
  - Can be used with a variety of different clients

Plugins:
  - Can be written in Python or Json (more coming!) 
  - Are activiated on W.I.L.L initiation or shutdown
  - Are activated based on entity recognition, POS tags, keywords, or even the presence of questions
  - Can interactively communicate with the user without having to re-run parsing every time
  

W.I.L.L started as my personal project but now has an active community of users and contributers. If you want to contribute by adding plugins, or even editing the framework, just submit a pull reuqest! Working plugins that are legal, useful, and original will always be accepted. .

### Version
3.0.1

### Tech

W.I.L.L is open source with a  [public repository][will]
 on GitHub.

### Installation

W.I.L.L is available via pip with `pip install W\I\L\L`

After installation, you need a wolframalpha API key to run the search module. Get one from http://products.wolframalpha.com/api/

After you have it, go to your W.I.L.L installation directory (find out where pip installs things on your OS), and copy example_config.json to config.json. Then, add the following lines as the last item entry:
```json
"wolfram":
  {
    "keys": ["YOUR_KEY"]
  }
```
### Plugins

The following plugins are currently available for W.I.L.L, with many more on the way.

Finished:
* Open (Use xdg-open, start, or open to open any program or file on the operating system)
* Search (Use Google, Wolframalpha, and Wikipedia to find an answer to most questions)
* Execute (Execute a terminal command)

In development:
* Chromecast (Uses pychromecast and splinter to cast several popular streaming services)
* Spotify (Access Spotify premium API)

### Plugin Creation

Writing a plugin for W.I.L.L is easier than you might think. Currently, W.I.L.L supports two types of plugins. Json and Python. All plugins should go in W.I.L.L/plugins.

Special thanks to https://github.com/brenttaylor for his contributions to the plugin framework

#### Python
The way W.I.L.L is designed, you can plug in pretty much any python file that you've made, just by adding a decorator.
Let's write a plugin. First, you need to import the API that W.I.L.L uses. If you're in the plugin directory, you can do that with this line:
```python
import will.plugins.API as API
```
Now we can write a function that we want W.I.L.L to execute. All plugin functions should accept 4 arguments. The first will be the first word of the command. The second will be the raw, full text of the command. The third should be *args, and that will contain all of the nlp data that your plugin might want to access. The fourth should be **kwargs, and that will contain metadata about the command. You shouldn't needed this unless you're debugging the plugin framework
```python
def test_func(leader, sentence, *args, **kwargs):
    print leader #The first word of the command
    print sentence #The entire command
    print args['ents'] #A dict of recognized entities
    print args['struct'] #A dict of recognized pos tags
    print kwargs #Dispatcher debug info
```
Now that we have that function, let's hook it up to the W.I.L.L API with a decorator. There are currently 4 functions inside the api that you can use. The first two go together. `@init`, which will run on initialization of W.I.L.L, and `@shutdown`, which will run as W.I.L.L exits. These do not need the standard arugments in the accompanying functions. Next, we have `@API.subscribe_to_any`. That will, as the name implies, be activated when any command is entered into W.I.L.L. Finally, the most important one. `@API.subscribe_to`. Unlike the others, this requires input data, so W.I.L.L can know under what circumstances to run it. You'll pass it a dictionary containing a neat package of information about the plugin. Included in this dictionary are the name of the plugin, what entities the plugin needs (list of supported entities can be found at https://spacy.io/docs#annotation-ner), what parts of speech the plugin needs, if the plugin needs questions, and any key words that it needs. Here's a sample of the dictionary.
```python
{
"name" : "test",
"ents_needed" : ["PERSON"], #Could also be left empty by writing "ents_needed" : False
"structure" : {"needed":["VERB"]}, #Could also be left empty with "structure" : {"needed":False}
"questions_needed" : False, #Always a bool, True or False if it needs questions or not
"key_words" : ["test"] #Can be left empty with"key_words" : False
}
```
Finally, you can load values in the config by importing will.config. Import it like this:
```python
import will.config as config
```
There are threwe methods available to plugins in config, `load_config`,`remove_config`, and `add_config`. `load_config`takes a header of something already in the config and returns the value. `add_config` updates the config with a dictionary passed to it, and `remove_config` removes takes a header and removes that item from the config. Like so:
```python
import will.config as config

#Add an item to the config
config.add_config({"docs_read" : True})

#Load an item from the config
docs_read = config.load_config("docs_read") #The value you just added

#Remove the item from the config
config.remove_config("docs_read")
```

Now that we've written our function defined the plugin, and familiarized ourself with the methods, let's tie it all together in a file.

`W.I.L.L/plugins/test.py`
```python
import will.plugins.API as API
import will.config as config

#A function that will run on initialization
@init
def on_init():
    print "W.I.L.L Started!"
    #Add an item into the config
    config.add_config({"will_started" : True})

#The dictionary we made earlier
plugin_data = 
{
"name" : "test",
"ents_needed" : ["PERSON"], #Could also be left empty by writing "ents_needed" : False
"structure" : {"needed":["VERB"]}, #Could also be left empty with "structure" : {"needed":False}
"questions_needed" : False, #Always a bool, True or False if it needs questions or not
"key_words" : ["test"] #Can be left empty with"key_words" : False
}

#Subscribe the plugin_data dictionary to the function we wrote earlier
@API.subscribe_to(plugin_data)
def test_func(leader, sentence, *args, **kwargs):
    print leader #The first word of the command
    print sentence #The entire command
    print args['ents'] #A dict of recognized entities
    print args['structure']['tags'] #A dict of recognized pos tags
    print kwargs #Dispatcher debug info
    #While we're in the function, why not load the config item we added earlier
    will_started = config.load_config("will_started")
    print will_started
    
#A function that will run as will exits
@shutdown
def on_shutdown():
    print "W.I.L.L is shutting down"
    #Remove the config item
    config.remove_config("will_started")
```

Now let's run our plugin! So we can see what's going on, let's use W.I.L.L in the terminal
```python
>>>import will #This might take some time as the nlp models take time to load
>>>will.run()
W.I.L.L Started!
>>>will.main("test this sentence includes Will, a person")
test
test this sentence includes Will, a person
{"Will", "PERSON"}
{'a': 'DT', 'sentence': 'NN', 'this': 'DT', 'is': 'VBZ', 'who': 'WP', ',': ',', 'includes': 'VBZ', 'Will': 'NNP', u'person': 'NN', 'test': 'NN'}
{'signal': 'test', 'sender': _Any}
True
>>>will.exit_func() #This will be called however W.I.L.L exits, you don't need to call it explicitly
W.I.L.L is shutting down
```
And there you have it! A working W.I.L.L plugin!
### Todos
 
 - Write setup scripts
 - Add JSON plugin docs
 - Add client creation docs
 - Chromecast plugin
 - Spotify plugin
 - Add more structural NLP
 - Add more clients

License
----

MIT

These docs made on dillinger.io, off the default template. 





   [will]: <https://github.com/ironman5366/W.I.L.L>
