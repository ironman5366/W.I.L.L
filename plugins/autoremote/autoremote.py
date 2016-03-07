import urllib2
import config


def main(command):
    key = config.load_config("autoremote")["key"]
    urllib2.urlopen(
        'https://autoremotejoaomgcd.appspot.com/sendmessage?key={0}&message={1}'  # noqa
        .format(key, command))
    return "Done"
