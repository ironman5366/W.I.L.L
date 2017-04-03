from core.plugin_handler import subscribe
import logging

log = logging.getLogger()

easter_eggs = {
    "Who are you?": "I am W.I.L.L, short for Wireless Intelligent Linguistical Liveware",
    "Who created you?": "I was created by Will Beddow (will@willbeddow.com)",
    "Take me to your leader": "I don't have a leader. But you can talk to my creator, Will Beddow (will@willbeddow.com)",
    "Why do you exist": "To kick ass, execute advanced context-aware natural language algorithms, and take names.",
    "What's your name?": "I am W.I.L.L, short for Wireless Intelligent Linguistic Liveware",
    "How old are you?": "W.I.L.L was first thought up in 2014, and W.I.L.L 1.0 was made in the same year. I underwent "
                        "many iterations and changes, and finally, here I am. Fun fact: the current W.I.L.L uses none "
                        "of the original code from W.I.L.L 1.0 ",
    "Hey W.I.L.L": "What's up?",
    "Who is your master?": "I was created by Will Beddow (will@willbeddow.com)"
}

def egg_hunt(event):
    scores = [event["doc"].similarity(event["parse"](x)) for x in easter_eggs]
    return max(scores) >= 0.96

@subscribe(name="easter_eggs", check=egg_hunt)
def egg(event):
    scores = {}
    for x in easter_eggs:
        x_parse = event["parse"](x)
        scores.update({
            event["doc"].similarity(x_parse): easter_eggs[x]
        })
    most_compatible = scores[max(scores)]
    log.debug("Query {0} activated easter egg {1}".format(event["command"], most_compatible))
    response = {"type": "success", "text": most_compatible, "data": {}}
    return response
