#Internal imports
from core.plugin_handler import subscribe
import tools

#Builtin imports
import logging
import json
import difflib

shows = json.loads(open("core/plugin_files/shows.json").read())
log = logging.getLogger()

def is_netflix(event):
    event_doc = event["doc"]
    return "netflix" in [word.orth_.lower() for word in event_doc]
@subscribe({"name": "netflix", "check":  is_netflix})
def main(event):
    event_doc = event["doc"]
    work = None
    for chunk in event_doc.noun_chunks:
        #Use dependency parsing to dermine the object of the command
        if chunk.root.dep_ == "dobj":
            work = chunk.text
    if not work:
        return {
            "type": "error",
            "text": "Couldn't parse song from sentence {0}".format(event["command"]),
            "data": {}
        }
    log.debug("In netflix module, found work {0}".format(work))
    #Find the show in a json file keyed with show names and that has show ids
    show_name = None
    for show in shows:
        if work.lower() in show.lower():
            show_name = show
            show_id = shows[show]
    if not show_name:
        return {
            "type":  "error",
            "text": "Couldn't find {0} in my list of Netflix shows and movies."
                    "If it's a new show, I might not have it. Feel free to let me know at "
                    "will@willbeddow.com so I can add the show to the list.",
            "data": {}
        }
    log.debug("Closest show is {0}".format(show_name))
    show_id = shows[show_name]
    show_str = "Directing you to {0}".format(show_name)
    return {"type": "success", "text": show_str, "data": {"url": "https://netflix.com/watch/{0}".format(show_id)}}