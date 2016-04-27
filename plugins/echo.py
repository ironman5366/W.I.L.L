import will.plugins.API as API


@API.subscribe_to("echo")
def echo(word, full_text):
    return ' '.join(full_text.split(' ')[1:])
