import WillPy.plugins.API as API


@API.subscribe_to({
"name": "echo",
"ents_needed" : False,
"structure" : {"needed":["VERB"]},
"questions_needed" : False,
"key_words" : ["echo"]})
def echo(word, full_text):
    return full_text
