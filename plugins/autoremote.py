import urllib2
import will.config as config
import will.plugins.API as API


@API.subscribe_to("autoremote")
def main(key_word, full_text):
    key = config.load_config("autoremote")["key"]
    urllib2.urlopen(
        'https://autoremotejoaomgcd.appspot.com/sendmessage?key={0}&message={1}'  # noqa
        .format(key, full_text))
    return "Done"
