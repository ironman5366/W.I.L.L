from distutils.core import setup
import os
import sys
setup(
  name = 'WillPy',
  packages = ['WillPy'],
  version = '3.3',
  description = 'A smart personal assistant',
install_requires=['beautifulsoup4', 'dateutils', 'easygui', 'expects', 'funcsigs', 'itsdangerous', 'MarkupSafe', 'mock', 'nose', 'pbr', 'PyDispatcher', 'python-dateutil', 'pytz', 'requests', 'six', 'termcolor', 'tinydb', 'voluptuous', 'websocket-client', 'Werkzeug', 'wikipedia', 'wolframalpha', 'spacy', 'keyring', 'pychromecast'],
  author = 'Will Beddow',
  author_email = 'WillPy@willbeddow.com',
  url = 'https://github.com/ironman5366/WillPy',
  download_url = 'https://github.com/ironman5366/WillPy/tarball/3.2',
  keywords = ['Personal Assistant', 'Plugins'],
  classifiers = [],
)