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