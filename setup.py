from distutils.core import setup
setup(
  name = 'W.I.L.L',
  packages = ['W.I.L.L', 'beautifulsoup4', 'dateutils', 'easygui', 'expects', 'funcsigs', 'itsdangerous', 'MarkupSafe', 'mock', 'nose', 'pbr', 'PyDispatcher', 'python-dateutil', 'pytz', 'requests', 'six', 'termcolor', 'tinydb', 'voluptuous', 'websocket-client', 'Werkzeug', 'wikipedia', 'wolframalpha', 'spacy', 'keyring', 'pychromecast'], # this must be the same as the name above
  version = '3.1',
  description = 'A smart personal assistant',
  author = 'Will Beddow',
  author_email = 'will@willbeddow.com',
  url = 'https://github.com/ironman5366/W.I.L.L',
  download_url = 'https://github.com/ironman5366/W.I.L.L/tarball/3.1',
  keywords = ['Personal Assistant', 'Plugins'],
  classifiers = [],
)
def wolfram_setup():
    wolframalpha_key = raw_input("Please enter a wolframalpha key. You can get one from http://products.wolframalpha.com/api/>")
    if wolframalpha_key:
        import will.config as config
        config.add_config({"wolfram" : [wolframalpha_key]})
    else:
        if raw_input("This is a required step for setup, are you sure you want to quit? (y/n)").lower() != "y":
            wolfram_setup()