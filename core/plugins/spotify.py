#Internal imports
from core.plugin_handler import subscribe
import tools

#External imports
import spotipy

#Builtin imports
import logging

sp = spotipy.Spotify()
log = logging.getLogger()

def is_spotify(event):
    event_doc = event["doc"]
    return "spotify" in [word.orth_.lower() for word in event_doc]

@subscribe(name="spotify", check=is_spotify)
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
    log.debug("In spotify module, found work {0}".format(work))
    song = sp.search(q='track:' + work, type='track')
    #Get the most popular of the found results
    song_items = song["tracks"]["items"]
    pops = {}
    for song_array in song_items:
        song_popularity = song_array["popularity"]
        pops.update({song_popularity: song_array})
    song_item = pops[max(pops.keys())]
    song_data = {
        "name": song_item["name"],
        "popularity": song_item["popularity"],
        "url": song_item["external_urls"]["spotify"],
        "artist": song_item["artists"][0]["name"]
    }
    log.debug("Found song {0}".format(song_data))
    #Get most popular song
    song_str = "Directing you to {0} by {1}".format(song_data["name"], song_data["artist"])
    return {"type": "success", "text": song_str, "data": {"url": song_data["url"]}}