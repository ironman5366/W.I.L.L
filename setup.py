from distutils.core import setup
setup(
  name = 'WillPy',
  packages = ['WillPy'],
  version = '3.1',
  description = 'A smart personal assistant',
  author = 'Will Beddow',
  author_email = 'WillPy@willbeddow.com',
  url = 'https://github.com/ironman5366/WillPy',
  download_url = 'https://github.com/ironman5366/WillPy/tarball/3.1',
  keywords = ['Personal Assistant', 'Plugins'],
  classifiers = [],
)
def wolfram_setup():
    wolframalpha_key = raw_input("Please enter a wolframalpha key. You can get one from http://products.wolframalpha.com/api/>")
    if wolframalpha_key:
        import WillPy.config as config
        config.add_config({"wolfram" : [wolframalpha_key]})
    else:
        if raw_input("This is a required step for setup, are you sure you want to quit? (y/n)").lower() != "y":
            wolfram_setup()